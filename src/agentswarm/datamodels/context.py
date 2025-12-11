from pydantic import BaseModel, ConfigDict
import uuid
from typing import List, Optional

from .message import Message


class Context():
    trace_id: str
    step_id: str
    parent_step_id: Optional[str]
    messages: List[Message]
    store: dict
    thoughts: list[str]

    def __init__(self, trace_id: str, messages: List[Message], store: dict, thoughts: list[str], step_id: str = None, parent_step_id: str = None):
        self.trace_id = trace_id
        self.step_id = step_id if step_id else str(uuid.uuid4())
        self.parent_step_id = parent_step_id
        self.messages = messages
        self.store = store
        self.thoughts = thoughts

    def get_store(self, key: str):
        if self.store is None:
            return None
        return self.store.get(key)

    def set_store(self, key: str, value: any):
        if self.store is None:
            self.store = {}
        self.store[key] = value

    def has_store(self, key: str) -> bool:
        if self.store is None:
            return False
        return key in self.store

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
