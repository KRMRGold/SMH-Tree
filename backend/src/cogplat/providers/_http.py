"""Small standard-library HTTP helpers; no extra runtime dependency is needed."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import AsyncIterator
from typing import Any

from cogplat.providers.base import ProviderError


def _open(url: str, method: str, headers: dict[str, str], body: bytes | None, timeout: float):
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise ProviderError(f"Provider returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError("Could not connect to the model provider.") from exc


async def get_json(url: str, headers: dict[str, str], timeout: float = 15.0) -> Any:
    response = await asyncio.to_thread(_open, url, "GET", headers, None, timeout)
    try:
        raw = await asyncio.to_thread(response.read)
    finally:
        await asyncio.to_thread(response.close)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("Provider returned invalid JSON.") from exc


async def stream_lines(
    url: str, headers: dict[str, str], payload: dict[str, object], timeout: float = 120.0
) -> AsyncIterator[str]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    response = await asyncio.to_thread(_open, url, "POST", headers, body, timeout)
    try:
        while True:
            line = await asyncio.to_thread(response.readline)
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\r\n")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError("The provider stream was interrupted.") from exc
    finally:
        await asyncio.to_thread(response.close)
