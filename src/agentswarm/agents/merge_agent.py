from typing import List
import uuid

from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from ..datamodels import Message, Context, KeyStoreResponse

class MergeAgentInput(BaseModel):
    keys: List[str] = Field(description="The list of keys to merge")

class MergeAgent(BaseAgent[MergeAgentInput, KeyStoreResponse]):
    def id(self) -> str:
        return "merge-agent"

    def description(self, user_id: str) -> str:
        return "I'm able to merge different informations into a single one."

    async def execute(self, user_id: str, context: Context, input: MergeAgentInput) -> KeyStoreResponse:
        values = [context.store.get(key) for key in input.keys]
        value = "\n".join(values)
        key = f"merged_{uuid.uuid4()}"
        context.store.set(key, value)
        return KeyStoreResponse(key=key, description=f"Merged information from keys {input.keys}")

    