from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING
from datetime import datetime
import json
import os
if TYPE_CHECKING:
    from ..datamodels.context import Context
from ..datamodels.store import Store



class Tracing(ABC):
    @abstractmethod
    def trace_agent(context: Context, agent_id: str, arguments: dict):
        pass

    @abstractmethod
    def trace_loop_step(context: Context, step_name: str):
        pass
    
    @abstractmethod
    def trace_agent_result(context: Context, agent_id: str, result: Any):
        pass
    
    @abstractmethod
    def trace_agent_error(context: Context, agent_id: str, error: Exception):
        pass



def _get_store_snapshot(store: Store) -> dict:
    """
    Returns a snapshot of the store.
    If TRACE_STORE_FULL is 'true', returns the full store.
    Otherwise, returns a summary with value types and sizes.
    """
    if os.getenv("TRACE_STORE_FULL", "false").lower() == "true":
        return store.items()
    
    summary = {}
    for key, value in store.items().items():
        val_str = str(value)
        size_str = f"{len(val_str) / 1024:.1f} KB" if len(val_str) > 1024 else f"{len(val_str)} B"
        summary[key] = f"<{type(value).__name__} | size: {size_str}> (set TRACE_STORE_FULL=true to see content)"
    return summary

class LocalTracing(Tracing):
    def __init__(self, trace_path: str = './traces'):
        self.trace_path = trace_path
    
    def trace_agent(self, context: Context, agent_id: str, arguments: dict):
        os.makedirs(self.trace_path, exist_ok=True)
        with open(os.path.join(self.trace_path, f"{context.trace_id}.json"), "a") as f:
            trace_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "agent",
                "step_id": context.step_id,
                "parent_step_id": context.parent_step_id,
                "agent_id": agent_id,
                "arguments": arguments,
                "messages": [message.model_dump() for message in context.messages],
                "store": _get_store_snapshot(context.store),
                "thoughts": context.thoughts
            }
            f.write(json.dumps(trace_data) + "\n")

    def trace_loop_step(self, context: Context, step_name: str):
        os.makedirs(self.trace_path, exist_ok=True)
        with open(os.path.join(self.trace_path, f"{context.trace_id}.json"), "a") as f:
            trace_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "loop_step",
                "step_id": context.step_id,
                "parent_step_id": context.parent_step_id,
                "agent_id": step_name, # Use agent_id field to store the step name for UI compatibility
                "arguments": {},
                "messages": [message.model_dump() for message in context.messages],
                "store": _get_store_snapshot(context.store),
                "thoughts": context.thoughts
            }
            f.write(json.dumps(trace_data) + "\n")

    def trace_agent_result(self, context: Context, agent_id: str, result: Any):
        os.makedirs(self.trace_path, exist_ok=True)
        with open(os.path.join(self.trace_path, f"{context.trace_id}.json"), "a") as f:
            
            serialized_result = None
            try:
                if hasattr(result, 'model_dump'):
                    serialized_result = result.model_dump(mode='json')
                elif hasattr(result, 'dict'):
                    serialized_result = result.dict()
                elif isinstance(result, list):
                    serialized_result = []
                    for item in result:
                        if hasattr(item, 'model_dump'):
                            serialized_result.append(item.model_dump(mode='json'))
                        elif hasattr(item, 'dict'):
                            serialized_result.append(item.dict())
                        else:
                            serialized_result.append(str(item))
                else:
                    serialized_result = str(result)
            except Exception:
                serialized_result = str(result)

            trace_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "agent_result",
                "step_id": context.step_id,
                "parent_step_id": context.parent_step_id,
                "agent_id": agent_id,
                "result": serialized_result,
                "messages": [message.model_dump() for message in context.messages],
                "store": _get_store_snapshot(context.store),
                "thoughts": context.thoughts
            }
            f.write(json.dumps(trace_data) + "\n")

    def trace_agent_error(self, context: Context, agent_id: str, error: Exception):
        os.makedirs(self.trace_path, exist_ok=True)
        with open(os.path.join(self.trace_path, f"{context.trace_id}.json"), "a") as f:
            trace_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "agent_error",
                "step_id": context.step_id,
                "parent_step_id": context.parent_step_id,
                "agent_id": agent_id,
                "error": str(error),
                "messages": [message.model_dump() for message in context.messages],
                "store": _get_store_snapshot(context.store),
                "thoughts": context.thoughts
            }
            f.write(json.dumps(trace_data) + "\n")
