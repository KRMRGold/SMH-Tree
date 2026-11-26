"""Read-only public web access for explicit desktop tool requests."""

from __future__ import annotations

import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit


MAX_BODY_BYTES = 512 * 1024
MAX_TEXT_CHARS = 12_000
MAX_REDIRECTS = 3
REQUEST_TIMEOUT = 12.0
PAGE_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
SEARCH_TYPES = frozenset({"application/json"})
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
IPV6_PUBLIC_UNICAST = ipaddress.ip_network("2000::/3")
IPV6_TRANSITION = (ipaddress.ip_network("2001::/32"), ipaddress.ip_network("2002::/16"))
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]")


class ToolInputError(ValueError):
    """The request contains an unsupported or disallowed input."""


class ToolUnavailableError(RuntimeError):
    """The requested tool could not read its source."""


@dataclass(frozen=True, slots=True)
class _Destination:
    url: str
    hostname: str
    target: str
    loopback: bool


@dataclass(frozen=True, slots=True)
class _Response:
    status: int
    location: str | None = None
    media_type: str = ""
    charset: str = "utf-8"
    data: bytes = b""
    truncated: bool = False


def _is_public_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if not address.is_global or address.is_multicast or address.is_reserved:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        return address in IPV6_PUBLIC_UNICAST and not any(
            address in network for network in IPV6_TRANSITION
        )
    return True


def _destination(url: str, *, allow_loopback: bool = False) -> _Destination:
    if not url or len(url) > 8192 or "\\" in url or any(
        ord(character) <= 32 or ord(character) == 127 or 0xD800 <= ord(character) <= 0xDFFF
        for character in url
    ):
        raise ToolInputError("Enter a valid URL.")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ToolInputError("Enter a valid URL.") from exc
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ToolInputError("A URL must have a hostname and no embedded credentials.")

    loopback = (
        allow_loopback and parsed.scheme == "http"
        and hostname in {"127.0.0.1", "localhost"} and port == 8888
    )
    if not loopback and (parsed.scheme != "https" or port not in {None, 443}):
        raise ToolInputError("Use a public HTTPS URL on port 443.")

    if not loopback:
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            try:
                hostname = hostname.rstrip(".").encode("idna").decode("ascii")
            except UnicodeError as exc:
                raise ToolInputError("Enter a valid hostname.") from exc
            labels = hostname.split(".")
            if len(labels) < 2 or not all(HOST_LABEL.fullmatch(label) for label in labels):
                raise ToolInputError("Use a public hostname or IP address.")
        else:
            if not _is_public_ip(address):
                raise ToolInputError("Private and other non-public network addresses are blocked.")
            hostname = str(address)

    authority = f"[{hostname}]" if ":" in hostname else hostname
    if loopback:
        authority += ":8888"
    path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    query = quote(parsed.query, safe="/?%:@!$&'()*+,;=-._~")
    clean_url = urlunsplit((parsed.scheme, authority, path, query, ""))
    target = path + (f"?{query}" if query else "")
    return _Destination(clean_url, hostname, target, loopback)


def _public_addresses(hostname: str) -> list[tuple[int, tuple]]:
    addresses = []
    for family, _, _, _, endpoint in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM):
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        address = ipaddress.ip_address(endpoint[0])
        if not _is_public_ip(address) or (family == socket.AF_INET6 and endpoint[3]):
            raise ToolInputError("Private and other non-public network addresses are blocked.")
        pair = (family, endpoint)
        if pair not in addresses:
            addresses.append(pair)
    if not addresses:
        raise ToolUnavailableError("The hostname did not resolve to a public address.")
    return addresses


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Web tool request timed out.")
    return remaining


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, deadline: float):
        self._deadline = deadline
        self._tls_context = ssl.create_default_context()
        super().__init__(hostname, 443, timeout=_remaining(deadline), context=self._tls_context)

    def connect(self) -> None:
        last_error = None
        # Use the checked numeric address while TLS authenticates the original hostname.
        for family, endpoint in _public_addresses(self.host):
            try:
                with socket.socket(family, socket.SOCK_STREAM) as transport:
                    transport.settimeout(_remaining(self._deadline))
                    transport.connect(endpoint)
                    transport.settimeout(_remaining(self._deadline))
                    self.sock = self._tls_context.wrap_socket(transport, server_hostname=self.host)
                return
            except ssl.SSLCertVerificationError:
                raise
            except OSError as exc:
                last_error = exc
        raise OSError("Could not connect to a public address.") from last_error


