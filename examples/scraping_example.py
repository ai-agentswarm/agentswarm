import asyncio
import os
from typing import List
import uuid
from agentswarm.agents import ReActAgent, BaseAgent, MapReduceAgent
from agentswarm.datamodels import Message, Context, LocalStore
from agentswarm.llms import LLM, GeminiLLM
from agentswarm.utils.tracing import LocalTracing
from print_utils import Colors, get_user_input, print_message, print_separator
from google.genai import Client
from basic_agents.scraper_agent import ScraperAgent

import textwrap

from dotenv import load_dotenv
load_dotenv()

client = Client(vertexai=True, project=os.getenv("VERTEX_PROJECT"), location=os.getenv("VERTEX_LOCATION"))

class MasterAgent(ReActAgent):
    def __init__(self):
        super().__init__(100, 5)

    def get_llm(self, user_id: str) -> LLM:
        return GeminiLLM(client=client)

    def id(self) -> str:
        return "master"

    def description(self, user_id: str) -> str:
        return "Master is the main agent that coordinates the other agents"

    def prompt(self, user_id: str) -> str:
        return "Use the available tools to answer the user's question. Otherwise, use your own information"

    def available_agents(self, user_id: str) -> List[BaseAgent]:
        additional_agents = [ScraperAgent()]
        all_agents_for_subtask = self.get_default_agents() + additional_agents
        return all_agents_for_subtask + [MapReduceAgent(max_iterations=1000, agents=all_agents_for_subtask)]


async def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🚀 Agents Swarm initialized!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")

    master_agent = MasterAgent()

    conversation = []
    store = LocalStore()
    tracing = LocalTracing()
    trace_id = str(uuid.uuid4())

    print(f"{Colors.GREEN}Trace ID: {trace_id}{Colors.END}")

    prompt = '''
    Visit the sitemap https://www.wired.com/sitemap.xml?year=2025&month=12&week=2 and extract the first 15 links that point to articles about artificial intelligence and AI.
    If you find less than 15 links, proceed only with those you have found. 
    For each of these articles, visit the link, generate a summary and finally create a well written report. 
    The report must include for each article: the title, the original link, a vote from 1 to 5 that how much an article seems interesting and impactful (try to be honest, you will save my time) and a brief summary of maximum 5 lines.
    '''

    print(f"\n{Colors.BOLD}{Colors.GRAY}{'=' * 80}{Colors.END}")
    wrapped_prompt = textwrap.fill(prompt, width=80)
    print(f"{Colors.BOLD}{Colors.GRAY}{wrapped_prompt}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GRAY}{'=' * 80}{Colors.END}\n")

    conversation.append(Message(type="user", content=prompt))
    context = Context(
        trace_id=trace_id,
        messages=conversation,
        store=store,
        tracing=tracing,
        default_llm=GeminiLLM(client=client)
    )
    tracing.trace_agent(context, master_agent.id(), {"task": prompt})

    print(f"\n{Colors.GRAY}⏳ Processing...{Colors.END}")

    try:
        response = await master_agent.execute('user-id', context)
        tracing.trace_agent_result(context, master_agent.id(), response)
        conversation = conversation + response
        
        print_separator()
        for message in response:
            print_message(message)

    except Exception as e:
        tracing.trace_agent_error(context, master_agent.id(), e)
        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()



if __name__ == "__main__":
    asyncio.run(main())