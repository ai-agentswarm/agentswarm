import os
from typing import List

from pydantic import BaseModel, Field
from ..llms import LLM, GeminiLLM
from .base_agent import BaseAgent
from ..datamodels import Context, Message, KeyStoreResponse
from .react_agent import ReActAgent

class MapReduceInput(BaseModel):
    task: str = Field(description="The task to solve, as a string")

class MapReduceAgent(ReActAgent[MapReduceInput, KeyStoreResponse]):
    def __init__(self, max_iterations: int = 100, agents: List[BaseAgent] = []):
        super().__init__(max_iterations)
        self.agents = agents

    def get_llm(self, user_id: str) -> LLM:
        # TODO: Better LLM consiguration
        return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))

    def id(self) -> str:
        return "map-reduce"
    
    def description(self, user_id: str) -> str:
        return """USE THIS AGENT FOR:
        1. COMPLEX CONTENT GENERATION: Creating multi-part artifacts like software libraries, full books, or extensive reports where each chapter/module needs to be generated in parallel.
        2. RECURSIVE TASKS: Exploration of hierarchical structures (directories, org charts) or recursive problem solving.
        3. LARGE DATASETS: Processing data that exceeds context limits by splitting (Map) and summarizing (Reduce).
        4. PARALLEL EXECUTION: Any task requiring massive parallel execution of sub-tasks.
        
        DO NOT USE FOR: Simple, linear tasks or single-file creation that fit in a single context window.
        """

    def prompt(self, user_id: str) -> str:
        return """You are a recursive Map-Reduce agent. Your GOAL is to solve the given 'task' completely and return the FINAL RESULT.
        
        ALGORITHM:
        1. ANALYZE: Understand the task (e.g., analyze a folder).
        2. MAP: Break it down into sub-tasks (e.g., read files in current dir, recursively call 'map-reduce' for sub-directories).
        3. EXECUTE: Run these sub-tasks using the available tools. Parallelize where possible.
        4. REDUCE: Collect ALL results from the sub-tasks.
        5. SYNTHESIZE: Combine them into a single, comprehensive final report.
        
        CRITICAL RULES:
        - ANTI-RECURSION: If your assigned task is T, DO NOT call 'map-reduce' with task T again. You must BREAK DOWN task T into smaller sub-tasks (t1, t2...) and delegate THOSE.
        - You are the one responsible for executing the atomic actions for T (e.g., gathering data, listing items) before delegating sub-parts.
        - Do NOT return "I am working on it". You must work on it UNTIL IT IS DONE.
        - Do NOT return partial results unless you have hit a hard limit.
        - Your final 'assistant' message MUST contain the complete answer/report.
        """

    def available_agents(self, user_id: str) -> List[BaseAgent]:
        # IMPORTANT: Return a NEW instance of MapReduceAgent instead of self.
        return [MapReduceAgent(max_iterations=self.max_iterations, agents=self.agents)] + self.agents

    def generate_messages_context(self, user_id: str, context: Context, input: MapReduceInput = None) -> List[Message]:
        msgs = super().generate_messages_context(user_id, context, input)
        msgs.append(Message(type="user", content=f"CURRENT TASK: {input.task}\n\nWARNING: Do not call 'map-reduce' with this exact same task '{input.task}' again, as it would cause an infinite loop. decompose it into smaller sub-tasks."))
        return msgs
