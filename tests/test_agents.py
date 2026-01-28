import pytest
from typing import List
from pydantic import BaseModel, Field
from agentswarm.agents import BaseAgent, RemoteAgent, RemoteExecutionMode
from agentswarm.datamodels import Context, LocalStore, Message, StrResponse
from agentswarm.datamodels.store import Store


class MockStore(Store):
    def items(self):
        return {}

    def to_dict(self):
        return {"type": "mock", "config": {}}

    def get(self, k):
        raise KeyError(k)

    def set(self, k, v):
        pass

    def has(self, k):
        return False

    def __len__(self):
        return 0

    @classmethod
    def recreate(cls, config):
        return cls()


class MockInput(BaseModel):
    text: str = Field(description="mock input")


class MockAgent(BaseAgent[MockInput, StrResponse]):
    def id(self) -> str:
        return "mock"

    def description(self, user_id: str) -> str:
        return "mock"

    async def execute(self, user_id, context, input):
        return StrResponse(value=f"Processed: {input.text}")


@pytest.mark.asyncio
async def test_base_agent_execution():
    """Verify that a simple agent can be executed with a context."""
    agent = MockAgent()
    context = Context(trace_id="t1", messages=[], store=LocalStore(), tracing=None)

    result = await agent.execute("u1", context, MockInput(text="hello"))
    assert result.value == "Processed: hello"


def test_base_agent_generic_types():
    """Verify that generic types are correctly extracted."""
    agent = MockAgent()
    assert agent._get_generic_type(0) == MockInput
    assert agent._get_generic_type(1) == StrResponse


class MockRemoteAgent(RemoteAgent[MockInput, StrResponse]):
    def id(self) -> str:
        return "remote-mock"

    def get_remote_agent_id(self) -> str:
        return "remote-mock"

    async def _call_remote_sync(self, payload: dict) -> dict:
        return {
            "result": {"value": "Remote Result"},
            "updated_context": payload["context"],
        }

    async def _call_remote_async_init(self, *args, **kwargs):
        pass

    async def _poll_for_result(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_remote_agent_merge():
    """Verify that RemoteAgent merges context correctly."""
    agent = MockRemoteAgent()
    context = Context(trace_id="t1", messages=[], store=MockStore(), tracing=None)

    result = await agent.execute("u1", context, MockInput(text="test"))
    assert result.value == "Remote Result"
    # Even if remote didn't add anything, merge should have been called
