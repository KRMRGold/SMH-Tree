"""Adapter contract tests against local mocked HTTP servers."""

import asyncio
import io
import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError

import pytest

from cogplat.domain.chat import ChatImage, ChatMessage
from cogplat.providers import _http, ollama, openai_compat
from cogplat.providers.base import ProviderError
from cogplat.providers.ollama import OllamaProvider
from cogplat.providers.openai_compat import OpenAICompatibleProvider
from cogplat.providers.openrouter import OpenRouterFreeProvider


PNG_DATA = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAAZ/lpQAAAAASUVORK5CYII="
)


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


def test_openrouter_lists_free_models_and_sends_zero_price_request(monkeypatch):
    async def catalog(url, headers, timeout):
        assert url == "https://openrouter.ai/api/v1/models"
        assert headers["Authorization"] == "Bearer test-secret"
        return {"data": [
            {"id": "example/model"},
            {"id": "@preset/example:free"},
            {"id": "openrouter/auto"},
            {"id": "example/model:free"},
            {"id": "openrouter/free"},
        ]}

    async def stream(url, headers, payload, timeout):
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-secret"
        assert payload["model"] in {"openrouter/free", "example/model:free"}
        assert "models" not in payload
        assert payload["provider"] == {"max_price": {"prompt": 0, "completion": 0}}
        yield 'data: {"choices":[{"delta":{"content":"hello"}}]}'
        yield "data: [DONE]"

    monkeypatch.setattr(openai_compat, "get_json", catalog)
    monkeypatch.setattr(openai_compat, "stream_lines", stream)
    provider = OpenRouterFreeProvider()
    assert provider.is_remote

    async def exercise():
        options = {"api_key": "test-secret"}
        messages = [ChatMessage(role="user", content="hello")]
        models = await provider.list_models(**options)
        assert models == ["openrouter/free", "example/model:free"]
        for model in models:
            assert [token async for token in provider.stream_chat(model, messages, **options)] == ["hello"]
        for model in ["example/model", "openrouter/auto", "@preset/example:free"]:
            with pytest.raises(ProviderError, match=":free"):
                _ = [token async for token in provider.stream_chat(model, messages, **options)]

    asyncio.run(exercise())


def test_ollama_sends_images_as_base64_and_preserves_text_only_options(monkeypatch):
    requests = []

    async def stream(url, headers, payload, timeout):
        assert url == "http://127.0.0.1:11434/api/chat"
        requests.append(payload)
        yield '{"message":{"content":"hello"},"done":true}'

    monkeypatch.setattr(ollama, "stream_lines", stream)
    history = ChatMessage(role="assistant", content="What should I look at?")
    user = ChatMessage(
        role="user",
        content="Describe this image.",
        images=[ChatImage(media_type="image/png", data=PNG_DATA)],
    )

    async def exercise():
        provider = OllamaProvider()
        assert [token async for token in provider.stream_chat("vision", [history, user])] == ["hello"]
        assert [
            token async for token in provider.stream_chat(
                "text", [history], options={"temperature": 0}, claim_extraction=True
            )
        ] == ["hello"]

    asyncio.run(exercise())
    assert requests == [
        {
            "model": "vision",
            "messages": [
                {"role": "assistant", "content": "What should I look at?"},
                {"role": "user", "content": "Describe this image.", "images": [PNG_DATA]},
            ],
            "stream": True,
        },
        {
            "model": "text",
            "messages": [{"role": "assistant", "content": "What should I look at?"}],
            "stream": True,
            "format": "json",
            "think": False,
            "options": {"temperature": 0},
        },
    ]


@pytest.mark.parametrize(
    ("provider_type", "model"),
    [
        (OpenAICompatibleProvider, "vision"),
        (OpenRouterFreeProvider, "openrouter/free"),
        (OpenRouterFreeProvider, "example/vision:free"),
    ],
)
def test_openai_compatible_sends_image_data_url_and_preserves_free_cap(monkeypatch, provider_type, model):
    requests = []

    async def stream(url, headers, payload, timeout):
        assert url == f"{provider.base_url}/chat/completions"
        assert headers["Authorization"] == "Bearer test-secret"
        requests.append(payload)
        yield 'data: {"choices":[{"delta":{"content":"hello"}}]}'
        yield "data: [DONE]"

    monkeypatch.setattr(openai_compat, "stream_lines", stream)
    provider = provider_type()
    messages = [
        ChatMessage(role="system", content="Describe the input."),
        ChatMessage(
            role="user",
            content="What is this?",
            images=[ChatImage(media_type="image/png", data=PNG_DATA)],
        ),
    ]

    async def exercise():
        options = {"api_key": "test-secret"}
        assert [token async for token in provider.stream_chat(model, messages, **options)] == ["hello"]
        if provider_type is OpenRouterFreeProvider:
            with pytest.raises(ProviderError, match=":free"):
                _ = [token async for token in provider.stream_chat("example/paid", messages, **options)]

    asyncio.run(exercise())
    expected = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Describe the input."},
            {"role": "user", "content": [
                {"type": "text", "text": "What is this?"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{PNG_DATA}"}},
            ]},
        ],
        "stream": True,
    }
    if provider_type is OpenRouterFreeProvider:
        expected["provider"] = {"max_price": {"prompt": 0, "completion": 0, "image": 0}}
    assert requests == [expected]


@pytest.mark.parametrize("provider_type", [OllamaProvider, OpenAICompatibleProvider])
@pytest.mark.parametrize("failure", ["http", "stream"])
def test_image_provider_errors_hint_at_model_support_without_leaking_bytes(monkeypatch, provider_type, failure):
    if failure == "http":
        def open_url(request, timeout):
            raise HTTPError(request.full_url, 400, f"Image rejected: {PNG_DATA}", {}, io.BytesIO())

        monkeypatch.setattr(_http.urllib.request, "urlopen", open_url)
    else:
        adapter = ollama if provider_type is OllamaProvider else openai_compat

        async def stream(url, headers, payload, timeout):
            report = json.dumps({"error": {"message": f"Image rejected: {PNG_DATA}"}})
            yield report if provider_type is OllamaProvider else f"data: {report}"

        monkeypatch.setattr(adapter, "stream_lines", stream)

    messages = [ChatMessage(
        role="user",
        content="What is this?",
        images=[ChatImage(media_type="image/png", data=PNG_DATA)],
    )]
    with pytest.raises(ProviderError, match="model supports images") as error:
        asyncio.run(_collect(provider_type(), messages))
    assert PNG_DATA not in "".join(traceback.format_exception(error.value))
