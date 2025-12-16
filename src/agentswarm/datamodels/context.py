from pydantic import BaseModel, ConfigDict
import uuid
from typing import List, Optional

from .message import Message
from ..llms import LLMUsage, LLM
from .store import Store

class Context():
    """
    The Context class contains all the information of the current context, with the messages, store, usage and so on.
    Moreover, the Context contains informations about the tracing and current execution step.
    """

    # The trace_id is the unique identifier of the current trace.
    trace_id: str
    # The step_id is the unique identifier of the current step, inside the trace
    step_id: str
    # The parent_step_id is the unique identifier of the parent step, that originally creates this step
    parent_step_id: Optional[str]
    # The list of the messages of the current context
    messages: List[Message]
    # Reference to the current store
    store: Store
    # List of the thoughts generated in the current context by LLMs
    thoughts: list[str]
    # Total (current) usage of the context stack
    usage: list[LLMUsage]


    def __init__(self, trace_id: str, messages: List[Message], store: Store, thoughts: list[str], step_id: str = None, parent_step_id: str = None, default_llm: Optional[LLM] = None):
        self.trace_id = trace_id
        self.step_id = step_id if step_id else str(uuid.uuid4())
        self.parent_step_id = parent_step_id
        self.messages = messages
        self.store = store
        self.thoughts = thoughts
        self.default_llm = default_llm

    def copy_for_execution(self):
        """
        Copy the current context for a new (clean) execution.
        The new context will have a cleaned messages list and thoughts, and will have a new step_id.
        The parent_step_id of the new context will be the current step_id, in order to trace the execution hierarchy.

        The store and the default_llm will remain the same.
        """
        new_context = Context(
            trace_id=self.trace_id,
            messages=[],
            store=self.store,
            thoughts=[],
            parent_step_id=self.step_id,
            default_llm=self.default_llm
        )
        return new_context

    def copy_for_iteration(self, step_id: str, messages: List[Message]):
        """
        Copy the current context for a new iteration with the specified step_id and messages.
        The new context will have the same messages and thoughts.
        The parent_step_id of the new context will be the current step_id, in order to trace the iteration hierarchy.

        The store and the default_llm will remain the same.
        """
        iter_context = Context(
            trace_id=self.trace_id,
            messages=messages,
            store=self.store,
            thoughts=self.thoughts,
            step_id=step_id,
            parent_step_id=self.step_id,
            default_llm=self.default_llm
        )
        return iter_context

    def debug_print(self) -> str:
        str_len = 100
        output = f"Messages ({len(self.messages)}):\n"
        for idx, message in enumerate(self.messages):
            content = message.content.replace('\n', ' ')
            if len(content) > str_len:
                content = content[:(str_len-3)] + "..."
            len_content = str_len -len(f"[{idx}] {message.type.upper()} ")
            output += f"[{idx}] {message.type.upper()} {'-'*len_content}\n"
            output += f"{content}\n"
            output += f"{'-'*str_len}\n"

        if self.store is not None and len(self.store) > 0:
            output += f"\nStore ({len(self.store)}):\n"
            output += f"{'-'*str_len}\n"
            for key, value in self.store.items():
                content = str(value).replace('\n', ' ')
                if len(content) > str_len:
                    content = content[:(str_len-3)] + "..."
                output += f"{key}: {content}\n"
            output += f"{'-'*str_len}\n"
        else:
            output += f"\nStore (0):\n"
            output += f"{'-'*str_len}\n"
            output += "Empty\n"
            output += f"{'-'*str_len}\n"

        if self.thoughts is not None and len(self.thoughts) > 0:
            output += f"\nThoughts:\n"
            output += f"{'-'*str_len}\n"
            for thought in self.thoughts:
                output += f"💭 {thought}\n"
            output += f"{'-'*str_len}\n"

        return output
