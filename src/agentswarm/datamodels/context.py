from __future__ import annotations
from pydantic import BaseModel, ConfigDict
import uuid
from typing import List, Optional, TYPE_CHECKING

from .message import Message
from ..llms.usage import LLMUsage
from .store import Store
from .feedback import Feedback, FeedbackSystem

if TYPE_CHECKING:
    from ..utils.tracing import Tracing
    from ..llms.llm import LLM


class Context:
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
    # Default LLM to use for the current context
    default_llm: Optional[LLM]
    # Reference to the tracing system
    tracing: Tracing
    # Reference to the feedback system
    feedback: Optional[FeedbackSystem]

    def __init__(
        self,
        trace_id: str,
        messages: List[Message],
        store: Store,
        tracing: Tracing,
        feedback: Optional[FeedbackSystem] = None,
        thoughts: list[str] = [],
        step_id: str = None,
        parent_step_id: str = None,
        default_llm: Optional[LLM] = None,
        usage: Optional[list[LLMUsage]] = None,
    ):
        self.trace_id = trace_id
        self.step_id = step_id if step_id else str(uuid.uuid4())
        self.parent_step_id = parent_step_id
        self.messages = messages
        self.store = store
        self.thoughts = thoughts if thoughts is not None else []
        self.default_llm = default_llm
        self.tracing = tracing
        self.feedback = feedback
        self.usage = usage if usage is not None else []

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
            default_llm=self.default_llm,
            tracing=self.tracing,
            feedback=self.feedback,
            usage=self.usage,
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
            default_llm=self.default_llm,
            tracing=self.tracing,
            feedback=self.feedback,
            usage=self.usage,
        )
        return iter_context

    def add_usage(self, usage: LLMUsage):
        """
        Add usage to the current context
        """
        self.usage.append(usage)

    def to_dict(self) -> dict:
        """
        Serializes the context to a dictionary.
        """
        from ..utils.serialization import serialize_component

        return {
            "trace_id": self.trace_id,
            "step_id": self.step_id,
            "parent_step_id": self.parent_step_id,
            "messages": [m.model_dump(by_alias=True) for m in self.messages],
            "store": serialize_component(self.store),
            "thoughts": self.thoughts,
            "usage": [u.model_dump() for u in self.usage],
            "tracing": serialize_component(self.tracing),
            "feedback": serialize_component(self.feedback),
        }

    @classmethod
    def from_dict(cls, data: dict, default_llm: Optional[LLM] = None) -> "Context":
        """
        Deserializes the context from a dictionary.
        """
        from ..utils.serialization import deserialize_component
        from ..utils.tracing import Tracing

        messages = [Message.model_validate(m) for m in data.get("messages", [])]
        usage = [LLMUsage.model_validate(u) for u in data.get("usage", [])]

        store = deserialize_component(data.get("store"), Store)

        tracing = deserialize_component(data.get("tracing"), Tracing)
        feedback = deserialize_component(data.get("feedback"), FeedbackSystem)

        return cls(
            trace_id=data["trace_id"],
            messages=messages,
            store=store,
            tracing=tracing,
            feedback=feedback,
            thoughts=data.get("thoughts", []),
            step_id=data.get("step_id"),
            parent_step_id=data.get("parent_step_id"),
            usage=usage,
            default_llm=default_llm,
        )

    def merge(
        self,
        remote_context: Context,
        base_messages_count: Optional[int] = None,
        base_thoughts_count: Optional[int] = None,
        base_usage_count: Optional[int] = None,
    ):
        """
        Merges the state from a remote context into this context.
        Ensures that messages, thoughts, and usage are appended/updated without breaking references.
        """
        # 1. Merge messages: append only new ones
        bm = (
            base_messages_count
            if base_messages_count is not None
            else len(self.messages)
        )
        if len(remote_context.messages) > bm:
            self.messages.extend(remote_context.messages[bm:])

        # 2. Merge thoughts: same logic
        bt = (
            base_thoughts_count
            if base_thoughts_count is not None
            else len(self.thoughts)
        )
        if len(remote_context.thoughts) > bt:
            self.thoughts.extend(remote_context.thoughts[bt:])

        # 3. Merge usage: same logic
        bu = base_usage_count if base_usage_count is not None else len(self.usage)
        if len(remote_context.usage) > bu:
            self.usage.extend(remote_context.usage[bu:])

    def emit_feedback(self, payload: Any, source: Optional[str] = None):
        """
        Emit a feedback event.
        If source is not specified, it could be inferred from the current context state if needed.
        """
        if self.feedback is None:
            return
        self.feedback.push(Feedback(source=source or "context", payload=payload))

    def debug_print(self) -> str:
        str_len = 100
        output = f"Messages ({len(self.messages)}):\n"
        for idx, message in enumerate(self.messages):
            content = message.content.replace("\n", " ")
            if len(content) > str_len:
                content = content[: (str_len - 3)] + "..."
            len_content = str_len - len(f"[{idx}] {message.type.upper()} ")
            output += f"[{idx}] {message.type.upper()} {'-'*len_content}\n"
            output += f"{content}\n"
            output += f"{'-'*str_len}\n"

        if self.store is not None and len(self.store) > 0:
            output += f"\nStore ({len(self.store)}):\n"
            output += f"{'-'*str_len}\n"
            for key, value in self.store.items():
                content = str(value).replace("\n", " ")
                if len(content) > str_len:
                    content = content[: (str_len - 3)] + "..."
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
