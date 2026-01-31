import asyncio
import pytest
from typing import List, Optional, Any
from agentswarm.llms import LLM, LLMFunction, LLMOutput, LLMUsage, ReliableLLM
from agentswarm.datamodels import Message


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
    ) -> LLMOutput:
        self.call_count += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.current_fails < self.fail_count:
            self.current_fails += 1
            raise Exception("Mock error")

        return LLMOutput(
            text="Success",
            function_calls=[],
            usage=LLMUsage(model="mock", total_token_count=10),
        )


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
async def test_timeout():
    # Delay is 2s, timeout is 0.5s
    mock = MockLLM(delay=2)
    reliable = ReliableLLM(mock, timeout=0.5, max_retries=0)
    with pytest.raises(Exception, match="timed out"):
        await reliable.generate([])
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_timeout_retry():
    # 1st attempt timeouts, 2nd attempt succeeds
    class TimeoutOnceMock(MockLLM):
        async def generate(self, messages, functions=None, feedback=None):
            if self.call_count == 0:
                # We still need to increment call_count if we don't call super
                self.call_count += 1
                await asyncio.sleep(1)
                return None
            return await super().generate(messages, functions, feedback)

    mock = TimeoutOnceMock()
    reliable = ReliableLLM(mock, timeout=0.5, max_retries=1, retry_delay=0.1)
    output = await reliable.generate([])
    assert output.text == "Success"
    assert mock.call_count == 2
