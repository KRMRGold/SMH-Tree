"""UTC timestamp helpers."""

from datetime import datetime, timezone


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp with millisecond precision."""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
