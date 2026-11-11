"""Adapter contract tests against local mocked HTTP servers."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cogplat.domain.chat import ChatMessage
from cogplat.providers.ollama import OllamaProvider
from cogplat.providers.openai_compat import OpenAICompatibleProvider


class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        body = json.dumps({"models": [{"name": "tiny:latest"}], "data": [{"id": "tiny"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson" if self.path == "/api/chat" else "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.path == "/api/chat":
            events = [
                {"message": {"content": "hello"}, "done": False},
                {"message": {"content": " world"}, "done": False},
                {"message": {}, "done": True},
            ]
            for event in events:
                self.wfile.write((json.dumps(event) + "\n").encode())
                self.wfile.flush()
        else:
            for event in [
                {"choices": [{"delta": {"content": "hello"}}]},
                {"choices": [{"delta": {"content": " world"}}]},
            ]:
                self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()


def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def test_ollama_adapter_lists_models_and_streams_tokens():
    httpd = server()
    try:
        provider = OllamaProvider(f"http://127.0.0.1:{httpd.server_port}")
        messages = [ChatMessage(role="user", content="hello")]
        async def exercise():
            models = await provider.list_models()
            tokens = [token async for token in provider.stream_chat("tiny:latest", messages)]
            return models, tokens
        models, tokens = asyncio.run(exercise())
        assert models == ["tiny:latest"]
        assert tokens == ["hello", " world"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_openai_compatible_adapter_streams_sse_tokens():
    httpd = server()
    try:
        provider = OpenAICompatibleProvider(f"http://127.0.0.1:{httpd.server_port}/v1")
        messages = [ChatMessage(role="user", content="hello")]
        tokens = asyncio.run(_collect(provider, messages))
        assert tokens == ["hello", " world"]
    finally:
        httpd.shutdown()
        httpd.server_close()


async def _collect(provider, messages):
    return [token async for token in provider.stream_chat("tiny", messages, api_key="test-secret")]
