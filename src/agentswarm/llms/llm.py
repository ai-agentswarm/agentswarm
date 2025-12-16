from typing import List, Any

from pydantic import BaseModel, Field
from ..datamodels.message import Message


class LLMFunction(BaseModel):
    name: str = Field(description="The name of the function")
    description: str = Field(description="The description of the function")
    parameters: dict = Field(description="The parameters of the function")

class LLMFunctionExecution(BaseModel):
    name: str = Field(description="The name of the function")
    arguments: dict = Field(description="The arguments of the function")

class LLMUsage(BaseModel):
    model: str = Field(description="The model of the LLM")
    prompt_token_count: int = Field(description="The number of tokens in the prompt", default=0)
    thoughts_token_count: int = Field(description="The number of tokens in the thoughts", default=0)
    tool_use_prompt_token_count: int = Field(description="The number of tokens in the tool use prompt", default=0)
    candidates_token_count: int = Field(description="The number of tokens in the candidates", default=0)
    total_token_count: int = Field(description="The total number of tokens", default=0)

class LLMOutput(BaseModel):
    text: str = Field(description="The text of the output")
    function_calls: List[LLMFunctionExecution] = Field(description="The function calls to be executed")
    usage: LLMUsage = Field(description="The usage of the LLM")

class LLM:
    async def generate(self, messages: List[Message], functions: List[LLMFunction] = None) -> LLMOutput:
        pass