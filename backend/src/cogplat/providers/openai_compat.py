"""OpenAI-compatible chat-completions streaming adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from urllib.error import HTTPError

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

    def _chat_payload(self, model: str, messages: list[ChatMessage]) -> dict[str, object]:
        wire_messages = []
        for message in messages:
            if not message.images:
                wire_messages.append({"role": message.role, "content": message.content})
                continue

            parts = [{"type": "text", "text": message.content}]
            for image in message.images:
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{image.media_type};base64,{image.data}"},
                })
            wire_messages.append({"role": message.role, "content": parts})

        return {
            "model": model,
            "messages": wire_messages,
            "stream": True,
        }

    async def stream_chat(
        self, model: str, messages: list[ChatMessage], **opts: object
    ) -> AsyncIterator[str]:
        payload = self._chat_payload(model, messages)
        headers = self._headers(opts.get("api_key"))
        has_images = any(message.images for message in messages)
        image_error = "The provider could not process the image request. Check that the model supports images."
        try:
            async for line in stream_lines(
                f"{self.base_url}/chat/completions",
                headers,
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
                    raise ProviderError(image_error if has_images else "OpenAI-compatible provider reported a generation error.")
                choices = item.get("choices") or []
                if choices:
                    content = (choices[0].get("delta") or {}).get("content")
                    if content:
                        yield str(content)
        except ProviderError as exc:
            if has_images:
                cause = exc.__cause__
                if isinstance(cause, HTTPError) and cause.code in {400, 404, 415, 422}:
                    raise ProviderError(image_error) from None
                raise exc from None
            raise

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Embedding support is not part of M2.")
