import io
import json
import socket
import ssl
import time
from email.message import Message
from urllib.parse import parse_qs, urlsplit

import pytest

from cogplat.services import web_tools


@pytest.mark.parametrize("url", [
    "http://example.com/",
    "https://example.com:444/",
    "https://user:password@example.com/",
    "https://localhost/",
    "https://127.0.0.1/",
    "https://169.254.169.254/",
    "https://100.64.0.1/",
    "https://224.1.1.1/",
    "https://[::ffff:127.0.0.1]/",
    "https://[2002:7f00:1::]/",
    "https://[64:ff9b::7f00:1]/",
])
def test_web_page_rejects_unsupported_destinations_without_network(monkeypatch, url):
    monkeypatch.setattr(web_tools, "_request", lambda *_: pytest.fail("unexpected web request"))
    with pytest.raises(web_tools.ToolInputError):
        web_tools.read_web_page(url)


def test_private_dns_answer_blocks_request_before_connecting(monkeypatch):
    monkeypatch.setattr(web_tools.socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.1", 443)),
    ])
    monkeypatch.setattr(web_tools.socket, "socket", lambda *_: pytest.fail("unexpected socket"))
    with pytest.raises(web_tools.ToolInputError, match="non-public"):
        web_tools.read_web_page("https://example.com/")


