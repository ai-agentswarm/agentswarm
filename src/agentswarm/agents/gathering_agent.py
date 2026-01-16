from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from ..datamodels import Context, StrResponse


class GatheringAgentInput(BaseModel):
    key: str = Field(description="The key of the information to gather")


class GatheringAgent(BaseAgent[GatheringAgentInput, StrResponse]):
    def id(self) -> str:
        return "gathering-agent"

    def description(self, user_id: str) -> str:
        return """
I'm able to gather an information from the store and add to the current context. 
USE THIS AGENT ONLY WHEN YOU NEED TO DISPLAY THE INFORMATION TO THE USER.
Whenever possible, if you need to filter or process the data, use the "transformer-agent".
        """

    async def execute(
        self, user_id: str, context: Context, input: GatheringAgentInput
    ) -> StrResponse:
        if not context.store.has(input.key):
            raise Exception(
                f"Information from the store with key {input.key} not found"
            )
        value = context.store.get(input.key)
        return StrResponse(value=value)
