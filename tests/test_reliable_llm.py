import asyncio
import pytest
from typing import List, Optional, Any
from agentswarm.llms import LLM, LLMFunction, LLMOutput, LLMUsage, ReliableLLM
from agentswarm.datamodels import Message
from agentswarm.datamodels.feedback import Feedback


def _success_output() -> LLMOutput:
    return LLMOutput(
        text="Success",
        function_calls=[],
        usage=LLMUsage(model="mock", total_token_count=10),
    )


class MockLLM(LLM):
    def __init__(self, fail_count=0, delay=0):
        self.fail_count = fail_count
        self.current_fails = 0
        self.delay = delay
        self.call_count = 0

    async def generate(
        self,
        messages: List[Message],
        functions: List[LLMFunction] = None,
        feedback: Optional[Any] = None,
        temperature: float = 0.0,
    ) -> LLMOutput:
        self.call_count += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.current_fails < self.fail_count:
            self.current_fails += 1
            raise Exception("Mock error")

        return _success_output()


@pytest.mark.asyncio
async def test_success_immediate():
    mock = MockLLM()
    reliable = ReliableLLM(mock)
    output = await reliable.generate([])
    assert output.text == "Success"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_retry_success():
    # Fails 2 times, should succeed on 3rd attempt
    mock = MockLLM(fail_count=2)
    reliable = ReliableLLM(mock, max_retries=3, retry_delay=0.1)
    output = await reliable.generate([])
    assert output.text == "Success"
    assert mock.call_count == 3


@pytest.mark.asyncio
async def test_retry_failure():
    # Fails 5 times, but max_retries is 3 (total 4 attempts)
    mock = MockLLM(fail_count=5)
    reliable = ReliableLLM(mock, max_retries=3, retry_delay=0.1)
    with pytest.raises(Exception, match="Mock error"):
        await reliable.generate([])
    assert mock.call_count == 4


@pytest.mark.asyncio
async def test_inactivity_timeout_on_total_stall():
    # No token is ever produced; a 2s stall must trip the 0.5s inactivity timeout.
    mock = MockLLM(delay=2)
    reliable = ReliableLLM(mock, timeout=0.5, max_retries=0)
    with pytest.raises(Exception, match="inactivity timeout"):
        await reliable.generate([])
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_long_streaming_does_not_timeout():
    # Total duration (1.5s) far exceeds the timeout (0.3s), but tokens keep
    # arriving every 0.15s so the inactivity timeout must never fire.
    class StreamingLLM(LLM):
        def __init__(self):
            self.call_count = 0

        async def generate(
            self, messages, functions=None, feedback=None, temperature=0.0
        ):
            self.call_count += 1
            for _ in range(10):
                await asyncio.sleep(0.15)
                if feedback:
                    feedback.push(Feedback(source="llm", payload="tok"))
            return _success_output()

    mock = StreamingLLM()
    reliable = ReliableLLM(mock, timeout=0.3, max_retries=0)
    output = await reliable.generate([])
    assert output.text == "Success"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_inactivity_timeout_on_stream_gap():
    # A first token arrives, then the stream stalls: the gap must trip the timeout.
    class StallAfterFirstToken(LLM):
        def __init__(self):
            self.call_count = 0

        async def generate(
            self, messages, functions=None, feedback=None, temperature=0.0
        ):
            self.call_count += 1
            if feedback:
                feedback.push(Feedback(source="llm", payload="tok"))
            await asyncio.sleep(5)
            return _success_output()

    mock = StallAfterFirstToken()
    reliable = ReliableLLM(mock, timeout=0.3, max_retries=0)
    with pytest.raises(Exception, match="inactivity timeout"):
        await reliable.generate([])
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_timeout_retry():
    # 1st attempt stalls (inactivity timeout), 2nd attempt succeeds.
    class TimeoutOnceMock(MockLLM):
        async def generate(
            self, messages, functions=None, feedback=None, temperature=0.0
        ):
            if self.call_count == 0:
                self.call_count += 1
                await asyncio.sleep(1)
                return None
            return await super().generate(messages, functions, feedback, temperature)

    mock = TimeoutOnceMock()
    reliable = ReliableLLM(mock, timeout=0.5, max_retries=1, retry_delay=0.1)
    output = await reliable.generate([])
    assert output.text == "Success"
    assert mock.call_count == 2


# --- Loop / output-cap protection -------------------------------------------

from agentswarm.utils.exceptions import LLMLoopError, LLMOutputLimitError


class LoopingLLM(LLM):
    """Emits a repeating phrase forever (tokens keep flowing, content repeats)."""

    def __init__(self, unit="repeat me ", count=10000, delay=0.001):
        self.unit = unit
        self.count = count
        self.delay = delay
        self.call_count = 0

    async def generate(self, messages, functions=None, feedback=None, temperature=0.0):
        self.call_count += 1
        for _ in range(self.count):
            await asyncio.sleep(self.delay)
            if feedback:
                feedback.push(Feedback(source="llm", payload=self.unit))
        return _success_output()


@pytest.mark.asyncio
async def test_loop_detection_aborts():
    mock = LoopingLLM()
    reliable = ReliableLLM(
        mock, timeout=30.0, max_retries=0, loop_min_repetitions=5
    )
    with pytest.raises(LLMLoopError):
        await reliable.generate([])
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_loop_detection_retries():
    mock = LoopingLLM()
    reliable = ReliableLLM(
        mock, timeout=30.0, max_retries=2, retry_delay=0.01, loop_min_repetitions=5
    )
    with pytest.raises(LLMLoopError):
        await reliable.generate([])
    # initial attempt + 2 retries
    assert mock.call_count == 3


@pytest.mark.asyncio
async def test_no_false_positive_on_varied_stream():
    class VariedLLM(LLM):
        async def generate(
            self, messages, functions=None, feedback=None, temperature=0.0
        ):
            for i in range(200):
                if feedback:
                    feedback.push(Feedback(source="llm", payload=f"word{i} "))
            return _success_output()

    mock = VariedLLM()
    reliable = ReliableLLM(mock, timeout=30.0, max_retries=0)
    output = await reliable.generate([])
    assert output.text == "Success"


@pytest.mark.asyncio
async def test_output_cap_aborts():
    class ChattyLLM(LLM):
        async def generate(
            self, messages, functions=None, feedback=None, temperature=0.0
        ):
            for i in range(1000):
                if feedback:
                    feedback.push(Feedback(source="llm", payload=f"chunk{i} "))
            return _success_output()

    mock = ChattyLLM()
    reliable = ReliableLLM(
        mock, timeout=30.0, max_retries=0, loop_detection=False, max_output_chars=100
    )
    with pytest.raises(LLMOutputLimitError):
        await reliable.generate([])
