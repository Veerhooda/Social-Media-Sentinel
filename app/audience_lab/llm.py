"""Muse Spark client over the Meta Model API (OpenAI-compatible Chat Completions).

Every agent in the Audience Lab goes through ``LLMClient.chat_json``: a system
prompt, a user payload, an optional image, and a Pydantic model describing the
required output. The schema is sent as ``response_format=json_schema`` so the
provider constrains decoding; the reply is still validated locally and a single
repair round is attempted before failing explicitly.
"""
from __future__ import annotations

import json
import logging
import random
import threading
import time
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from app.audience_lab.config import AudienceLabSettings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504, 529}


class LLMError(RuntimeError):
    """The model could not produce a valid response (network, auth, schema)."""


class LLMClient(Protocol):
    model_name: str

    def chat_json(
        self, *, system: str, user: str, output: type[T], name: str,
        image_data_url: str | None = None, temperature: float | None = None,
        reasoning_effort: str | None = None,
    ) -> T: ...


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Inline $refs and mark every object strict (all keys required, no extras)."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].rsplit("/", 1)[-1]])
            out = {k: walk(v) for k, v in node.items() if k not in {"title", "default", "examples"}}
            if out.get("type") == "object" and "properties" in out:
                out["additionalProperties"] = False
                out["required"] = list(out["properties"].keys())
            return out
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(raw)


def _extract_text(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("Model response had no message content") from exc
    if isinstance(content, list):  # content-part style responses
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise LLMError("Model returned an empty message")
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()


class MuseSparkClient:
    def __init__(self, settings: AudienceLabSettings, session: requests.Session | None = None):
        if not settings.api_key:
            raise LLMError("META_MODEL_API_KEY is not configured")
        self.settings = settings
        self.model_name = settings.audience_lab_model
        self.http = session or requests.Session()
        self.url = settings.meta_model_base_url.rstrip("/") + "/chat/completions"
        self.on_retry: Callable[[str], None] | None = None
        self._local = threading.local()

    def last_usage(self) -> dict | None:
        """Token usage of the most recent call made from the current thread."""
        return getattr(self._local, "usage", None)

    def _retrying(self, reason: str) -> None:
        log.warning("Muse Spark call retrying: %s", reason)
        if self.on_retry:
            self.on_retry(reason)

    # -- transport -------------------------------------------------------
    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.settings.api_key}", "Content-Type": "application/json"}
        attempts = self.settings.audience_lab_max_retries + 1
        last_error = "unknown error"
        for attempt in range(attempts):
            try:
                response = self.http.post(self.url, headers=headers, json=body, timeout=self.settings.audience_lab_timeout_seconds)
            except requests.RequestException as exc:
                last_error = f"network error: {type(exc).__name__}"
            else:
                if response.status_code < 400:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise LLMError("Model API returned non-JSON body") from exc
                detail = response.text[:300]
                last_error = f"HTTP {response.status_code}: {detail}"
                if response.status_code in {400, 422} and "reasoning_effort" in body and "reasoning" in detail.lower():
                    raise _ReasoningUnsupported(last_error)
                if response.status_code in {400, 422} and "response_format" in body and _is_schema_rejection(detail):
                    raise _SchemaUnsupported(last_error)
                if response.status_code not in RETRYABLE:
                    raise LLMError(f"Model API rejected the request ({last_error})")
                retry_after = response.headers.get("retry-after")
                if attempt < attempts - 1 and retry_after and retry_after.replace(".", "", 1).isdigit():
                    self._retrying(last_error[:120])
                    time.sleep(min(float(retry_after), 30))
                    continue
            if attempt < attempts - 1:
                self._retrying(last_error[:120])
                time.sleep(min(2 ** attempt + random.random(), 20))
        raise LLMError(f"Model API unavailable after {attempts} attempts ({last_error})")

    def _post_adaptive(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._post(body)
        except _ReasoningUnsupported:
            log.warning("reasoning_effort rejected by the API; retrying without it")
            body.pop("reasoning_effort", None)
            return self._post(body)

    # -- public ----------------------------------------------------------
    def chat_json(
        self, *, system: str, user: str, output: type[T], name: str,
        image_data_url: str | None = None, temperature: float | None = None,
        reasoning_effort: str | None = None,
    ) -> T:
        self._local.usage = None
        started = time.monotonic()
        schema = strict_json_schema(output)
        user_content: Any = user
        if image_data_url:
            user_content = [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
        body: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.settings.audience_lab_temperature if temperature is None else temperature,
            "response_format": {"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}},
        }
        effort = reasoning_effort if reasoning_effort is not None else self.settings.audience_lab_reasoning_effort
        if effort:
            body["reasoning_effort"] = effort
        try:
            payload = self._post_adaptive(body)
        except _SchemaUnsupported:
            # Fall back to plain JSON mode with the schema carried in the prompt.
            log.warning("json_schema response_format rejected for %s; retrying with json_object", name)
            body["response_format"] = {"type": "json_object"}
            messages[0] = {"role": "system", "content": system + "\n\nReturn ONLY a JSON object matching this JSON Schema:\n" + json.dumps(schema)}
            payload = self._post_adaptive(body)

        self._local.usage = payload.get("usage")
        log.info("Muse Spark %s ok in %.1fs usage=%s", name, time.monotonic() - started, payload.get("usage"))
        text = _extract_text(payload)
        try:
            return output.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as first_error:
            log.warning("Invalid %s output, attempting one repair round", name)
            repair = dict(body)
            repair["messages"] = [*messages, {"role": "assistant", "content": text[:20000]}, {
                "role": "user",
                "content": "Your previous reply did not match the required JSON schema: "
                f"{str(first_error)[:800]}\nReturn the corrected JSON object only.",
            }]
            text = _extract_text(self._post_adaptive(repair))
            try:
                return output.model_validate(json.loads(text))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise LLMError(f"Model output for {name} did not match the schema") from exc


class _SchemaUnsupported(LLMError):
    pass


class _ReasoningUnsupported(LLMError):
    pass


def _is_schema_rejection(detail: str) -> bool:
    lowered = detail.lower()
    return any(token in lowered for token in ("response_format", "json_schema", "schema"))


def build_client(settings: AudienceLabSettings) -> LLMClient:
    return MuseSparkClient(settings)
