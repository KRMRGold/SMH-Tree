"""Pydantic request contracts for M1 conversation resources."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    project_id: str | None = None


class BranchFork(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_branch_id: str
    fork_message_id: str
    name: str = Field(min_length=1, max_length=200)


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system", "tool"]
    participant: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200_000)
    model_ref: str | None = Field(default=None, max_length=500)
