from abc import abstractmethod
import traceback
import asyncio
from typing import List, TypeVar
import uuid

from pydantic import BaseModel
from .base_agent import BaseAgent
from ..llms import LLM, LLMFunction
from .gathering_agent import GatheringAgent
from .merge_agent import MergeAgent
from .transformer_agent import TransformerAgent
from .thinking_agent import ThinkingAgent
from ..datamodels import (
    Message,
    Context,
    KeyStoreResponse,
    ThoughtResponse,
    VoidResponse,
    StrResponse,
    CompletionResponse,
    ToolCall,
)

InputType = TypeVar("InputType", bound=BaseModel)
OutputType = TypeVar("OutputType", bound=BaseModel)


class ReActAgent(BaseAgent[InputType, OutputType]):

    def __init__(self, max_iterations: int = 100, max_concurrent_agents: int = 5):
        self.max_iterations = max_iterations
        self.max_concurrent_agents = max_concurrent_agents

    @abstractmethod
    def get_llm(self, user_id: str) -> LLM:
        """
        Returns the LLM to be used by the agent.
        """
        pass

    @abstractmethod
    def prompt(self, user_id: str) -> str:
        """
        Returns the prompt to be used by the agent.
        """
        pass

    def get_thinking_agent(self):
        """
        Returns the thinking agent to be used by the agent.
        """
        return ThinkingAgent()

    def get_default_agents(self) -> List[BaseAgent]:
        """
        Returns the default agents for implementing the ReActAgent loop.
        """
        return [
            self.get_thinking_agent(),
            GatheringAgent(),
            TransformerAgent(),
            MergeAgent(),
        ]

    @abstractmethod
    def available_agents(self, user_id: str) -> List[BaseAgent]:
        """
        Returns the available agents to be used by the agent.
        """
        pass

    async def on_agent_result(
        self, user_id: str, context: Context, agent_id: str, result
    ) -> None:
        """
        Hook called after an agent execution completes successfully.
        Override in subclasses to inspect or react to agent results.

        Args:
            user_id: The user ID for the current execution.
            context: The current execution context (with access to store, etc.).
            agent_id: The ID of the agent that was executed.
            result: The result returned by the agent (KeyStoreResponse, StrResponse, etc.).
        """
        pass

    def generate_function_calls(self, user_id: str) -> List[LLMFunction]:
        functions = []
        for agent in self.available_agents(user_id):
            try:
                functions.append(
                    LLMFunction(
                        name=agent.id(),
                        description=agent.description(user_id),
                        parameters=agent.input_parameters(),
                    )
                )
            except Exception as e:
                print(f"Error generating function call for agent {agent.id()}: {e}")
                print(traceback.format_exc())
        return functions

    async def agent_execution(
        self, user_id: str, context: Context, function: LLMFunction
    ):
        agent = next(
            (
                agent
                for agent in self.available_agents(user_id)
                if agent.id() == function.name
            ),
            None,
        )
        if agent is None:
            raise Exception(f"Agent {function.name} not found")

        input_type = agent._get_generic_type(0)
        if input_type and isinstance(function.arguments, dict):
            validated_input = input_type(**function.arguments)

            # Create a new context for the agent to support tracing hierarchy
            new_context = context.copy_for_execution()

            # Trace the agent execution
            context.tracing.trace_agent(new_context, agent.id(), function.arguments)

            try:
                result = await agent.execute(user_id, new_context, validated_input)
                context.tracing.trace_agent_result(new_context, agent.id(), result)
                return result
            except Exception as e:
                context.tracing.trace_agent_error(new_context, agent.id(), e)
                raise e
        raise Exception(f"Invalid arguments for agent {function.name}")

    def generate_messages_context(
        self, user_id: str, context: Context, input: InputType = None
    ) -> List[Message]:
        all: List[Message] = []
        all.append(Message(type="system", content=REACT_SYS_PROMPT))
        all.append(
            Message(
                type="system",
                content=f"Use the tool '{self.get_thinking_agent().id()}' IN PARALLEL to the other tools to explain your plan.",
            )
        )
        all.append(Message(type="system", content=self.prompt(user_id)))
        all.extend(context.messages)
        return all

    async def gather_with_concurrency(self, n, *tasks):
        """
        Runs tasks with a concurrency limit of n.
        """
        semaphore = asyncio.Semaphore(n)

        async def sem_task(task):
            async with semaphore:
                return await task

        return await asyncio.gather(*(sem_task(task) for task in tasks))

    async def execute(
        self, user_id: str, context: Context, input: InputType = None
    ) -> OutputType:

        current_context = self.generate_messages_context(user_id, context, input)
        iteration = 0

        while iteration < self.max_iterations:

            # Create an iteration step ID
            iteration_step_id = f"{context.step_id}_iter_{iteration}"

            # Trace the iteration start
            iter_context = context.copy_for_iteration(
                iteration_step_id, current_context
            )

            context.tracing.trace_loop_step(iter_context, f"Iteration {iteration}")

            tmp_context = current_context

            response = await self.get_llm(user_id).generate(
                tmp_context,
                functions=self.generate_function_calls(user_id),
                feedback=iter_context.feedback,
            )
            iter_context.add_usage(response.usage)

            if response.function_calls is None or len(response.function_calls) == 0:
                return [Message(type="assistant", content=response.text)]

            for fc in response.function_calls:
                if not getattr(fc, "id", None):
                    fc.id = uuid.uuid4().hex[
                        :9
                    ]  # 9 alnum: ok per Mistral, Gemini, Bedrock\

            assistant_turn = Message(
                type="assistant",
                content=response.text or "",
                tool_calls=[
                    ToolCall(
                        id=fc.id,
                        name=fc.name,
                        arguments=fc.arguments,
                        thought_signature=getattr(fc, "thought_signature", None),
                    )
                    for fc in response.function_calls
                ],
            )

            has_execution_tool = any(
                fc.name != self.get_thinking_agent().id()
                for fc in response.function_calls
            )

            tasks = [
                self.execute_and_handle_result(user_id, iter_context, fc, context)
                for fc in response.function_calls
            ]
            results = await self.gather_with_concurrency(
                self.max_concurrent_agents, *tasks
            )

            output = []
            for res in results:
                if res:
                    if res.type == "completion":
                        return [res]  # CompletionResponse terminates the loop
                    output.append(res)  # tool-result messages

            # (3) termination "with only thinking + final text": do NOT return internal tool-results
            if not has_execution_tool and response.text:
                return [Message(type="assistant", content=response.text)]

            current_context = current_context + [assistant_turn] + output
            iteration += 1

        raise Exception("Max iterations reached")

    async def execute_and_handle_result(
        self, user_id, iter_context, function_call, context
    ) -> Message:
        call_id = function_call.id
        name = function_call.name
        try:
            result = await self.agent_execution(user_id, iter_context, function_call)
            await self.on_agent_result(user_id, context, name, result)

            if isinstance(result, CompletionResponse):
                return Message(type="completion", content=result.value)

            if isinstance(result, Message):
                payload = result.content
            elif isinstance(result, ThoughtResponse):
                context.thoughts.append(result.thought)
                payload = f"Thought: {result.thought}"
            elif isinstance(result, VoidResponse) or result is None:
                payload = f"Agent {name} executed successfully."
            elif isinstance(result, KeyStoreResponse):
                payload = (
                    f"Agent {name} executed and stored {result.description} "
                    f"in the store with key {result.key}."
                )
            elif isinstance(result, StrResponse):
                payload = f"Agent {name} executed and returned {result.value}."
            else:
                payload = f"Result of agent {name} execution: {result}"

            return Message(
                type="tool", tool_call_id=call_id, name=name, content=payload
            )
        except Exception as e:
            return Message(
                type="tool",
                tool_call_id=call_id,
                name=name,
                content=f"Error executing agent {name}: {e}",
            )


