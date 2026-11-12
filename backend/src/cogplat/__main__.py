"""Command-line entry point used by the Electron desktop supervisor."""

from __future__ import annotations

import argparse

import uvicorn

from cogplat.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SMH-Tree local API.")
    parser.add_argument("--host", choices=("127.0.0.1",), default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        access_log=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
