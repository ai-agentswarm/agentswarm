from typing import Literal, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class Message(BaseModel):
    type: Literal["user", "assistant", "system", "execution"] = Field(alias="t")
    content: Any = Field(alias="c")
    
    model_config = ConfigDict(
        populate_by_name=True
    )
