import asyncio
import os
from typing import List
import uuid
from pydantic import BaseModel, Field
from agentswarm.agents import ReActAgent, BaseAgent
from agentswarm.datamodels import Message, Context, LocalStore, CompletionResponse
from agentswarm.llms import LLM, GeminiLLM
from agentswarm.utils.tracing import LocalTracing
from print_utils import Colors, print_message, print_separator
from google.genai import Client

from dotenv import load_dotenv

load_dotenv()

client = Client(
    vertexai=True,
    project=os.getenv("VERTEX_PROJECT"),
    location=os.getenv("VERTEX_LOCATION"),
)


class MockCompletionInput(BaseModel):
    query: str = Field(description="The query to complete.")


class MockCompletionAgent(BaseAgent[MockCompletionInput, CompletionResponse]):
    def id(self) -> str:
        return "mock_completion_agent"

    def description(self, user_id: str) -> str:
        return "An agent that can answer questions"

    async def execute(
        self, user_id: str, context: Context, input: MockCompletionInput = None
    ) -> CompletionResponse:
        return CompletionResponse(
            value=f"FINAL COMPLETION: The answer to '{input.query}' is 42."
        )


class CompletionTestMasterAgent(ReActAgent):
    def __init__(self):
        super().__init__(max_iterations=10, max_concurrent_agents=5)

    def get_llm(self, user_id: str) -> LLM:
        return GeminiLLM(client=client, model="gemini-2.5-flash-lite")

    def id(self) -> str:
        return "completion_test_master"

    def description(self, user_id: str) -> str:
        return "A master agent to test CompletionResponse"

    def prompt(self, user_id: str) -> str:
        return "I'm your master agent."

    def available_agents(self, user_id: str) -> List[BaseAgent]:
        return self.get_default_agents() + [MockCompletionAgent()]


async def run_test(prompt: str, scenario_name: str):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}>>> SCENARIO: {scenario_name}{Colors.END}")
    print(f"{Colors.GREEN}Prompt: '{prompt}'{Colors.END}")

    master_agent = CompletionTestMasterAgent()
    store = LocalStore()
    tracing = LocalTracing()
    trace_id = str(uuid.uuid4())
    messages = [Message(type="user", content=prompt)]

    context = Context(
        trace_id=trace_id,
        messages=messages,
        store=store,
        tracing=tracing,
        default_llm=GeminiLLM(client=client),
    )

    try:
        results = await master_agent.execute("user-id", context)

        print_separator()
        print(f"{Colors.BOLD}{Colors.YELLOW}Final Results in Loop Output:{Colors.END}")
        for result in results:
            if isinstance(result, Message):
                print_message(result)
            elif isinstance(result, CompletionResponse):
                print(
                    f"\n{Colors.BOLD}{Colors.MAGENTA}🏁 FINAL COMPLETION RESPONSE:{Colors.END}"
                )
                print(f"{Colors.MAGENTA}{result.value}{Colors.END}")

    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")


async def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}🚀 CompletionResponse Refined Logic Test{Colors.END}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")

    # Scenario 1: Only CompletionResponse (should terminate)
    await run_test("Give me the final answer to life.", "Single CompletionResponse")

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}✅ Examples completed.{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")


if __name__ == "__main__":
    asyncio.run(main())
