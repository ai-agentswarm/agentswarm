import os
import uuid

from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from ..datamodels import Message, Context, KeyStoreResponse
from ..llms import GeminiLLM


class TransformerAgentInput(BaseModel):
    key: str = Field(description="The key of the information to transform")
    cmd: str = Field(
        description="""The command to execute to transform the information. 
Examples of cmd: 
- filter the data only for the keys that contain the word 'apple'
- make a short summary of the available data
- extract the email, name, surnamed and addresses
- obtain the tasks with the due date before 12/01/2025
YOU CAN NOT USE PYTHON OR ANY OTHER PROGRAMMING LANGUAGE TO SPECIFY THE COMMAND.
"""
    )


class TransformerAgent(BaseAgent[TransformerAgentInput, KeyStoreResponse]):
    def id(self) -> str:
        return "transformer-agent"

    def description(self, user_id: str) -> str:
        return """
I'm able to transform an information from the store into a new information in the store.
I can be used to apply complex llm-based task to the stored data, in order to optimize the general context.
        """

    async def execute(
        self, user_id: str, context: Context, input: TransformerAgentInput
    ) -> KeyStoreResponse:
        if not context.store.has(input.key):
            raise ValueError(f"Key {input.key} not found in store")

        value = context.store.get(input.key)
        all = [Message(type="user", content=f"{value}")]

        all.append(
            Message(
                type="user",
                content=f"Filter the previous data using this command:\n{input.cmd}\n. The ouput should be a new data, not a prompt or a python code. If not specified, you can optimize the output for your internal use.",
            )
        )

        llm = context.default_llm
        if llm is None:
            raise ValueError("Default LLM not set")
        response = await llm.generate(all)
        context.add_usage(response.usage)

        new_key = f"transformer_{uuid.uuid4()}"
        context.store.set(new_key, response.text)

        return KeyStoreResponse(
            key=new_key,
            description=f"Transformed information from key {input.key} with command {input.cmd}",
        )
