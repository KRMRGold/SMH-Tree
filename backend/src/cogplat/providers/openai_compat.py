"""OpenAI-compatible chat-completions streaming adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from cogplat.domain.chat import ChatMessage
from cogplat.providers._http import get_json, stream_lines
from cogplat.providers.base import ProviderError


class OpenAICompatibleProvider:
    label = "OpenAI-compatible"
    is_remote = True

    def __init__(self, base_url: str = "https://api.openai.com/v1", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _headers(api_key: object = None) -> dict[str, str]:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderError("A provider API key is required for this remote provider.")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key.strip()}",
        }

    async def list_models(self, **opts: object) -> list[str]:
        data = await get_json(
            f"{self.base_url}/models",
            self._headers(opts.get("api_key")),
            min(self.timeout, 15.0),
        )
        return [str(item["id"]) for item in data.get("data", []) if item.get("id")]

    async def stream_chat(
        self, model: str, messages: list[ChatMessage], **opts: object
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": True,
        }
        async for line in stream_lines(
            f"{self.base_url}/chat/completions",
            self._headers(opts.get("api_key")),
            payload,
            self.timeout,
        ):
            if not line or line.startswith(":") or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                item = json.loads(data)
            except json.JSONDecodeError as exc:
                raise ProviderError("OpenAI-compatible provider returned invalid SSE data.") from exc
            if item.get("error"):
                raise ProviderError("OpenAI-compatible provider reported a generation error.")
            choices = item.get("choices") or []
            if choices:
                content = (choices[0].get("delta") or {}).get("content")
                if content:
                    yield str(content)

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Embedding support is not part of M2.")
