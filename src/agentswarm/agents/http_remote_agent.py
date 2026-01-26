import asyncio
import httpx
from typing import Optional, TypeVar

from .remote_agent import RemoteAgent, RemoteExecutionMode, RemoteExecutionHandler
from .base_agent import InputType, OutputType
from ..datamodels import Context


class HttpRemoteAgent(RemoteAgent[InputType, OutputType]):
    """
    Implementation of RemoteAgent that uses HTTP to communicate with the remote agent.
    """

    def __init__(
        self,
        base_url: str,
        remote_agent_id: str,
        mode: RemoteExecutionMode = RemoteExecutionMode.SYNC,
        timeout: float = 30.0,
    ):
        super().__init__(mode=mode)
        self.base_url = base_url.rstrip("/")
        self.remote_agent_id = remote_agent_id
        self.timeout = timeout

    def id(self) -> str:
        return f"remote_http_{self.remote_agent_id}"

    def description(self, user_id: str) -> str:
        return f"Remote agent proxy for {self.remote_agent_id}"

    def get_remote_agent_id(self) -> str:
        return self.remote_agent_id

    async def _call_remote_sync(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/execute", json=payload)
            response.raise_for_status()
            return response.json()

    async def _call_remote_async_init(self, payload: dict) -> RemoteExecutionHandler:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/execute/async", json=payload)
            response.raise_for_status()
            data = response.json()
            return RemoteExecutionHandler(
                handler_id=data["handler_id"], status=data.get("status", "pending")
            )

    async def _poll_for_result(
        self, handler: RemoteExecutionHandler, context: Context
    ) -> OutputType:
        interval = 1.0
        max_retries = 60  # 1 minute

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for _ in range(max_retries):
                response = await client.get(
                    f"{self.base_url}/execute/status/{handler.handler_id}"
                )
                response.raise_for_status()
                data = response.json()

                if data["status"] == "completed":
                    return self._process_remote_result(data, context)
                elif data["status"] == "failed":
                    raise RuntimeError(f"Remote execution failed: {data.get('error')}")

                await asyncio.sleep(interval)
                # Exponential backoff?
                interval = min(interval * 1.5, 10.0)

        raise TimeoutError("Remote execution timed out")