def test_connection_pins_numeric_address_and_verifies_tls_hostname(monkeypatch):
    resolved = []
    connected = []
    tls = []
    public_endpoint = ("93.184.216.34", 443)

    def resolve(hostname, port, *, type):
        resolved.append((hostname, port, type))
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", public_endpoint)]

    class Transport:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, seconds):
            assert seconds > 0

        def connect(self, endpoint):
            connected.append(endpoint)

    class TLSContext:
        def wrap_socket(self, transport, *, server_hostname):
            tls.append((transport, server_hostname))
            return object()

    transport = Transport()
    monkeypatch.setattr(web_tools.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(web_tools.socket, "socket", lambda *_: transport)
    connection = web_tools._PinnedHTTPSConnection("example.com", time.monotonic() + 5)
    assert connection._tls_context.verify_mode == ssl.CERT_REQUIRED
    assert connection._tls_context.check_hostname
    connection._tls_context = TLSContext()
    connection.connect()

    assert resolved == [("example.com", 443, socket.SOCK_STREAM)]
    assert connected == [public_endpoint]
    assert tls == [(transport, "example.com")]


def test_web_page_reports_an_untrusted_certificate(monkeypatch):
    class RejectingConnection:
        def __init__(self, *_):
            pass

        def request(self, *args, **kwargs):
            raise ssl.SSLCertVerificationError("untrusted test certificate")

        def close(self):
            pass

    monkeypatch.setattr(web_tools, "_PinnedHTTPSConnection", RejectingConnection)
    with pytest.raises(web_tools.ToolUnavailableError, match="HTTPS certificate"):
        web_tools.read_web_page("https://example.com/")


def test_web_page_checks_redirect_destination_before_second_request(monkeypatch):
    requested = []

    def request(destination, *_):
        requested.append(destination.url)
        return web_tools._Response(302, "https://127.0.0.1/private")

    monkeypatch.setattr(web_tools, "_request", request)
    with pytest.raises(web_tools.ToolInputError, match="non-public"):
        web_tools.read_web_page("https://example.com/")
    assert requested == ["https://example.com/"]


def test_web_page_follows_relative_redirect_and_extracts_bounded_text(monkeypatch):
    requested = []

    def request(destination, *_):
        requested.append(destination.url)
        if len(requested) == 1:
            return web_tools._Response(302, "/article?from=home#heading")
        markup = (
            "<html><head><title>Example &amp; test</title></head><body>"
            "<p>One <strong>two</strong>.</p><script>alert('bad')</script>"
            "<style>bad</style><template>bad</template><p>" + ("z" * 40) + "</p></body></html>"
        )
        return web_tools._Response(200, media_type="text/html", data=markup.encode())

    monkeypatch.setattr(web_tools, "_request", request)
    monkeypatch.setattr(web_tools, "MAX_TEXT_CHARS", 24)
    assert web_tools.read_web_page("https://example.com/") == {
        "url": "https://example.com/article?from=home",
        "title": "Example & test",
        "text": "One two.\n" + "z" * 15,
        "truncated": True,
    }
    assert requested == ["https://example.com/", "https://example.com/article?from=home"]


def test_web_transport_uses_get_only_and_stops_at_the_response_limit(monkeypatch):
    class Response:
        status = 200
        headers = Message()
        headers["Content-Type"] = "text/plain; charset=utf-8"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def getheader(self, name, default=None):
            return self.headers.get(name, default)

        read1 = io.BytesIO(b"x" * 50).read1

    class Connection:
        sock = None
        closed = False

        def request(self, method, target, *, headers):
            assert method == "GET"
            assert target == "/the-page"
            assert headers["Accept-Encoding"] == "identity"
            assert set(headers) == {"Accept", "Accept-Encoding", "User-Agent"}

        def getresponse(self):
            return Response()

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(web_tools, "_PinnedHTTPSConnection", lambda *args: connection)
    monkeypatch.setattr(web_tools, "MAX_BODY_BYTES", 32)
    assert web_tools.read_web_page("https://example.com/the-page") == {
        "url": "https://example.com/the-page",
        "title": "example.com",
        "text": "x" * 32,
        "truncated": True,
    }
    assert connection.closed


def test_web_page_reports_no_readable_text(monkeypatch):
    monkeypatch.setattr(web_tools, "_request", lambda *_: web_tools._Response(
        200, media_type="text/html", data=b"<script>text</script>",
    ))
    with pytest.raises(web_tools.ToolUnavailableError, match="readable text"):
        web_tools.read_web_page("https://example.com/the-page")


def test_search_encodes_query_and_returns_sanitized_distinct_results(monkeypatch):
    def request(destination, accepted_types, deadline):
        assert destination.loopback
        assert destination.hostname == "localhost"
        assert urlsplit(destination.url).path == "/search"
        assert parse_qs(urlsplit(destination.url).query) == {"q": ["a & b"], "format": ["json"]}
        assert accepted_types == {"application/json"}
        hits = [
            {"url": "https://127.0.0.1/", "title": "local"},
            {"url": "javascript:alert(1)", "title": "script"},
            {"url": "https://example.com/page#a", "title": "A <b>&amp; B</b>", "content": "<p>Te\ud800xt.</p>"},
            {"url": "https://example.com/page#b", "title": "duplicate"},
            *({"url": f"https://example.com/{index}", "title": str(index)} for index in range(10)),
        ]
        return web_tools._Response(200, data=json.dumps({"results": hits}).encode())

    monkeypatch.setattr(web_tools, "_request", request)
    result = web_tools.search_web("http://localhost:8888", " a & b ")
    assert result["query"] == "a & b"
    assert len(result["results"]) == 8
    assert result["results"][0] == {
        "url": "https://example.com/page",
        "title": "A & B",
        "snippet": "Text.",
    }
    assert result["results"][-1]["url"] == "https://example.com/6"


@pytest.mark.parametrize("server", [
    "http://127.0.0.1",
    "http://127.0.0.1:8889",
    "http://127.0.0.1:8888/unexpected",
    "http://127.0.0.2:8888",
    "https://example.com/?search=unexpected",
])
def test_search_rejects_other_local_endpoints_or_query_in_base(monkeypatch, server):
    monkeypatch.setattr(web_tools, "_request", lambda *_: pytest.fail("unexpected web request"))
    with pytest.raises(web_tools.ToolInputError):
        web_tools.search_web(server, "query")


def test_search_does_not_send_query_across_redirect(monkeypatch):
    requested = []

    def request(destination, *_):
        requested.append(destination.hostname)
        return web_tools._Response(302, "https://elsewhere.example/search")

    monkeypatch.setattr(web_tools, "_request", request)
    with pytest.raises(web_tools.ToolUnavailableError, match="redirected"):
        web_tools.search_web("https://search.example", "query")
    assert requested == ["search.example"]


def test_search_rejects_long_query_before_network(monkeypatch):
    monkeypatch.setattr(web_tools, "_request", lambda *_: pytest.fail("unexpected web request"))
    with pytest.raises(web_tools.ToolInputError, match="300 characters"):
        web_tools.search_web("https://search.example", "q" * 301)
