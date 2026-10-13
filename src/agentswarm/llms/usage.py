from pydantic import BaseModel, Field


class LLMUsage(BaseModel):
    model: str = Field(description="The model of the LLM")
    prompt_token_count: int = Field(
        description="The number of tokens in the prompt", default=0
    )
    thoughts_token_count: int = Field(
        description="The number of tokens in the thoughts", default=0
    )
    tool_use_prompt_token_count: int = Field(
        description="The number of tokens in the tool use prompt", default=0
    )
    candidates_token_count: int = Field(
        description="The number of tokens in the candidates", default=0
    )
    total_token_count: int = Field(description="The total number of tokens", default=0)
    cached_prompt_token_count: int = Field(
        description=(
            "Prompt tokens served from the provider cache. Subset of prompt_token_count, "
            "not additive. 0 when the provider does not report it."
        ),
        default=0,
    )