def _request(destination: _Destination, accepted_types: frozenset[str], deadline: float) -> _Response:
    headers = {
        "Accept": ", ".join(sorted(accepted_types)),
        "Accept-Encoding": "identity",
        "User-Agent": "SMH-Tree Web Tools",
    }
    try:
        if destination.loopback:
            connection = http.client.HTTPConnection("127.0.0.1", 8888, timeout=_remaining(deadline))
            headers["Host"] = f"{destination.hostname}:8888"
        else:
            connection = _PinnedHTTPSConnection(destination.hostname, deadline)
        try:
            connection.request("GET", destination.target, headers=headers)
            transport = connection.sock
            if transport is not None:
                transport.settimeout(_remaining(deadline))
            with connection.getresponse() as response:
                if response.status in REDIRECT_CODES:
                    return _Response(response.status, response.getheader("Location"))
                if not 200 <= response.status < 300:
                    raise ToolUnavailableError(f"The server returned HTTP {response.status}.")
                media_type = response.headers.get_content_type()
                if not response.getheader("Content-Type") or media_type not in accepted_types:
                    raise ToolUnavailableError("The server returned an unsupported content type.")
                encoding = response.getheader("Content-Encoding", "identity").strip().lower()
                if encoding not in {"", "identity"}:
                    raise ToolUnavailableError("The server returned an unsupported content encoding.")
                body = bytearray()
                while len(body) <= MAX_BODY_BYTES:
                    timeout = _remaining(deadline)
                    if transport is not None and transport.fileno() >= 0:
                        transport.settimeout(timeout)
                    chunk = response.read1(min(64 * 1024, MAX_BODY_BYTES + 1 - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                return _Response(
                    response.status,
                    media_type=media_type,
                    charset=response.headers.get_content_charset() or "utf-8",
                    data=bytes(body[:MAX_BODY_BYTES]),
                    truncated=len(body) > MAX_BODY_BYTES,
                )
        finally:
            connection.close()
    except TimeoutError as exc:
        raise ToolUnavailableError("The web request timed out.") from exc
    except ssl.SSLCertVerificationError as exc:
        raise ToolUnavailableError("Could not verify the website's HTTPS certificate.") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise ToolUnavailableError("Could not connect to or read from the server.") from exc


class _PageText(HTMLParser):
    _SKIP = frozenset({"script", "style", "noscript", "template", "svg", "canvas"})
    _BLOCKS = frozenset({
        "address", "article", "aside", "blockquote", "br", "div", "footer", "h1", "h2", "h3",
        "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "p", "pre", "section", "td", "tr",
    })

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.text: list[str] = []
        self._skipped: list[str] = []
        self._in_head = False
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skipped.append(tag)
        elif not self._skipped:
            if tag == "head":
                self._in_head = True
            elif tag == "title":
                self._in_title = True
            elif tag in self._BLOCKS:
                self.text.append("\n")

    def handle_endtag(self, tag):
        if self._skipped:
            if tag == self._skipped[-1]:
                self._skipped.pop()
        elif tag == "head":
            self._in_head = False
            self._in_title = False
        elif tag == "title":
            self._in_title = False
        elif tag in self._BLOCKS:
            self.text.append("\n")

    def handle_data(self, data):
        if self._skipped:
            return
        if self._in_title:
            self.title.append(data)
        elif not self._in_head:
            self.text.append(data)


def _clean_text(text: str) -> str:
    return "\n".join(
        line for line in (" ".join(line.split()) for line in CONTROL_CHARS.sub("", text).splitlines())
        if line
    )


def _decode(response: _Response) -> str:
    try:
        return response.data.decode(response.charset, errors="replace")
    except (LookupError, UnicodeError):
        return response.data.decode("utf-8", errors="replace")


def read_web_page(url: str) -> dict:
    """Fetch and extract plain text from a public HTTPS page."""
    deadline = time.monotonic() + REQUEST_TIMEOUT
    destination = _destination(url)
    for hop in range(MAX_REDIRECTS + 1):
        response = _request(destination, PAGE_TYPES, deadline)
        if response.status not in REDIRECT_CODES:
            break
        if hop == MAX_REDIRECTS or not response.location:
            raise ToolUnavailableError("The page returned an invalid or excessive redirect.")
        destination = _destination(urljoin(destination.url, response.location))

    raw_text = _decode(response)
    title = destination.hostname
    if response.media_type != "text/plain":
        parser = _PageText()
        try:
            parser.feed(raw_text)
            parser.close()
        except (AssertionError, ValueError) as exc:
            raise ToolUnavailableError("The server returned unreadable HTML.") from exc
        title = " ".join(_clean_text("".join(parser.title)).split())[:240] or title
        raw_text = "".join(parser.text)
    text = _clean_text(raw_text)
    if not text:
        raise ToolUnavailableError("The page did not contain readable text.")
    return {
        "url": destination.url,
        "title": title,
        "text": text[:MAX_TEXT_CHARS].rstrip(),
        "truncated": response.truncated or len(text) > MAX_TEXT_CHARS,
    }


def _search_text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    parser = _PageText()
    try:
        parser.feed(value[: limit * 4])
        parser.close()
    except (AssertionError, ValueError):
        return ""
    return " ".join(_clean_text("".join(parser.text)).split())[:limit]


def search_web(server_url: str, query: str) -> dict:
    """Run one explicitly submitted query on a configured SearXNG server."""
    query = query.strip()
    if not query or len(query) > 300:
        raise ToolInputError("Enter a search query between 1 and 300 characters.")
    server = _destination(server_url, allow_loopback=True)
    if "?" in server_url or "#" in server_url or (server.loopback and server.target != "/"):
        raise ToolInputError("Use the base address of a SearXNG server.")
    try:
        params = urlencode({"q": query, "format": "json"})
    except UnicodeEncodeError as exc:
        raise ToolInputError("Enter a search query with valid Unicode.") from exc
    destination = _destination(server.url.rstrip("/") + f"/search?{params}", allow_loopback=True)
    response = _request(destination, SEARCH_TYPES, time.monotonic() + REQUEST_TIMEOUT)
    if response.status in REDIRECT_CODES:
        raise ToolUnavailableError("The search server redirected. Use its final base address.")
    if response.truncated:
        raise ToolUnavailableError("The search response exceeded the size limit.")
    try:
        data = json.loads(response.data)
    except (ValueError, RecursionError) as exc:
        raise ToolUnavailableError("The search server did not return valid JSON.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ToolUnavailableError("The search server did not return a SearXNG result list.")

    results = []
    seen_urls = set()
    for item in data["results"]:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        try:
            result_url = _destination(item["url"]).url
        except ToolInputError:
            continue
        if result_url in seen_urls:
            continue
        seen_urls.add(result_url)
        results.append({
            "url": result_url,
            "title": _search_text(item.get("title"), 240) or result_url,
            "snippet": _search_text(item.get("content"), 500),
        })
        if len(results) == 8:
            break
    return {"query": query, "results": results}
