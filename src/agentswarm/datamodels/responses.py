from pydantic import BaseModel, ConfigDict, Field
from typing import List
from .message import Message


class KeyStoreResponse(BaseModel):
    """
    The response of an agent that stores something in the store.
    """

    key: str = Field(description="the key of the property stored in the store")
    description: str = Field(
        description="the description of the property stored in the store"
    )


class VoidResponse(BaseModel):
    """
    The response of an agent that does not return anything.
    """

    pass


class StrResponse(BaseModel):
    """
    The response of an agent that returns a simple string, that should be elaborated
    """

    value: str = Field(description="The value of the response.")


class ThoughtResponse(BaseModel):
    """
    Encapsulate the thought of an agent.
    """

    thought: str = Field(description="The thought of the agent.")


class CompletionResponse(BaseModel):
    """
    The response of an agent that returns a completion.
    When returned by an agent used in a ReActAgent loop, will terminate the loop,
    and return the value as the final result.
    """

    value: str = Field(description="The value of the response.")
