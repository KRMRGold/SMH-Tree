"""Free-only OpenRouter provider."""

import re

from cogplat.domain.chat import ChatMessage
from cogplat.providers.base import ProviderError
from cogplat.providers.openai_compat import OpenAICompatibleProvider


FREE_ROUTER = "openrouter/free"
FREE_VARIANT = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+:free")


class OpenRouterFreeProvider(OpenAICompatibleProvider):
    label = "OpenRouter Free (remote)"

    def __init__(self):
        super().__init__("https://openrouter.ai/api/v1")

    async def list_models(self, **opts: object) -> list[str]:
        available = await super().list_models(**opts)
        free_variants = {model for model in available if FREE_VARIANT.fullmatch(model)}
        return [FREE_ROUTER, *sorted(free_variants)]

    def _chat_payload(self, model: str, messages: list[ChatMessage]) -> dict[str, object]:
        if model != FREE_ROUTER and not FREE_VARIANT.fullmatch(model):
            raise ProviderError("Choose the OpenRouter Free router or a model ending in :free.")
        payload = super()._chat_payload(model, messages)
        max_price = {"prompt": 0, "completion": 0}
        if any(message.images for message in messages):
            max_price["image"] = 0
        payload["provider"] = {"max_price": max_price}
        return payload
