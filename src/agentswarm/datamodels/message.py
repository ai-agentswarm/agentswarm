from typing import Literal, Any, Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    id: str = Field(description="Stable id linking a tool call to its result")
    name: str = Field(description="The agent/function invoked")
    arguments: dict = Field(default_factory=dict)
    thought_signature: Optional[bytes] = None


class Message(BaseModel):
    type: Literal["user", "assistant", "system", "execution", "completion", "tool"] = (
        Field(alias="t")
    )
    content: Any = Field(alias="c", default=None)
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
