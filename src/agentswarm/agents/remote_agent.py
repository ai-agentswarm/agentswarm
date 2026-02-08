from abc import abstractmethod
from enum import Enum
from typing import Any, Optional, TypeVar

from pydantic import BaseModel

from .base_agent import BaseAgent, InputType, OutputType
from ..datamodels import Context


class RemoteExecutionMode(Enum):
    SYNC = "sync"
    ASYNC = "async"


class RemoteExecutionHandler(BaseModel):
    """
    Handler for asynchronous remote execution.
    Can be used to poll for results.
    """

    handler_id: str
    status: str = "pending"
    result: Optional[Any] = None
    updated_context: Optional[dict] = None


class RemoteAgent(BaseAgent[InputType, OutputType]):
    """
    Base class for proxy agents that delegate execution to a remote environment.
    """

    def __init__(self, mode: RemoteExecutionMode = RemoteExecutionMode.SYNC):
        self.mode = mode

    @abstractmethod
    def get_remote_agent_id(self) -> str:
        """
        Returns the ID of the agent on the remote side (the Worker).
        This is used for routing the request to the correct implementation.
        It may differ from the local id() of this proxy agent to allow for
        versioning, aliases, or multi-region routing.
        """
        pass

    async def execute(
        self, user_id: str, context: Context, input: InputType = None
    ) -> OutputType:
        """
        Delegates execution to the remote environment.
        """
        # 1. Serialize context and input
        base_messages_count = len(context.messages)
        base_thoughts_count = len(context.thoughts)
        base_usage_count = len(context.usage)

        payload = {
            "user_id": user_id,
            "agent_id": self.get_remote_agent_id(),
            "context": context.to_dict(),
            "input": (
                (input.model_dump() if hasattr(input, "model_dump") else input)
                if input is not None
                else None
            ),
        }

        # 2. Call remote
        if self.mode == RemoteExecutionMode.SYNC:
            result_data = await self._call_remote_sync(payload)
            return self._process_remote_result(
                result_data,
                context,
                base_messages_count,
                base_thoughts_count,
                base_usage_count,
            )
        else:
            handler = await self._call_remote_async_init(payload)
            # For now, we might want to poll automatically if the user just awaits execute()
            # or return the handler if we change the return type.
            # But BaseAgent.execute expects OutputType.
            # So sync execution (awaiting it) should probably block/poll.
            return await self._poll_for_result(
                handler,
                context,
                base_messages_count,
                base_thoughts_count,
                base_usage_count,
            )

    @abstractmethod
    async def _call_remote_sync(self, payload: dict) -> dict:
        pass

    @abstractmethod
    async def _call_remote_async_init(self, payload: dict) -> RemoteExecutionHandler:
        pass

    @abstractmethod
    async def _poll_for_result(
        self,
        handler: RemoteExecutionHandler,
        context: Context,
        base_messages_count: int,
        base_thoughts_count: int,
        base_usage_count: int,
    ) -> OutputType:
        pass

    def _process_remote_result(
        self,
        result_data: dict,
        local_context: Context,
        base_messages_count: int,
        base_thoughts_count: int,
        base_usage_count: int,
    ) -> OutputType:
        """
        Updates the local context with remote changes and returns the result.
        """
        # Update messages
        remote_context_dict = result_data.get("updated_context")
        if remote_context_dict:
            remote_context = Context.from_dict(remote_context_dict)
            local_context.merge(
                remote_context,
                base_messages_count,
                base_thoughts_count,
                base_usage_count,
            )

        # Parse result
        output_type = self._get_generic_type(1)
        if output_type and "result" in result_data:
            if hasattr(output_type, "model_validate"):
                return output_type.model_validate(result_data["result"])
            return result_data["result"]

        return result_data.get("result")
