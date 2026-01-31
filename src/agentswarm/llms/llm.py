from __future__ import annotations
from typing import List, Any, Optional
from pydantic import BaseModel, Field
from ..datamodels.message import Message
from ..datamodels.feedback import FeedbackSystem


class LLMFunction(BaseModel):
    name: str = Field(description="The name of the function")
    description: str = Field(description="The description of the function")
    parameters: dict = Field(description="The parameters of the function")


class LLMFunctionExecution(BaseModel):
    name: str = Field(description="The name of the function")
    arguments: dict = Field(description="The arguments of the function")


from .usage import LLMUsage


class LLMOutput(BaseModel):
    text: str = Field(description="The text of the output")
    function_calls: List[LLMFunctionExecution] = Field(
        description="The function calls to be executed"
    )
    usage: LLMUsage = Field(description="The usage of the LLM")


class LLM:
    async def generate(
        self,
        messages: List[Message],
        functions: List[LLMFunction] = None,
        feedback: Optional[FeedbackSystem] = None,
    ) -> LLMOutput:
        pass
