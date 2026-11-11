"""Pydantic contracts for scoped memory resources."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

MemoryScope = Literal["global", "user", "project", "conversation", "branch", "agent"]
MemoryKind = Literal["preference", "fact", "decision", "goal", "procedure", "open_question", "pattern"]
MemoryState = Literal["active", "outdated", "superseded", "archived"]
OriginKind = Literal["user", "agent", "extraction", "import"]

class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    scope: MemoryScope
    scope_id: str | None = None
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=200_000)
    importance: int = Field(default=3, ge=1, le=5)
    origin_kind: OriginKind = "user"
    origin_ref: str | None = Field(default=None, max_length=500)

class MemoryLifecycleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    state: Literal["outdated", "superseded", "archived"]
    superseded_by: str | None = None

    @model_validator(mode="after")
    def validate_superseded_by(self):
        if self.state == "superseded" and not self.superseded_by:
            raise ValueError("superseded_by is required when state is superseded")
        if self.state != "superseded" and self.superseded_by is not None:
            raise ValueError("superseded_by is only valid when state is superseded")
        return self

class MemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    id: str
    scope: MemoryScope
    scope_id: str | None
    kind: MemoryKind
    content: str
    importance: int
    state: MemoryState
    superseded_by: str | None
    origin_kind: OriginKind
    origin_ref: str | None
    created_at: str
    updated_at: str
