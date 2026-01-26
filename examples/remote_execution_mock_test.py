import asyncio
from typing import List, Optional
from pydantic import BaseModel, Field

from agentswarm.agents import BaseAgent, HttpRemoteAgent, RemoteExecutionMode
from agentswarm.datamodels import (
    Context,
    Message,
    Store,
    LocalStore,
    CompletionResponse,
    FeedbackSystem,
)
from agentswarm.utils.tracing import Tracing
from agentswarm.utils.remote_handler import RemoteAgentHandler


# --- Mock Serializable Components ---

_SHARED_STORE_DATA = {}


class MockRemoteStore(Store):
    """
    A Mock store that uses a global dictionary to simulate a shared resource (like Redis).
    """

    def get(self, key):
        return _SHARED_STORE_DATA.get(key)

    def set(self, key, value):
        _SHARED_STORE_DATA[key] = value

    def has(self, key):
        return key in _SHARED_STORE_DATA

    def items(self):
        return _SHARED_STORE_DATA

    def to_dict(self) -> dict:
        return {}

    @classmethod
    def recreate(cls, config: dict) -> "MockRemoteStore":
        return cls()


class MockTracing(Tracing):
    def trace_agent(self, context, agent_id, arguments):
        pass

    def trace_loop_step(self, context, step_name):
        pass

    def trace_agent_result(self, context, agent_id, result):
        pass

    def trace_agent_error(self, context, agent_id, error):
        pass

    def to_dict(self) -> dict:
        return {}

    @classmethod
    def recreate(cls, config: dict) -> "MockTracing":
        return cls()


# --- Real Agent (would be on the worker) ---


class GreetingInput(BaseModel):
    name: str


class GreetingAgent(BaseAgent[GreetingInput, CompletionResponse]):
    def id(self) -> str:
        return "greeting_agent"

    def description(self, user_id: str) -> str:
        return "Greets a user"

    async def execute(
        self, user_id: str, context: Context, input: GreetingInput = None
    ) -> CompletionResponse:
        context.store.set("last_greeted", input.name)
        return CompletionResponse(value=f"Hello, {input.name}!")


# --- Mock HTTP Client for Testing ---


class MockHttpClient:
    def __init__(self, handler: RemoteAgentHandler):
        self.handler = handler

    async def post(self, url: str, json: dict):
        # Simulate /execute endpoint
        if "/execute" in url:
            result = await self.handler.handle_execute(json)

            # Wrap in a mock Response object
            class MockResponse:
                def __init__(self, data):
                    self.data = data

                def json(self):
                    return self.data

                def raise_for_status(self):
                    pass

            return MockResponse(result)
        raise ValueError(f"Unknown URL: {url}")


# --- Test Execution ---


async def main():
    print("🚀 Starting Remote Agent Mock Test")

    # 1. Setup Remote Side (Worker)
    real_agent = GreetingAgent()
    remote_handler = RemoteAgentHandler(agents=[real_agent])

    # 2. Setup Local Side (Executor)
    # Use concrete types for OutputType parsing to work
    class GreetingProxyAgent(HttpRemoteAgent[GreetingInput, CompletionResponse]):
        pass

    proxy_agent = GreetingProxyAgent(
        base_url="http://mock-worker", remote_agent_id="greeting_agent"
    )

    # Mocking the _call_remote_sync method to use our local handler
    mock_client = MockHttpClient(remote_handler)

    async def mocked_call(payload):
        resp = await mock_client.post("http://mock-worker/execute", json=payload)
        return resp.json()

    proxy_agent._call_remote_sync = mocked_call

    # 3. Create Context
    store = MockRemoteStore()
    tracing = MockTracing()
    context = Context(trace_id="test-trace", messages=[], store=store, tracing=tracing)

    # 4. Execute
    print("Calling remote agent...")
    input_data = GreetingInput(name="Alice")
    result = await proxy_agent.execute("user-1", context, input=input_data)

    # 5. Verify
    print(f"Result: {result.value}")
    assert result.value == "Hello, Alice!"

    print(f"Store state after remote call: {context.store.get('last_greeted')}")
    assert context.store.get("last_greeted") == "Alice"

    print("✅ Remote Agent Mock Test Passed!")


if __name__ == "__main__":
    asyncio.run(main())
