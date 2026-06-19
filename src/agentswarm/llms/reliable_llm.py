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
    few characters, checks whether the tail of the window is a pattern repeated
    consecutively "enough" times. This catches the classic failure mode where
    an LLM gets stuck re-emitting the same word, line, sentence or whole
    paragraph indefinitely, regardless of how fast the tokens arrive.

    **Length-aware threshold.** The number of consecutive copies required to
    declare a loop scales with the pattern length, because the two failure
    modes have very different statistics:

      - A *short* pattern (a single character, a word) can repeat a handful of
        times in perfectly legitimate output, so many copies are required
        before it is suspicious (up to ``min_repetitions``).
      - A *long* pattern (a full sentence or paragraph) repeating verbatim even
        a few times in a row is, with overwhelming probability, a loop. The
        chance of a 400-character span recurring by accident is negligible, so
        only ``long_pattern_min_repetitions`` copies are required.

    Concretely, the required repetition count for a pattern of length ``p`` is
    ``clamp(ceil(min_loop_span / p), long_pattern_min_repetitions,
    min_repetitions)``: it decreases as the pattern grows, bottoming out at
    ``long_pattern_min_repetitions`` for long units and topping out at
    ``min_repetitions`` for very short ones. This is what lets it catch the
    multi-sentence "reasoning loop" that a fixed short pattern length / high
    repetition count would silently miss.

    **Filler characters.** Short patterns made up entirely of "filler"
    characters are common in legitimate output and must not be mistaken for a
    loop. This covers two overlapping families:

      - *Whitespace* (spaces, tabs, newlines): indentation, alignment, blank
        lines.
      - *Structural formatting* characters (``- = _ * # | ~ + .``): Markdown
        table separators (``|--------|``), horizontal rules (``------``),
        header underlines (``======``), leader dots (``......``) and similar.
        A single repeated dash or pipe is exactly what a Markdown table emits,
        so it must not trip the strict short-pattern threshold.

    Any short pattern composed solely of such filler characters requires a much
    higher count, ``whitespace_min_repetitions``, before it is declared a loop.
    A truly runaway filler stream is still caught (the high threshold is small
    next to the thousands of characters a stuck model produces, and the output
    cap remains the final backstop).
    """

    #: Structural formatting characters that, like whitespace, legitimately
    #: tile in real output (Markdown tables, rules, header underlines, leaders).
    DEFAULT_FILLER_CHARS = frozenset("-=_*#|~+.")

    def __init__(
        self,
        min_repetitions: int = 12,
        max_pattern_length: int = 2048,
        check_every: int = 16,
        whitespace_min_repetitions: int = 256,
        long_pattern_min_repetitions: int = 4,
        min_loop_span: int = 48,
        whitespace_max_pattern_length: int = 8,
        filler_chars: Optional[frozenset] = None,
    ):
        if long_pattern_min_repetitions < 2:
            raise ValueError("long_pattern_min_repetitions must be at least 2")
        if min_repetitions < long_pattern_min_repetitions:
            raise ValueError(
                "min_repetitions must be >= long_pattern_min_repetitions"
            )
        if whitespace_min_repetitions < min_repetitions:
            raise ValueError(
                "whitespace_min_repetitions must be >= min_repetitions"
            )
        self.min_repetitions = min_repetitions
        self.max_pattern_length = max_pattern_length
        self.check_every = max(1, check_every)
        self.whitespace_min_repetitions = whitespace_min_repetitions
        self.long_pattern_min_repetitions = long_pattern_min_repetitions
        self.min_loop_span = min_loop_span
        self.whitespace_max_pattern_length = whitespace_max_pattern_length
        self.filler_chars = (
            filler_chars if filler_chars is not None else self.DEFAULT_FILLER_CHARS
        )
        # The window must hold the longest repetition we may need to confirm.
        # For long (numeric-threshold) patterns that is the largest pattern at
        # ``long_pattern_min_repetitions`` copies; for short whitespace patterns
        # it is ``whitespace_min_repetitions`` copies of a small unit. One extra
        # copy of margin lets detection succeed even when it fires mid-pattern.
        self._window_size = max(
            (long_pattern_min_repetitions + 1) * max_pattern_length,
            (whitespace_min_repetitions + 1) * whitespace_max_pattern_length,
        )
        self._buffer = ""
        self._since_check = 0

    def _is_filler(self, unit: str) -> bool:
        """True if ``unit`` is composed solely of whitespace/structural chars.

        Filler characters (spaces, tabs, newlines, and Markdown structural
        characters such as ``- = _ * # | ~ + .``) tile legitimately in real
        output, so any run made up entirely of them gets the lenient
        ``whitespace_min_repetitions`` threshold rather than the strict
        short-pattern one. The check is on character composition, not length:
        a long run of dashes is still just filler and must not be treated as a
        suspicious "long pattern".
        """
        if not unit:
            return False
        return all(ch.isspace() or ch in self.filler_chars for ch in unit)

    def required_repetitions(self, unit: str) -> int:
        """Consecutive copies of ``unit`` needed before it counts as a loop."""
        p = len(unit)
        if p == 0:
            return self.min_repetitions
        if self._is_filler(unit):
            return self.whitespace_min_repetitions
        # ceil(min_loop_span / p), clamped to [long_pattern_min, min_reps].
        base = -(-self.min_loop_span // p)
        return min(self.min_repetitions, max(self.long_pattern_min_repetitions, base))

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
        if n < 2:
            return None
        last = s[-1]
        # At least two copies must fit, so the period cannot exceed n // 2.
        max_p = min(self.max_pattern_length, n // 2)
        for p in range(1, max_p + 1):
            # Cheap prune: a p-periodic suffix has s[-1] == s[-1 - p]. This skips
            # the vast majority of candidate lengths with a single comparison
            # before any slice is materialized.
            if s[n - 1 - p] != last:
                continue
            unit = s[n - p : n]
            required = self.required_repetitions(unit)
            # Not enough buffered characters to confirm this many repetitions.
            if required * p > n:
                continue
            for r in range(2, required + 1):
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
                reps = self._detector.required_repetitions(unit)
                self._abort(
                    LLMLoopError(
                        f"LLM stream stuck repeating {reps}+ times: {preview!r}"
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
         short pattern repeats consecutively too many times. Short patterns made
         of filler characters (whitespace and Markdown structural characters
         like ``- = _ * # | ~``) use a much higher repetition threshold so that
         legitimate indentation, blank lines and table separators are not
         mistaken for a loop.

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
        loop_max_pattern_length: int = 2048,
        loop_whitespace_min_repetitions: int = 256,
        loop_long_pattern_min_repetitions: int = 4,
        loop_min_span: int = 48,
        loop_filler_chars: Optional[frozenset] = None,
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
            loop_min_repetitions (int): Maximum consecutive repetitions required
                before a loop is declared; this is the threshold for the
                shortest patterns (e.g. a single repeated character). Longer
                patterns require progressively fewer copies. Defaults to 12.
            loop_max_pattern_length (int): Longest repeating pattern (in
                characters) considered by the detector. Must be large enough to
                cover whole repeated sentences/paragraphs, not just words.
                Defaults to 2048.
            loop_whitespace_min_repetitions (int): Minimum consecutive
                repetitions required before a short *filler* pattern is declared
                a loop. Filler patterns are runs of whitespace (spaces, tabs,
                newlines) or Markdown structural characters (``- = _ * # | ~``),
                which legitimately tile in tables, rules and indentation. Set
                high enough to never trip on a wide table or a long separator
                while still catching runaway filler. Must be >=
                ``loop_min_repetitions``. Defaults to 256.
            loop_long_pattern_min_repetitions (int): Minimum consecutive
                repetitions required for a long pattern (a full sentence or
                paragraph). A long unit recurring verbatim even a few times is
                almost certainly a loop, so this is small. Must be >= 2 and
                <= ``loop_min_repetitions``. Defaults to 4.
            loop_min_span (int): Target repeated span, in characters, used to
                interpolate the required repetition count between
                ``loop_long_pattern_min_repetitions`` (long patterns) and
                ``loop_min_repetitions`` (short patterns). Defaults to 48.
            loop_filler_chars (Optional[frozenset]): Set of structural
                characters that, together with whitespace, get the lenient
                filler threshold. ``None`` uses the default
                (``- = _ * # | ~ + .``).
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
        self.loop_whitespace_min_repetitions = loop_whitespace_min_repetitions
        self.loop_long_pattern_min_repetitions = loop_long_pattern_min_repetitions
        self.loop_min_span = loop_min_span
        self.loop_filler_chars = loop_filler_chars
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
                whitespace_min_repetitions=self.loop_whitespace_min_repetitions,
                long_pattern_min_repetitions=self.loop_long_pattern_min_repetitions,
                min_loop_span=self.loop_min_span,
                filler_chars=self.loop_filler_chars,
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
