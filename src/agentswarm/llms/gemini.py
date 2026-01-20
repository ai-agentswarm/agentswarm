from typing import List, Any, Optional
import logging
from ..datamodels.message import Message
from .llm import LLM, LLMFunction, LLMFunctionExecution, LLMOutput, LLMUsage
from ..datamodels.feedback import Feedback, FeedbackSystem
from google.genai import Client, types

logging.getLogger("google_genai._api_client").setLevel(logging.WARNING)
logging.getLogger("google_genai.models").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


class GeminiLLM(LLM):

    def __init__(
        self,
        api_key: str = None,
        model: str = "gemini-3-flash-preview",
        client: Client = None,
    ):
        if api_key is None and client is None:
            raise ValueError("api_key or client must be provided")
        self.client = client if client is not None else Client(api_key=api_key)
        self.model = model

    async def generate(
        self,
        messages: List[Message],
        functions: List[LLMFunction] = None,
        feedback: Optional[FeedbackSystem] = None,
    ) -> LLMOutput:
        contents = []
        sys_instruct = []
        for message in messages:
            if message.type != "system":
                role = "model" if message.type == "assistant" else message.type
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=message.content)])
                )
            else:
                sys_instruct.append(message.content)
        if len(sys_instruct) == 0:
            sys_instruct = None

        function_declarations = []
        if functions is not None:
            for fn in functions:
                function_declarations.append(
                    {
                        "name": fn.name,
                        "description": fn.description,
                        "parameters": fn.parameters,
                    }
                )
            tools = [types.Tool(function_declarations=function_declarations)]
        else:
            tools = None

        config = types.GenerateContentConfig(
            temperature=0,
            tools=tools,
            system_instruction=sys_instruct,
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
                ),
            ],
        )

        if feedback:
            text_parts = []
            output_function_calls = []
            usage = None
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.model, config=config, contents=contents
            ):
                if (
                    chunk.candidates
                    and chunk.candidates[0].content
                    and chunk.candidates[0].content.parts
                ):
                    for part in chunk.candidates[0].content.parts:
                        if part.text:
                            text_parts.append(part.text)
                            feedback.push(Feedback(payload=part.text, source="llm"))
                        if part.function_call:
                            args = part.function_call.args
                            if args is not None and not isinstance(args, dict):
                                try:
                                    args = dict(args)
                                except Exception:
                                    pass
                            output_function_calls.append(
                                LLMFunctionExecution(
                                    name=part.function_call.name, arguments=args
                                )
                            )
                if chunk.usage_metadata:
                    usg = chunk.usage_metadata
                    usage = LLMUsage(
                        model=self.model,
                        prompt_token_count=(
                            usg.prompt_token_count
                            if usg.prompt_token_count is not None
                            else 0
                        ),
                        thoughts_token_count=(
                            usg.thoughts_token_count
                            if usg.thoughts_token_count is not None
                            else 0
                        ),
                        tool_use_prompt_token_count=(
                            usg.tool_use_prompt_token_count
                            if usg.tool_use_prompt_token_count is not None
                            else 0
                        ),
                        candidates_token_count=(
                            usg.candidates_token_count
                            if usg.candidates_token_count is not None
                            else 0
                        ),
                        total_token_count=(
                            usg.total_token_count
                            if usg.total_token_count is not None
                            else 0
                        ),
                    )
            return LLMOutput(
                text="".join(text_parts),
                function_calls=output_function_calls,
                usage=usage,
            )

        response = await self.client.aio.models.generate_content(
            model=self.model, config=config, contents=contents
        )

        usg = response.usage_metadata
        usage = LLMUsage(
            model=self.model,
            prompt_token_count=(
                usg.prompt_token_count if usg.prompt_token_count is not None else 0
            ),
            thoughts_token_count=(
                usg.thoughts_token_count if usg.thoughts_token_count is not None else 0
            ),
            tool_use_prompt_token_count=(
                usg.tool_use_prompt_token_count
                if usg.tool_use_prompt_token_count is not None
                else 0
            ),
            candidates_token_count=(
                usg.candidates_token_count
                if usg.candidates_token_count is not None
                else 0
            ),
            total_token_count=(
                usg.total_token_count if usg.total_token_count is not None else 0
            ),
        )

        output_function_calls = []
        text_parts = []
        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
                if part.function_call:
                    args = part.function_call.args
                    if args is not None and not isinstance(args, dict):
                        try:
                            args = dict(args)
                        except Exception:
                            pass
                    output_function_calls.append(
                        LLMFunctionExecution(
                            name=part.function_call.name, arguments=args
                        )
                    )

        return LLMOutput(
            text="".join(text_parts), function_calls=output_function_calls, usage=usage
        )
