from .base_agent import BaseAgent
from ..datamodels import Context, ThoughtResponse
from pydantic import BaseModel, Field


class ThinkingInput(BaseModel):
    reasoning: str = Field(description="The detailed chain of thought regarding the current state and plan.")
    self_correction: str = Field(strict=False, description="Critique of previous actions (if any).")

class ThinkingAgent(BaseAgent[ThinkingInput, ThoughtResponse]):
    def id(self) -> str:
        return "thinking_tool"

    def description(self, user_id: str) -> str:
        return (
            "Use this tool to plan your actions. "
            "You MUST call this tool AND ALL other necessary action tools IN THE SAME TURN. "
            "Do not wait for the next turn to act. "
            "Plan for parallel execution where possible."
        )

    async def execute(self, user_id: str, context: Context, input_args: ThinkingInput) -> ThoughtResponse:
        part = ""
        if input_args.self_correction:
            part += f" Self-correction: {input_args.self_correction}"
        return ThoughtResponse(thought=f"{input_args.reasoning}.{part}")

