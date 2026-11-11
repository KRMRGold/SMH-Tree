"""Provider protocol and shared errors."""

from collections.abc import AsyncIterator
from typing import Protocol

from cogplat.domain.chat import ChatMessage


class ProviderError(Exception):
    """A provider request or response failed."""


class ModelProvider(Protocol):
    label: str
    is_remote: bool

    async def list_models(self, **opts: object) -> list[str]: ...

    async def stream_chat(
        self, model: str, messages: list[ChatMessage], **opts: object
    ) -> AsyncIterator[str]: ...

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]: ...
