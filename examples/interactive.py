import asyncio
import os
from typing import List
import uuid
from agentswarm.agents import ReActAgent, BaseAgent, MapReduceAgent
from agentswarm.datamodels import Message, Context
from agentswarm.llms import LLM, GeminiLLM
from agentswarm.utils.tracing import trace_agent, trace_agent_error, trace_agent_result
from print_utils import Colors, get_user_input, print_message, print_separator

from basic_agents.scraper_agent import ScraperAgent

import textwrap

from dotenv import load_dotenv
load_dotenv()

print(os.getenv("GEMINI_API_KEY"))

class MasterAgent(ReActAgent):
    def __init__(self, max_iterations: int = 100, max_concurrent_agents: int = 1):
        super().__init__(max_iterations, max_concurrent_agents)

    def get_llm(self, user_id: str) -> LLM:
        return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))

    def id(self) -> str:
        return "master"

    def description(self, user_id: str) -> str:
        return "Master is the main agent that coordinates the other agents"

    def prompt(self, user_id: str) -> str:
        return "Use the available tools to answer the user's question. Otherwise, use your own information"

    def available_agents(self, user_id: str) -> List[BaseAgent]:
        return []


async def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🚀 Agents Swarm initialized!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")

    master_agent = MasterAgent()

    conversation = []
    store = {}
    thoughts = []
    trace_id = str(uuid.uuid4())

    print(f"{Colors.GREEN}Trace ID: {trace_id}{Colors.END}")

    while True:
        user_input = get_user_input()
        
        if user_input.lower() == "exit":
            print(f"\n{Colors.BOLD}{Colors.MAGENTA}👋 Goodbye!{Colors.END}\n")
            break
        
        if not user_input.strip():
            print(f"{Colors.YELLOW}⚠️ Insert a valid message{Colors.END}")
            continue
        
        conversation.append(Message(type="user", content=user_input))
        context = Context(trace_id=trace_id, messages=conversation, store=store, thoughts=thoughts, default_llm=GeminiLLM(api_key=os.getenv("GEMINI_API_KEY")))
        
        trace_agent(context, master_agent.id(), {"task": user_input})

        print(f"\n{Colors.GRAY}⏳ Processing...{Colors.END}")
        try:
            response = await master_agent.execute('user-id', context)
            trace_agent_result(context, master_agent.id(), response)
            conversation = conversation + response
            
            print_separator()
            for message in response:
                print_message(message)

        except Exception as e:
            trace_agent_error(context, master_agent.id(), e)
            print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
            import traceback
            traceback.print_exc()



if __name__ == "__main__":
    asyncio.run(main())