import asyncio
import logging
from typing import Callable, List, Optional
from .llm import LLM, LLMFunction, LLMOutput
from ..datamodels.message import Message
from ..datamodels.feedback import Feedback, FeedbackSystem
from ..utils.exceptions import LLMLoopError, LLMOutputLimitError

logger = logging.getLogger(__name__)


class _LoopDetector:
    """
    Detects degenerate repetition loops in a token stream.

    It keeps a bounded sliding window of the most recent characters and, every
    few characters, checks whether the tail of the window is a short pattern
    repeated consecutively at least ``min_repetitions`` times. This catches the
    classic failure mode where an LLM gets stuck re-emitting the same word,
    line, or phrase indefinitely, regardless of how fast the tokens arrive.
    """

    def __init__(
        self,
        min_repetitions: int = 12,
        max_pattern_length: int = 256,
        check_every: int = 16,
    ):
        if min_repetitions < 2:
            raise ValueError("min_repetitions must be at least 2")
        self.min_repetitions = min_repetitions
        self.max_pattern_length = max_pattern_length
        self.check_every = max(1, check_every)
        # The window only needs to hold the longest detectable repetition.
        self._window_size = max_pattern_length * (min_repetitions + 1)
        self._buffer = ""
        self._since_check = 0

    def feed(self, text: str):
        self._buffer += text
        if len(self._buffer) > self._window_size:
            self._buffer = self._buffer[-self._window_size :]
        self._since_check += len(text)

    def detect(self) -> Optional[str]:
        """Return the repeating unit if a loop is detected, else ``None``."""
        if self._since_check < self.check_every:
            return None
        self._since_check = 0

        s = self._buffer
        n = len(s)
        max_p = min(self.max_pattern_length, n // self.min_repetitions)
        for p in range(1, max_p + 1):
            unit = s[n - p : n]
            for r in range(2, self.min_repetitions + 1):
                if s[n - r * p : n - (r - 1) * p] != unit:
                    break
            else:
                return unit
        return None


class _StreamGuard(FeedbackSystem):
    """
    A FeedbackSystem proxy that observes the token stream of the wrapped LLM
    and signals when the request should be aborted.

    It transparently forwards every event to an optional inner feedback system
    while providing three protections to :class:`ReliableLLM`:

      - ``last_activity`` tracking for the inactivity (idle) timeout,
      - repetition-loop detection via :class:`_LoopDetector`,
      - an optional hard cap on the total number of emitted characters.

    When a loop or the output cap is hit, ``abort_exception`` is populated and
    ``abort_event`` is set so the watchdog can cancel the generation promptly.
    """

    def __init__(
        self,
        inner: Optional[FeedbackSystem],
        clock: Callable[[], float],
        detector: Optional[_LoopDetector] = None,
        max_output_chars: Optional[int] = None,
    ):
        self._inner = inner
        self._clock = clock
        self._detector = detector
        self._max_output_chars = max_output_chars
        self.last_activity = clock()
        self.total_chars = 0
        self.abort_exception: Optional[Exception] = None
        self.abort_event = asyncio.Event()

    def push(self, feedback: Feedback):
        # Any token produced by the LLM counts as liveness.
        if feedback.source == "llm":
            self.last_activity = self._clock()
            payload = feedback.payload
            if isinstance(payload, str) and payload:
                self._inspect(payload)
        if self._inner is not None:
            self._inner.push(feedback)

    def _inspect(self, text: str):
        if self.abort_exception is not None:
            return

        self.total_chars += len(text)
        if (
            self._max_output_chars is not None
            and self.total_chars > self._max_output_chars
        ):
            self._abort(
                LLMOutputLimitError(
                    f"LLM output exceeded {self._max_output_chars} characters"
                )
            )
            return

        if self._detector is not None:
            self._detector.feed(text)
            unit = self._detector.detect()
            if unit is not None:
                preview = unit if len(unit) <= 40 else unit[:40] + "..."
                self._abort(
                    LLMLoopError(
                        "LLM stream stuck repeating "
                        f"{self._detector.min_repetitions}+ times: {preview!r}"
                    )
                )

    def _abort(self, exc: Exception):
        self.abort_exception = exc
        self.abort_event.set()

    def subscribe(self, callback: Callable[[Feedback], None]):
        if self._inner is not None:
            self._inner.subscribe(callback)

    def to_dict(self) -> dict:
        raise NotImplementedError("_StreamGuard is an internal, non-serializable proxy.")

    @classmethod
    def recreate(cls, config: dict) -> "_StreamGuard":
        raise NotImplementedError("_StreamGuard is an internal, non-serializable proxy.")


class ReliableLLM(LLM):
    """
    A wrapper around an LLM that adds robustness guards and a retry mechanism.

    It protects against three distinct failure modes, observed live on the
    token stream through the :class:`FeedbackSystem`:

      1. **Inactivity timeout.** Instead of a total-duration timeout, the
         request is aborted only when ``timeout`` seconds elapse without a new
         token. This covers a model that never starts responding
         (time-to-first-token) and a stream that stalls between chunks, while
         never penalizing a legitimately long generation that keeps streaming.

      2. **Repetition loops.** When a model "goes mad" and keeps emitting the
         same word/line/phrase, the tokens keep flowing so the timeout would
         not help. A loop detector watches the stream and aborts as soon as a
         short pattern repeats consecutively too many times.

      3. **Output cap (optional).** A hard limit on total emitted characters,
         as a last-resort bound on runaway generations.

    Every aborted attempt is retried with exponential backoff, up to
    ``max_retries`` times.

    Token activity is observed through the :class:`FeedbackSystem`. An internal
    proxy feedback is always supplied to the wrapped LLM (which, for
    streaming-capable backends, also enables incremental token delivery). If
    the underlying LLM emits no token feedback, loop detection and the output
    cap are inactive and the inactivity timeout degrades to a total-duration
    timeout.
    """

    def __init__(
        self,
        llm: LLM,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        loop_detection: bool = True,
        loop_min_repetitions: int = 12,
        loop_max_pattern_length: int = 256,
        max_output_chars: Optional[int] = None,
    ):
        """
        Initialize the ReliableLLM.

        Args:
            llm (LLM): The base LLM implementation to wrap.
            timeout (float): Inactivity timeout in seconds. A request is aborted
                only if this much time passes without a new token. Defaults to 30.0.
            max_retries (int): Maximum number of retries. Defaults to 3.
            retry_delay (float): Initial delay between retries in seconds. Defaults to 1.0.
            backoff_factor (float): Multiplier for the retry delay. Defaults to 2.0.
            loop_detection (bool): Enable repetition-loop detection. Defaults to True.
            loop_min_repetitions (int): Minimum consecutive repetitions of a
                pattern before a loop is declared. Defaults to 12.
            loop_max_pattern_length (int): Longest repeating pattern (in
                characters) considered by the detector. Defaults to 256.
            max_output_chars (Optional[int]): Hard cap on total emitted
                characters. ``None`` disables the cap. Defaults to None.
        """
        self.llm = llm
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.loop_detection = loop_detection
        self.loop_min_repetitions = loop_min_repetitions
        self.loop_max_pattern_length = loop_max_pattern_length
        self.max_output_chars = max_output_chars

    async def generate(
        self,
        messages: List[Message],
        functions: List[LLMFunction] = None,
        feedback: Optional[FeedbackSystem] = None,
        temperature: float = 0.0,
    ) -> LLMOutput:
        """
        Generate a response from the wrapped LLM with inactivity, loop and
        output-size guards plus a retry mechanism.
        """
        last_exception = None
        current_delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                return await self._generate_guarded(
                    messages, functions, feedback, temperature
                )
            except asyncio.TimeoutError:
                last_exception = TimeoutError(
                    f"No token received for {self.timeout}s (inactivity timeout)"
                )
                logger.warning(f"Attempt {attempt + 1} failed: inactivity timeout")
            except (LLMLoopError, LLMOutputLimitError) as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

            if attempt < self.max_retries:
                logger.info(f"Retrying in {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay *= self.backoff_factor
            else:
                logger.error("Max retries reached.")

        raise last_exception

    def _build_guard(
        self, feedback: Optional[FeedbackSystem], clock: Callable[[], float]
    ) -> _StreamGuard:
        detector = (
            _LoopDetector(
                min_repetitions=self.loop_min_repetitions,
                max_pattern_length=self.loop_max_pattern_length,
            )
            if self.loop_detection
            else None
        )
        return _StreamGuard(
            inner=feedback,
            clock=clock,
            detector=detector,
            max_output_chars=self.max_output_chars,
        )

    async def _generate_guarded(
        self,
        messages: List[Message],
        functions: Optional[List[LLMFunction]],
        feedback: Optional[FeedbackSystem],
        temperature: float,
    ) -> LLMOutput:
        """
        Run a single generation attempt, aborting it on inactivity, a detected
        repetition loop, or an exceeded output cap.
        """
        loop = asyncio.get_event_loop()
        guard = self._build_guard(feedback, loop.time)

        gen_task = asyncio.ensure_future(
            self.llm.generate(messages, functions, guard, temperature)
        )
        abort_task = asyncio.ensure_future(guard.abort_event.wait())

        try:
            while True:
                if gen_task.done():
                    return gen_task.result()

                idle = loop.time() - guard.last_activity
                remaining = self.timeout - idle
                if remaining <= 0:
                    # No activity within the timeout window: abort this attempt.
                    raise asyncio.TimeoutError()

                await asyncio.wait(
                    {gen_task, abort_task},
                    timeout=max(remaining, 0),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # A loop or output-cap breach takes precedence over a result
                # that may have completed in the same slice.
                if guard.abort_exception is not None:
                    raise guard.abort_exception
                if gen_task.done():
                    return gen_task.result()
                # Otherwise the timeout slice elapsed; re-evaluate idle time.
        finally:
            abort_task.cancel()
            if not gen_task.done():
                gen_task.cancel()
                try:
                    await gen_task
                except (asyncio.CancelledError, Exception):
                    pass
