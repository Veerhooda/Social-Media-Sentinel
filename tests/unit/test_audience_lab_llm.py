from __future__ import annotations

import copy
import json

import pytest

from app.audience_lab.config import AudienceLabSettings
from app.audience_lab.llm import LLMError, MuseSparkClient, strict_json_schema
from app.audience_lab.schemas import SegmentReaction, SimulationRequest


class FakeResponse:
    def __init__(self, status: int, body: dict | str):
        self.status_code = status
        self._body = body
        self.headers: dict[str, str] = {}

    @property
    def text(self) -> str:
        return self._body if isinstance(self._body, str) else json.dumps(self._body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError
        return self._body


class FakeHTTP:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def post(self, url, headers, json, timeout):  # noqa: A002 - mirrors requests
        self.calls.append({"url": url, "headers": headers, "json": copy.deepcopy(json)})
        return self.responses.pop(0)


def _settings(**kw) -> AudienceLabSettings:
    return AudienceLabSettings(_env_file=None, META_MODEL_API_KEY="test-key", audience_lab_max_retries=2, **kw)


def _content(obj) -> dict:
    return {"choices": [{"message": {"content": json.dumps(obj)}}]}


VALID_REACTION = {
    "first_impression": "ok",
    "reaction_mix_pct": {"positive": 50, "neutral": 30, "negative": 10, "sarcastic": 10},
    "interested_pct": 40, "engage_pct": 20, "share_pct": 5,
    "interested_subgroups": [{"who": "devs", "why": "tools", "share_of_segment_pct": 30}],
    "sample_reactions": [{"voice": "dev", "tone": "positive", "text": "nice"}],
    "what_works": ["clear"], "what_fails": [], "misread_risks": [],
    "suggested_edits": [{"change": "add link", "expected_effect": "more clicks"}],
    "confidence": "medium", "confidence_reason": "moderate evidence",
}


def test_strict_schema_inlines_refs_and_requires_every_key():
    schema = strict_json_schema(SegmentReaction)
    assert "$defs" not in json.dumps(schema) and "$ref" not in json.dumps(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    mix = schema["properties"]["reaction_mix_pct"]
    assert mix["additionalProperties"] is False and set(mix["required"]) == {"positive", "neutral", "negative", "sarcastic"}


def test_client_sends_openai_compatible_request_with_schema_and_image():
    http = FakeHTTP([FakeResponse(200, _content(VALID_REACTION))])
    client = MuseSparkClient(_settings(audience_lab_reasoning_effort="low"), session=http)
    result = client.chat_json(system="sys", user="post", output=SegmentReaction, name="segment_reaction",
                              image_data_url="data:image/png;base64,AAAA")
    assert result.interested_pct == 40
    call = http.calls[0]
    assert call["url"] == "https://api.meta.ai/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer test-key"
    body = call["json"]
    assert body["model"] == "muse-spark-1.3-contributor"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["name"] == "segment_reaction"
    assert body["reasoning_effort"] == "low"
    assert body["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png")


def test_client_retries_transient_errors(monkeypatch):
    monkeypatch.setattr("app.audience_lab.llm.time.sleep", lambda *_: None)
    http = FakeHTTP([FakeResponse(503, "busy"), FakeResponse(429, "slow"), FakeResponse(200, _content(VALID_REACTION))])
    client = MuseSparkClient(_settings(), session=http)
    assert client.chat_json(system="s", user="u", output=SegmentReaction, name="r").engage_pct == 20
    assert len(http.calls) == 3


def test_client_fails_explicitly_on_auth_error():
    http = FakeHTTP([FakeResponse(401, {"error": "bad key"})])
    client = MuseSparkClient(_settings(), session=http)
    with pytest.raises(LLMError, match="401"):
        client.chat_json(system="s", user="u", output=SegmentReaction, name="r")


def test_client_falls_back_to_json_object_when_schema_mode_rejected():
    http = FakeHTTP([FakeResponse(400, {"error": "response_format json_schema not supported"}), FakeResponse(200, _content(VALID_REACTION))])
    client = MuseSparkClient(_settings(), session=http)
    client.chat_json(system="s", user="u", output=SegmentReaction, name="r")
    assert http.calls[1]["json"]["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in http.calls[1]["json"]["messages"][0]["content"]


def test_client_repairs_invalid_output_once_then_fails():
    bad = {"choices": [{"message": {"content": "```json\n{\"first_impression\": 1}\n```"}}]}
    http = FakeHTTP([FakeResponse(200, bad), FakeResponse(200, _content(VALID_REACTION))])
    client = MuseSparkClient(_settings(), session=http)
    assert client.chat_json(system="s", user="u", output=SegmentReaction, name="r").share_pct == 5
    http = FakeHTTP([FakeResponse(200, bad), FakeResponse(200, bad)])
    with pytest.raises(LLMError, match="did not match"):
        MuseSparkClient(_settings(), session=http).chat_json(system="s", user="u", output=SegmentReaction, name="r")


def test_missing_key_is_unavailable_not_silent():
    with pytest.raises(LLMError, match="META_MODEL_API_KEY"):
        MuseSparkClient(AudienceLabSettings(_env_file=None))


def test_simulation_request_validation():
    assert SimulationRequest(text="  hi  ", platform="YouTube").platform == "youtube"
    with pytest.raises(ValueError):
        SimulationRequest(text="hi", platform="not a platform!")
    with pytest.raises(ValueError):
        SimulationRequest(text="hi", image_data_url="http://example.com/a.png")


def test_retries_are_reported_and_usage_recorded(monkeypatch):
    monkeypatch.setattr("app.audience_lab.llm.time.sleep", lambda *_: None)
    ok = _content(VALID_REACTION) | {"usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    http = FakeHTTP([FakeResponse(503, "busy"), FakeResponse(200, ok)])
    client = MuseSparkClient(_settings(), session=http)
    seen: list[str] = []
    client.on_retry = seen.append
    client.chat_json(system="s", user="u", output=SegmentReaction, name="r")
    assert len(seen) == 1 and "503" in seen[0]
    assert client.last_usage() == {"prompt_tokens": 10, "completion_tokens": 5}


def test_per_call_reasoning_effort_and_fallback_when_rejected():
    http = FakeHTTP([FakeResponse(400, {"error": "unknown parameter reasoning_effort"}), FakeResponse(200, _content(VALID_REACTION))])
    client = MuseSparkClient(_settings(), session=http)
    client.chat_json(system="s", user="u", output=SegmentReaction, name="r", reasoning_effort="low")
    assert http.calls[0]["json"]["reasoning_effort"] == "low"
    assert "reasoning_effort" not in http.calls[1]["json"]
