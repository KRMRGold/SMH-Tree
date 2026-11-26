"""Chat request and provider message contracts."""

import base64
import binascii
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, field_validator


MAX_CHAT_IMAGES = 4
MAX_CHAT_IMAGE_BYTES = 4 * 1024 * 1024
MAX_CHAT_IMAGE_TOTAL_BYTES = 8 * 1024 * 1024
MAX_CHAT_IMAGE_BASE64_LENGTH = 4 * ((MAX_CHAT_IMAGE_BYTES + 2) // 3)

ChatImageMediaType = Literal["image/png", "image/jpeg", "image/webp"]


class ChatImage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    media_type: ChatImageMediaType
    data: str = Field(min_length=1, max_length=MAX_CHAT_IMAGE_BASE64_LENGTH, repr=False)

    @field_validator("data")
    @classmethod
    def validate_image_data(cls, data: str, info: ValidationInfo) -> str:
        try:
            decoded = base64.b64decode(data, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Image data must be valid base64.") from exc
        if len(decoded) > MAX_CHAT_IMAGE_BYTES:
            raise ValueError("Each image must be 4 MiB or smaller.")
        if base64.b64encode(decoded).decode("ascii") != data:
            raise ValueError("Image data must be valid base64.")

        media_type = info.data.get("media_type")
        if media_type == "image/png":
            matches = decoded.startswith(b"\x89PNG\r\n\x1a\n")
        elif media_type == "image/jpeg":
            matches = decoded.startswith(b"\xff\xd8\xff")
        elif media_type == "image/webp":
            matches = decoded.startswith(b"RIFF") and decoded[8:12] == b"WEBP"
        else:
            return data
        if not matches:
            raise ValueError("Image data does not match its media type.")
        return data

    @property
    def byte_count(self) -> int:
        return len(self.data) // 4 * 3 - (len(self.data) - len(self.data.rstrip("=")))


def _check_image_total(images: list[ChatImage]) -> list[ChatImage]:
    if sum(image.byte_count for image in images) > MAX_CHAT_IMAGE_TOTAL_BYTES:
        raise ValueError("Images in a message must total 8 MiB or less.")
    return images


ChatImages = Annotated[list[ChatImage], Field(max_length=MAX_CHAT_IMAGES), AfterValidator(_check_image_total)]


class ChatMessage(BaseModel):
    role: str
    content: str
    images: ChatImages = Field(default_factory=list)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=200_000)
    provider: str = Field(default="ollama", min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    allow_remote: bool = False
    images: ChatImages = Field(default_factory=list)


class ClaimExtractionRequest(BaseModel):
    """Explicit model-assisted extraction request for one existing message."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="ollama", min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    allow_remote: bool = False
