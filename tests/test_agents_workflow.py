import pytest
import uuid
import asyncio
from typing import List, Any, Optional
from pydantic import BaseModel, Field

from agentswarm.agents import BaseAgent, ReActAgent
from agentswarm.datamodels import Context, Message, LocalStore, StrResponse
from agentswarm.llms import LLM, LLMOutput, LLMUsage, LLMFunction, LLMFunctionExecution
from agentswarm.utils.tracing import Tracing

# --- Mock Infrastructure ---


class DummyTracing(Tracing):
    def trace_agent(self, *args, **kwargs):
        pass

    def trace_loop_step(self, *args, **kwargs):
        pass

    def trace_agent_result(self, *args, **kwargs):
        pass

    def trace_agent_error(self, *args, **kwargs):
        pass

    def to_dict(self):
        return {"type": "dummy"}

    @classmethod
    def recreate(cls, config):
        return cls()


class MockLLM(LLM):
    def __init__(self, responses: List[str]):
        self.responses = responses
        self.call_count = 0

    async def generate(
        self,
        messages: List[Message],
        functions: List[LLMFunction] = None,
        feedback: Any = None,
    ) -> LLMOutput:
        resp_text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        usage = LLMUsage(model="mock-exhaustive", total_token_count=100)

        function_calls = []
        if "CALL:" in resp_text:
            import re

            match = re.search(r"CALL: (\w+)\((.*)\)", resp_text)
            if match:
                name, args_str = match.groups()
                function_calls.append(LLMFunctionExecution(name=name, arguments={}))

        return LLMOutput(text=resp_text, function_calls=function_calls, usage=usage)


# --- Test Agents ---


class DataProducerAgent(BaseAgent[dict, StrResponse]):
    def id(self) -> str:
        return "producer"

    def description(self, user_id: str) -> str:
        return "Produces data"

    async def execute(self, user_id, context, input=None) -> StrResponse:
        context.messages.append(Message(type="assistant", content="Producer worked"))
        context.store.set("producer_key", "producer_value")
        context.add_usage(LLMUsage(model="producer-model", total_token_count=10))
        return StrResponse(value="Done")


class DataConsumerAgent(BaseAgent[dict, StrResponse]):
    def id(self) -> str:
        return "consumer"

    def description(self, user_id: str) -> str:
        return "Consumes data"

    async def execute(self, user_id, context, input=None) -> StrResponse:
        val = context.store.get("producer_key")
        context.messages.append(
            Message(type="assistant", content=f"Consumer read: {val}")
        )
        context.add_usage(LLMUsage(model="consumer-model", total_token_count=20))
        return StrResponse(value=f"Consumed {val}")


class OrchestratorAgent(ReActAgent):
    def __init__(self, mock_llm: MockLLM):
        super().__init__()
        self.mock_llm = mock_llm

    def id(self) -> str:
        return "orchestrator"

    def description(self, user_id: str) -> str:
        return "Orchestrates"

    def get_llm(self, user_id: str) -> LLM:
        return self.mock_llm

    def prompt(self, user_id: str) -> str:
        return "You are an orchestrator."

    def available_agents(self, user_id: str) -> List[BaseAgent]:
        return [DataProducerAgent(), DataConsumerAgent()]


# --- Tests ---


@pytest.mark.asyncio
async def test_multi_agent_flow_integration():
    """
    Verifies that a ReActAgent can call sub-agents, and their
    usage and store updates are preserved in the master context.
    NOTE: ReActAgent returns only the final messages, but usage and store are mutated.
    """
    mock_llm = MockLLM(
        responses=["CALL: producer({})", "CALL: consumer({})", "Finishing now."]
    )

    agent = OrchestratorAgent(mock_llm)
    context = Context(
        trace_id=str(uuid.uuid4()),
        messages=[Message(type="user", content="Start")],
        store=LocalStore(),
        tracing=DummyTracing(),
    )

    result = await agent.execute("test-user", context)

    # 1. Check result (final iteration output)
    assert len(result) == 1
    assert "Finishing" in result[0].content

    # 2. Check Store mutation (preserved from sub-agents)
    assert context.store.get("producer_key") == "producer_value"

    # 3. Check Usage mutation (THIS IS THE CRITICAL PART FOR THE BUG FIX)
    # LLM(3 calls * 100) + Producer(10) + Consumer(20) = 330
    total_tokens = sum(u.total_token_count for u in context.usage)
    assert total_tokens == 330
    assert len(context.usage) == 5


@pytest.mark.asyncio
async def test_recursive_react_limit():
    """Verify that ReActAgent hits the limit and raises Exception."""
    mock_llm = MockLLM(responses=["CALL: producer({})"])
    agent = OrchestratorAgent(mock_llm)
    agent.max_iterations = 2

    context = Context(
        trace_id="t-loop", messages=[], store=LocalStore(), tracing=DummyTracing()
    )

    with pytest.raises(Exception, match="Max iterations reached"):
        await agent.execute("user", context)

    # Even if it failed, usage should have been recorded up to the point of failure
    # 2 iterations * (LLM + Producer) = 4 usage entries
    assert len(context.usage) == 4
