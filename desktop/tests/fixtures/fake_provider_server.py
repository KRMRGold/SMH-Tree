"""Minimal fake-provider ASGI server for desktop end-to-end tests."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator

import uvicorn

from cogplat.config import load_settings
from cogplat.domain.chat import ChatMessage
from cogplat.main import create_app


class FakeProvider:
    label = "Desktop test provider"
    is_remote = False

    async def list_models(self) -> list[str]:
        return ["fake-model"]

    async def stream_chat(
        self, model: str, messages: list[ChatMessage], **options: object
    ) -> AsyncIterator[str]:
        yield "hello"
        yield " from "
        yield "SMH-Tree"

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", choices=("127.0.0.1",), default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    settings = load_settings()
    app = create_app(settings, providers={"fake": FakeProvider()})
    uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
