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
        model: str = "gemini-3.1-flash-lite",
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
        temperature: float = 0.0,
    ) -> LLMOutput:
        contents = []
        sys_instruct = []
        pending_tool_parts = []

        def flush_tools():
            if pending_tool_parts:
                contents.append(
                    types.Content(role="user", parts=list(pending_tool_parts))
                )
                pending_tool_parts.clear()

        for message in messages:
            if message.type == "system":
                sys_instruct.append(message.content)
                continue
            if message.type == "tool":
                resp = (
                    message.content
                    if isinstance(message.content, dict)
                    else {"result": message.content}
                )
                fr = types.FunctionResponse(name=message.name, response=resp)
                if message.tool_call_id:
                    try:
                        fr.id = message.tool_call_id
                    except Exception:
                        pass
                pending_tool_parts.append(types.Part(function_response=fr))
                continue
            flush_tools()
            if message.type in ("assistant", "completion"):
                parts = []
                if message.content:
                    parts.append(types.Part(text=message.content))
                for tc in (message.tool_calls or []):
                    fc = types.FunctionCall(name=tc.name, args=tc.arguments)
                    try:
                        fc.id = tc.id
                    except Exception:
                        pass
                    part = types.Part(function_call=fc)
                    if tc.thought_signature is not None:
                        part.thought_signature = tc.thought_signature
                    parts.append(part)
                # Gemini rejects any Content with an empty parts array
                # ("must include at least one parts field"). An assistant turn
                # with no text and no tool calls (e.g. an empty model response)
                # carries no information, so skip it entirely.
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            else:  # user / execution
                # Skip messages with no usable text: an empty/None content would
                # serialize to an empty part and trigger the same 400 error.
                if message.content:
                    contents.append(
                        types.Content(
                            role="user", parts=[types.Part(text=message.content)]
                        )
                    )
        flush_tools()
        if not sys_instruct:
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
            temperature=temperature,
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
                                    name=part.function_call.name,
                                    arguments=args,
                                    id=getattr(part.function_call, "id", None),
                                    thought_signature=getattr(part, "thought_signature", None),
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
                        cached_prompt_token_count=(
                            usg.cached_content_token_count
                            if usg.cached_content_token_count is not None
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
            cached_prompt_token_count=(
                usg.cached_content_token_count
                if usg.cached_content_token_count is not None
                else 0
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
                            name=part.function_call.name,
                            arguments=args,
                            id=getattr(part.function_call, "id", None),
                            thought_signature=getattr(part, "thought_signature", None),
                        )
                    )

        return LLMOutput(
            text="".join(text_parts), function_calls=output_function_calls, usage=usage
        )
