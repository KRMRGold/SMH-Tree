"""Python-owned UUIDv7 identifiers (Python 3.12 compatible)."""

from __future__ import annotations

import secrets
import time
import uuid


def new_id() -> str:
    """Return a UUIDv7 string using a millisecond timestamp and random payload."""

    timestamp_ms = int(time.time_ns() // 1_000_000) & ((1 << 48) - 1)
    random_bits = secrets.randbits(74)
    rand_a = (random_bits >> 62) & 0xFFF
    rand_b = random_bits & ((1 << 62) - 1)

    value = (
        (timestamp_ms << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0b10 << 62)
        | rand_b
    )
    return str(uuid.UUID(int=value))


def is_uuid7(value: str) -> bool:
    """Return whether value parses as a UUID with version 7 and RFC variant."""

    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return parsed.version == 7 and parsed.variant == uuid.RFC_4122
