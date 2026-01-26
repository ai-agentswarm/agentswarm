from typing import Dict, Any, List, Optional, Callable
import asyncio

from ..datamodels import Context
from ..agents.base_agent import BaseAgent
from ..llms import LLM


class RemoteAgentHandler:
    """
    Utility to handle incoming remote execution requests.
    Used on the remote side (worker) to execute local agents.
    """

    def __init__(self, agents: List[BaseAgent], default_llm: Optional[LLM] = None):
        self.agents = {agent.id(): agent for agent in agents}
        self.default_llm = default_llm

    async def handle_execute(self, payload: dict) -> dict:
        """
        Handles a synchronous execution request.
        """
        user_id = payload["user_id"]
        agent_id = payload["agent_id"]
        context_dict = payload["context"]
        input_dict = payload.get("input")

        # 1. Locate agent
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # 2. Deserialize context and input
        context = Context.from_dict(context_dict, default_llm=self.default_llm)

        # Parse input if provided and agent expects it
        input_obj = None
        if input_dict:
            input_type = agent._get_generic_type(0)
            if input_type:
                input_obj = input_type.model_validate(input_dict)

        # 3. Execute agent
        result = await agent.execute(user_id, context, input=input_obj)

        # 4. Serialize result and updated context
        serialized_result = None
        if hasattr(result, "model_dump"):
            serialized_result = result.model_dump()
        else:
            serialized_result = result

        return {"result": serialized_result, "updated_context": context.to_dict()}

    # ASYNC handling is more complex as it requires persistent state for handlers.
    # This might be left as a skeleton or implemented with a simple dict for mock purposes.
    # In a real cloud env, this would use a task queue (Celery, etc.)
