"""Provider-neutral context compiler contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Sequence

from cogplat.domain.chat import ChatMessage

if TYPE_CHECKING:
    from cogplat.services.permissions import AccessContext


@dataclass(frozen=True, slots=True)
class CompileRequest:
    access_context: AccessContext
    current_user_message: str
    current_user_message_id: str
    history: Sequence[dict[str, object]]
    provider_id: str
    provider_label: str
    provider_is_remote: bool
    model: str
    max_input_tokens: int
    reserve_output_tokens: int
    compiler_version: str = "m5.0.0"


class TokenCounter(Protocol):
    def count_messages(self, messages: Sequence[ChatMessage]) -> int: ...


class DefaultTokenCounter:
    """Conservative character-based estimate with per-message role overhead."""

    def count_messages(self, messages: Sequence[ChatMessage]) -> int:
        return sum(4 + math.ceil(len(message.content) / 3.5) for message in messages)


@dataclass(slots=True)
class ContextPacket:
    messages: list[ChatMessage]
    included_sources: list[dict[str, object]]
    excluded_sources: list[dict[str, object]]
    token_estimate: int
    max_input_tokens: int
    reserve_output_tokens: int
    input_budget: int
    section_allocations: dict[str, int]
    transformations: list[dict[str, object]]
    provider_id: str
    provider_label: str
    model: str
    compiler_version: str

    @property
    def source_refs(self) -> list[str]:
        return [str(item["ref"]) for item in self.included_sources]

    def to_dict(self) -> dict[str, object]:
        return {
            "messages": [message.model_dump() for message in self.messages],
            "included_sources": self.included_sources,
            "excluded_sources": self.excluded_sources,
            "token_estimate": self.token_estimate,
            "max_input_tokens": self.max_input_tokens,
            "reserve_output_tokens": self.reserve_output_tokens,
            "input_budget": self.input_budget,
            "section_allocations": self.section_allocations,
            "transformations": self.transformations,
            "provider_id": self.provider_id,
            "provider_label": self.provider_label,
            "model": self.model,
            "compiler_version": self.compiler_version,
        }


class ContextCompileError(Exception):
    """A deterministic, inspectable failure to produce a valid context packet."""

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
