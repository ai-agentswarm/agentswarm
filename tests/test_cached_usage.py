"""Tests for LLMUsage.cached_prompt_token_count and its population by GeminiLLM."""

from types import SimpleNamespace

import pytest
from google.genai import types
from pydantic import BaseModel, Field

from agentswarm.datamodels import Context, Message
from agentswarm.datamodels.feedback import Feedback, FeedbackSystem
from agentswarm.datamodels.store import Store
from agentswarm.llms import GeminiLLM, LLMUsage


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


# --- Helpers -----------------------------------------------------------------


def _response(text=None, usage=None) -> types.GenerateContentResponse:
    candidates = None
    if text is not None:
        candidates = [
            types.Candidate(
                content=types.Content(role="model", parts=[types.Part(text=text)])
            )
        ]
    return types.GenerateContentResponse(candidates=candidates, usage_metadata=usage)


class _FakeModels:
    """Stands in for client.aio.models; records nothing, makes no network calls."""

    def __init__(self, response=None, chunks=None):
        self._response = response
        self._chunks = chunks or []

    async def generate_content(self, **kwargs):
        return self._response

    async def generate_content_stream(self, **kwargs):
        async def _gen():
            for c in self._chunks:
                yield c

        return _gen()


def _llm(**kwargs) -> GeminiLLM:
    client = SimpleNamespace(aio=SimpleNamespace(models=_FakeModels(**kwargs)))
    return GeminiLLM(client=client, model="gemini-test")


class _SinkFeedback(FeedbackSystem):
    def __init__(self):
        self.events = []

    def push(self, feedback: Feedback):
        self.events.append(feedback)

    def subscribe(self, callback):
        pass

    def to_dict(self):
        return {}

    @classmethod
    def recreate(cls, config):
        return cls()


MESSAGES = [Message(type="user", content="hi")]


# --- GeminiLLM ---------------------------------------------------------------


async def test_non_streaming_reports_cached_tokens():
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=5000,
        cached_content_token_count=1200,
        candidates_token_count=10,
        total_token_count=5010,
    )
    out = await _llm(response=_response("ok", usage)).generate(MESSAGES)

    assert out.usage.cached_prompt_token_count == 1200
    # prompt_token_count stays the total prompt size (cached tokens included).
    assert out.usage.prompt_token_count == 5000


async def test_non_streaming_cached_none_gives_zero():
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=5000, cached_content_token_count=None
    )
    out = await _llm(response=_response("ok", usage)).generate(MESSAGES)

    assert out.usage.cached_prompt_token_count == 0
    assert out.usage.prompt_token_count == 5000


async def test_streaming_takes_cached_tokens_from_usage_chunk():
    chunks = [
        _response("Hel"),  # no usage_metadata
        _response("lo"),
        _response(
            None,
            types.GenerateContentResponseUsageMetadata(
                prompt_token_count=3000,
                cached_content_token_count=2048,
                total_token_count=3002,
            ),
        ),
    ]
    out = await _llm(chunks=chunks).generate(MESSAGES, feedback=_SinkFeedback())

    assert out.text == "Hello"
    assert out.usage.cached_prompt_token_count == 2048
    assert out.usage.prompt_token_count == 3000


# --- LLMUsage / Context ------------------------------------------------------


def test_llmusage_default_is_zero():
    u = LLMUsage(model="x")
    assert u.cached_prompt_token_count == 0


def _ctx(usage):
    return Context(trace_id="t", messages=[], store=MockStore(), tracing=None, usage=usage)


def test_context_round_trip_preserves_cached_tokens():
    ctx = _ctx([LLMUsage(model="x", prompt_token_count=5000, cached_prompt_token_count=1200)])
    restored = Context.from_dict(ctx.to_dict())

    assert restored.usage[0].cached_prompt_token_count == 1200
    assert restored.usage[0].prompt_token_count == 5000


def test_context_from_dict_without_field_defaults_to_zero():
    # Payload as produced by a 0.9.2 remote agent.
    data = _ctx([]).to_dict()
    data["usage"] = [{"model": "x", "prompt_token_count": 5000, "total_token_count": 5010}]
    restored = Context.from_dict(data)

    assert restored.usage[0].cached_prompt_token_count == 0


def test_older_llmusage_ignores_new_field():
    # Replica of the 0.9.2 LLMUsage: a new payload must validate, not be rejected.
    class LLMUsageV092(BaseModel):
        model: str = Field()
        prompt_token_count: int = 0
        thoughts_token_count: int = 0
        tool_use_prompt_token_count: int = 0
        candidates_token_count: int = 0
        total_token_count: int = 0

    payload = LLMUsage(model="x", prompt_token_count=5000, cached_prompt_token_count=1200).model_dump()
    old = LLMUsageV092.model_validate(payload)

    assert old.prompt_token_count == 5000
    assert not hasattr(old, "cached_prompt_token_count")
