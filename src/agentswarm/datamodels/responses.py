from pydantic import BaseModel, ConfigDict, Field
from typing import List
from .message import Message

class Response(BaseModel):
    messages: List[Message] = Field(alias="msgs", default=None, description="The messages to return to the user. It can be null")
    key: str = Field(alias="key", description="If an agent store something, it can return just the corresponing key in this property.")

class KeyStoreResponse(BaseModel):
    key: str = Field(description="the key of the property stored in the store")
    description: str = Field(description="the description of the property stored in the store")

class VoidResponse(BaseModel):
    pass

class ThoughtResponse(BaseModel):
    thought: str = Field(description="The thought of the agent.")