REACT_SYS_PROMPT = """
You are an advanced AI agent capable of using multiple tools to solve complex tasks.

### KEY OPERATIONAL RULES:
1. **PARALLEL EXECUTION:** If you need to perform multiple independent actions (e.g., scraping two different URLs, or listing a dir and reading a file), you MUST execute them ALL in a single turn. Do not do them one by one.
2. **THINKING:** Always use the available thinking tool to explain your plan. This explanation should cover ALL the actions you are about to take in this turn.
3. **EFFICIENCY:** Minimize the number of turns. Gather as much information as possible in each step.
4. **CONTEXT MANAGEMENT:** Do not overload your context with massive raw data (like full HTML pages or large files). Use available tools to filter, summarize, or extract specific details from the raw data gathered by other agents. Only bring the final, relevant information into your main context.

### TRUTH AND DATA INTEGRITY:
1. **NO HALLUCINATIONS:** You must rely EXCLUSIVELY on the information returned by the tools. Do not use your internal training data to answer questions about specific external data (e.g., website content, file content, specific IDs).
2. **NO GUESSING:** Never guess parameters, IDs, or values. If you don't have a required parameter, ask the user or find it with another tool.
3. **ADMIT FAILURE:** If the tools do not provide the necessary information, simply state: "I could not find this information in the available records". Do not make up an answer. It is better to say "I don't know" than to lie.
"""
