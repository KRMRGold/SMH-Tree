"""Chat request and provider message contracts."""

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=200_000)
    provider: str = Field(default="ollama", min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    allow_remote: bool = False
