import pytest
import uuid
from agentswarm.datamodels import Context, Message
from agentswarm.llms import LLMUsage
from agentswarm.datamodels.store import Store


class MockStore(Store):
    def items(self):
        return {}

    def to_dict(self):
        return {"type": "mock", "config": {}}

    def get(self, k):
        raise KeyError(k)

    def set(self, k, v):
        pass

    def has(self, k):
        return False

    def __len__(self):
        return 0

    @classmethod
    def recreate(cls, config):
        return cls()


def test_context_constructor_reference_sharing():
    """Verify that usage and thoughts lists are shared between contexts when copied."""
    usage = [LLMUsage(model="test", total_token_count=10)]
    thoughts = ["thought 1"]

    ctx1 = Context(
        trace_id="trace-1",
        messages=[],
        store=MockStore(),
        tracing=None,
        usage=usage,
        thoughts=thoughts,
    )

    # Copy for execution (should share usage/thoughts reference)
    ctx2 = ctx1.copy_for_execution()

    assert ctx2.usage is usage
    # thoughts are reset in copy_for_execution as it should be fresh for a new agent run
    assert ctx2.thoughts is not thoughts

    # Let's check copy_for_iteration
    ctx3 = ctx1.copy_for_iteration("step-2", [])
    assert ctx3.usage is usage
    assert ctx3.thoughts is thoughts


def test_context_merge_concurrency():
    """Verify that merge handles parallel updates correctly using base counts."""
    # Use MockStore to avoid RemoteExecutionNotSupportedError during to_dict()
    ctx_master = Context(
        trace_id="trace-1",
        messages=[Message(type="user", content="msg1")],
        store=MockStore(),
        tracing=None,
        usage=[LLMUsage(model="m1", total_token_count=5)],
    )

    # Snapshot base counts
    bm = len(ctx_master.messages)
    bu = len(ctx_master.usage)

    # Simulate Task A (remote)
    ctx_a_data = ctx_master.to_dict()
    ctx_a_data["messages"].append({"type": "assistant", "content": "resp A"})
    ctx_a_data["usage"].append({"model": "m-a", "total_token_count": 10})
    ctx_a = Context.from_dict(ctx_a_data)

    # Simulate Task B (remote)
    ctx_b_data = ctx_master.to_dict()
    ctx_b_data["messages"].append({"type": "assistant", "content": "resp B"})
    ctx_b_data["usage"].append({"model": "m-b", "total_token_count": 20})
    ctx_b = Context.from_dict(ctx_b_data)

    # Merge A first
    ctx_master.merge(ctx_a, base_messages_count=bm, base_usage_count=bu)
    assert len(ctx_master.messages) == 2
    assert len(ctx_master.usage) == 2

    # Merge B second (should not overwrite A)
    ctx_master.merge(ctx_b, base_messages_count=bm, base_usage_count=bu)
    assert len(ctx_master.messages) == 3
    assert len(ctx_master.usage) == 3

    assert ctx_master.messages[1].content == "resp A"
    assert ctx_master.messages[2].content == "resp B"


def test_context_serialization():
    """Verify context serialization and deserialization."""
    ctx = Context(
        trace_id="t1",
        messages=[Message(type="user", content="hello")],
        store=MockStore(),
        tracing=None,
        usage=[LLMUsage(model="m1", total_token_count=100)],
    )

    data = ctx.to_dict()
    assert data["trace_id"] == "t1"
    assert len(data["messages"]) == 1
    assert len(data["usage"]) == 1

    ctx2 = Context.from_dict(data)
    assert ctx2.trace_id == "t1"
    assert len(ctx2.messages) == 1
    assert ctx2.messages[0].content == "hello"
    assert len(ctx2.usage) == 1
    assert ctx2.usage[0].total_token_count == 100
