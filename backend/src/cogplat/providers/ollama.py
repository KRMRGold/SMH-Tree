"""Ollama chat adapter using its newline-delimited JSON streaming API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from cogplat.domain.chat import ChatMessage
from cogplat.providers._http import get_json, stream_lines
from cogplat.providers.base import ProviderError


class OllamaProvider:
    label = "Ollama"
    is_remote = False

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def list_models(self, **opts: object) -> list[str]:
        data = await get_json(f"{self.base_url}/api/tags", {}, min(self.timeout, 15.0))
        return [str(item["name"]) for item in data.get("models", []) if item.get("name")]

    async def stream_chat(
        self, model: str, messages: list[ChatMessage], **opts: object
    ) -> AsyncIterator[str]:
        payload: dict[str, object] = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": True,
        }
        if "options" in opts and isinstance(opts["options"], dict):
            payload["options"] = opts["options"]

        async for line in stream_lines(
            f"{self.base_url}/api/chat",
            {"Content-Type": "application/json"},
            payload,
            self.timeout,
        ):
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProviderError("Ollama returned an invalid stream event.") from exc
            if item.get("error"):
                raise ProviderError("Ollama reported a generation error.")
            content = item.get("message", {}).get("content")
            if content:
                yield str(content)
            if item.get("done"):
                break

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Embedding support is not part of M2.")
