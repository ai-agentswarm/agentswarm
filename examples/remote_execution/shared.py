from agentswarm.datamodels import LocalStore
from agentswarm.utils.tracing import Tracing
from pydantic import BaseModel, Field

# --- Shared Models ---


class CalculatorInput(BaseModel):
    operation: str = Field(description="The operation to perform (add, sub, mul, div)")
    a: float
    b: float


# --- Serializable Components ---


import json
import os


class RemoteCompatibleStore(LocalStore):
    """
    A simple JSON-file based store to simulate a shared remote resource (like Redis)
    for the example.
    """

    def __init__(self, file_path="shared_store.json"):
        super().__init__()
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            self._save({})

    def _load(self):
        with open(self.file_path, "r") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f)

    def get(self, key: str) -> any:
        return self._load().get(key)

    def set(self, key: str, value: any):
        data = self._load()
        data[key] = value
        self._save(data)

    def items(self) -> dict[str, any]:
        return self._load()

    def to_dict(self) -> dict:
        return {"file_path": self.file_path}

    @classmethod
    def recreate(cls, config: dict) -> "RemoteCompatibleStore":
        return cls(config.get("file_path", "shared_store.json"))


class SilentTracing(Tracing):
    """
    A tracing implementation that does nothing but is serializable.
    """

    def trace_agent(self, context, agent_id, arguments):
        pass

    def trace_loop_step(self, context, step_name):
        pass

    def trace_agent_result(self, context, agent_id, result):
        pass

    def trace_agent_error(self, context, agent_id, error):
        pass

    def to_dict(self) -> dict:
        return {"silent": True}

    @classmethod
    def recreate(cls, config: dict) -> "SilentTracing":
        return cls()
