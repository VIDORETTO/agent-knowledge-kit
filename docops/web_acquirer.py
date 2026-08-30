"""Bounded, provenance-preserving acquisition for public documentation sites."""

from __future__ import annotations

import fnmatch
import hashlib
import http.client
import ipaddress
import math
import re
import socket
import ssl
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from io import BytesIO
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from . import __version__
from .source_resolver import canonicalize_url

_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "bearer",
    "client_secret",
    "password",
    "passwd",
    "private_key",
    "secret",
    "signature",
    "sig",
    "token",
}


class AcquisitionError(RuntimeError):
    """A structured error for one source acquisition."""

    def __init__(self, code: str, message: str, *, url: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.url = url


class NetworkPolicyError(AcquisitionError):
    """Raised when a URL violates the default network safety policy."""


@dataclass(frozen=True)
class FetchPolicy:
    timeout_seconds: float = 20.0
    max_bytes: int = 5_000_000
    max_redirects: int = 5
    retries: int = 2
    allow_private: bool = False
    user_agent: str = f"docops/{__version__} (+documentation acquisition)"
    allowed_content_types: tuple[str, ...] = (
        "text/html",
        "application/xhtml+xml",
        "text/plain",
        "text/markdown",
        "application/xml",
        "text/xml",
        "application/json",
        "application/pdf",
    )

    def __post_init__(self) -> None:
        if not isinstance(self.timeout_seconds, (int, float)) or isinstance(self.timeout_seconds, bool) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if isinstance(self.max_bytes, bool) or not isinstance(self.max_bytes, int) or self.max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (self.max_redirects, self.retries)):
            raise ValueError("max_redirects and retries cannot be negative")


@dataclass(frozen=True)
class CrawlOptions:
    use_sitemap: bool = True
    max_pages: int = 50
    max_depth: int = 2
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    same_host: bool = True
    follow_links_without_sitemap: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.max_pages, bool) or not isinstance(self.max_pages, int) or self.max_pages < 1:
            raise ValueError("max_pages must be positive")
        if isinstance(self.max_depth, bool) or not isinstance(self.max_depth, int) or self.max_depth < 0:
            raise ValueError("max_depth cannot be negative")


@dataclass(frozen=True)
class FetchedResponse:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    redirects: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedDocument:
    content: str
    canonical: str
    title: str | None
    links: tuple[str, ...]
    content_type: str
    browser_required: bool = False


@dataclass
class WebAcquisitionResult:
    entries: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "accepted": sum(1 for entry in self.entries if entry.get("status") == "accepted"),
            "ignored": sum(1 for entry in self.entries if entry.get("status") == "ignored"),
            "errors": sum(1 for entry in self.entries if entry.get("status") in {"error", "failed"}),
        }


def _host_port(parsed: Any) -> tuple[str, int]:
    try:
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise NetworkPolicyError("invalid_url", "URL has an invalid port") from exc
    return host.casefold(), port


def _address_is_private(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _query_has_credentials(query: str) -> bool:
    for key, _value in parse_qsl(query, keep_blank_values=True):
        normalized = re.sub(r"[-\s]+", "_", key.casefold())
        if normalized in _SENSITIVE_QUERY_KEYS or normalized.endswith(("_token", "_secret")):
            return True
    return False


class NetworkPolicy:
    """Validate every hop before an HTTP request is sent."""

    _blocked_names = {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
        "instance-data",
        "instance-data.ec2.internal",
    }

    def __init__(self, *, allow_private: bool = False) -> None:
        self.allow_private = allow_private

    def _parse_and_check(self, url: str) -> tuple[Any, str, int]:
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise NetworkPolicyError("invalid_url", "URL is malformed", url=url) from exc
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise NetworkPolicyError("invalid_url", "only http and https URLs are supported", url=url)
        if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
            raise NetworkPolicyError("credentials_in_url", "credentials in URLs are not accepted", url=url)
        if _query_has_credentials(parsed.query):
            raise NetworkPolicyError("credentials_in_url", "credential-like query parameters are not accepted", url=url)
        host, port = _host_port(parsed)
        if not self.allow_private and (host in self._blocked_names or _address_is_private(host)):
            raise NetworkPolicyError("ssrf_blocked", f"network target is not allowed: {host}", url=url)
        return parsed, host, port

    def resolve_addresses(self, url: str) -> tuple[str, ...]:
        """Return the addresses permitted for one request.

        Callers that connect to a public URL must use the returned literal
        addresses. Re-resolving the hostname during the socket connection
        would reopen a DNS-rebinding/TOCTOU gap between this policy check and
        the actual request.
        """
        _parsed, host, port = self._parse_and_check(url)
        if self.allow_private:
            return (host,)
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
                if item[4]
            }
        except socket.gaierror as exc:
            raise AcquisitionError("dns_failed", f"could not resolve {host}: {exc}", url=url) from exc
        if not addresses:
            raise AcquisitionError("dns_failed", f"could not resolve {host}", url=url)
        if any(_address_is_private(address) for address in addresses):
            raise NetworkPolicyError("ssrf_blocked", f"network target resolves to a private address: {host}", url=url)
        return tuple(sorted(addresses))

    def validate(self, url: str) -> str:
        try:
            canonical = canonicalize_url(url)
        except ValueError as exc:
            raise NetworkPolicyError("invalid_url", "URL is malformed", url=url) from exc
        self.resolve_addresses(canonical)
        return canonical


class _DocumentHTMLParser(HTMLParser):
    """Small dependency-free HTML-to-Markdown normalizer."""

    _block_tags = {"p", "div", "section", "article", "header", "footer", "main", "aside", "blockquote", "tr"}

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts: list[str] = []
        self.links: list[str] = []
        self.title_parts: list[str] = []
        self._tag_stack: list[str] = []
        self._skip_depth = 0
        self._pre_depth = 0
        self._heading: int | None = None
        self._anchor: str | None = None
        self.script_count = 0
        self.visible_characters = 0
        self.canonical: str | None = None

    def _newline(self, count: int = 1) -> None:
        self.parts.append("\n" * count)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attributes = {key.casefold(): value or "" for key, value in attrs}
        self._tag_stack.append(tag)
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self._skip_depth += 1
            if tag == "script":
                self.script_count += 1
            return
        if self._skip_depth:
            return
        if tag == "link" and "canonical" in attributes.get("rel", "").casefold().split():
            href = attributes.get("href")
            if href:
                canonical = _safe_http_url(urljoin(self.base_url, href))
                if canonical:
                    self.canonical = canonical
        if tag == "title":
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading = int(tag[1])
            self._newline(2)
            self.parts.append("#" * self._heading + " ")
        elif tag in self._block_tags:
            self._newline(2)
        elif tag == "br":
            self._newline()
        elif tag == "li":
            self._newline()
            self.parts.append("- ")
        elif tag == "pre":
            self._pre_depth += 1
            self._newline(2)
            self.parts.append("```\n")
        elif tag == "a":
            href = attributes.get("href")
            if href:
                anchor = _safe_http_url(urljoin(self.base_url, href))
                if anchor:
                    self._anchor = anchor
                    self.links.append(anchor)
                    self.parts.append("[")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in {"script", "style", "noscript", "template", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if self._tag_stack:
            # HTML is often not perfectly nested; remove the nearest matching
            # tag rather than trusting malformed input to corrupt state.
            for index in range(len(self._tag_stack) - 1, -1, -1):
                if self._tag_stack[index] == tag:
                    del self._tag_stack[index]
                    break
        if self._skip_depth:
            return
        if tag == "title":
            return
        if tag == "a" and self._anchor:
            self.parts.append(f"]({self._anchor})")
            self._anchor = None
        elif tag == "pre" and self._pre_depth:
            self._pre_depth -= 1
            self._newline()
            self.parts.append("```\n")
        elif tag in self._block_tags or tag in {"h1", "h2", "h3", "h4", "h5", "h6", "li"}:
            self._newline()
            if tag.startswith("h"):
                self._heading = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if "title" in self._tag_stack:
            self.title_parts.append(data.strip())
            return
        if self._pre_depth:
            self.parts.append(data)
            self.visible_characters += len(data.strip())
            return
        value = re.sub(r"\s+", " ", data)
        if value.strip():
            self.parts.append(value)
            self.visible_characters += len(value.strip())


def normalize_html(body: bytes, url: str, *, content_type: str = "text/html") -> NormalizedDocument:
    parser = _DocumentHTMLParser(url)
    parser.feed(body.decode("utf-8", errors="replace"))
    content = re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()
    browser_required = parser.script_count > 0 and parser.visible_characters < 80
    return NormalizedDocument(
        content=content,
        canonical=parser.canonical or canonicalize_url(url),
        title=" ".join(part for part in parser.title_parts if part) or None,
        links=tuple(dict.fromkeys(parser.links)),
        content_type=content_type,
        browser_required=browser_required,
    )


def _extract_pdf_bytes(body: bytes) -> str:
    """Extract text from a fetched PDF without treating its bytes as UTF-8."""

    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AcquisitionError("dependency_missing", "pypdf is required to normalize fetched PDFs") from exc
    try:
        reader = PdfReader(BytesIO(body))
        content = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise AcquisitionError("ocr_required", "fetched PDF has no safely extractable text") from exc
    if not content:
        raise AcquisitionError("ocr_required", "fetched PDF has no safely extractable text")
    return content


def _safe_http_url(value: str) -> str | None:
    """Return a canonical HTTP(S) URL or ignore malformed/untrusted links."""

    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"}:
            return None
        return canonicalize_url(value)
    except ValueError:
        return None


def _is_asset(url: str) -> bool:
    path = urlsplit(url).path.casefold()
    return path.endswith(
        (
            ".css",
            ".js",
            ".mjs",
            ".ts",
            ".map",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".woff",
            ".woff2",
            ".ttf",
            ".zip",
        )
    )


def _matches(url: str, pattern: str) -> bool:
    path = urlsplit(url).path
    target = f"{path}?{urlsplit(url).query}" if urlsplit(url).query else path
    if pattern.startswith("re:"):
        return bool(re.search(pattern[3:], url))
    return fnmatch.fnmatch(url, pattern) or fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(target, pattern)


def destination_for_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/")
    if not path:
        segments = ["index"]
    else:
        segments = []
        for raw_segment in path.split("/"):
            if not raw_segment:
                continue
            segment = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_segment).strip("-")
            segments.append(segment if segment not in {"", ".", ".."} else "index")
    name = "/".join(segment or "index" for segment in segments)
    if name.casefold().endswith((".html", ".htm")):
        name = name.rsplit(".", 1)[0]
    if "." not in name.rsplit("/", 1)[-1]:
        name += ".md"
    if parsed.query:
        digest = hashlib.sha256(parsed.query.encode("utf-8")).hexdigest()[:10]
        parent, _, filename = name.rpartition("/")
        stem, dot, extension = filename.rpartition(".")
        filename = f"{stem or filename}--{digest}{dot}{extension}" if dot else f"{filename}--{digest}"
        name = f"{parent}/{filename}" if parent else filename
    return name


class WebAcquirer:
    """Fetch one page or a bounded site using sitemap-first discovery."""

    def __init__(self, *, policy: FetchPolicy | None = None, network_policy: NetworkPolicy | None = None) -> None:
        self.policy = policy or FetchPolicy()
        self.network_policy = network_policy or NetworkPolicy(allow_private=self.policy.allow_private)

    def _open_pinned(self, url: str) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
        """Open a direct HTTP(S) connection to a policy-approved IP.

        ``urllib`` delegates hostname resolution to ``http.client`` after the
        SSRF check. That gap is exploitable by DNS rebinding. This small direct
        client keeps the original Host/SNI name for virtual hosting while
        dialing one of the literal addresses approved immediately beforehand.
        """
        parsed = urlsplit(url)
        host, port = _host_port(parsed)
        addresses = self.network_policy.resolve_addresses(url)
        target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        headers = {
            "Accept": "text/html,application/xhtml+xml,text/plain,application/xml,application/json,application/pdf",
            "Connection": "close",
            "Host": parsed.netloc,
            "User-Agent": self.policy.user_agent,
        }
        last_error: OSError | None = None
        for address in addresses:
            raw_socket: socket.socket | None = None
            connection: http.client.HTTPConnection | None = None
            try:
                raw_socket = socket.create_connection((address, port), timeout=self.policy.timeout_seconds)
                if parsed.scheme == "https":
                    context = ssl.create_default_context()
                    wrapped_socket = context.wrap_socket(raw_socket, server_hostname=host)
                    raw_socket = None
                    connection = http.client.HTTPSConnection(host, port, timeout=self.policy.timeout_seconds, context=context)
                    connection.sock = wrapped_socket
                else:
                    connection = http.client.HTTPConnection(host, port, timeout=self.policy.timeout_seconds)
                    connection.sock = raw_socket
                    raw_socket = None
                connection.request("GET", target, headers=headers)
                return connection, connection.getresponse()
            except OSError as exc:
                last_error = exc
                if connection is not None:
                    connection.close()
                if raw_socket is not None:
                    raw_socket.close()
        raise OSError(f"could not connect to {host}:{port}: {last_error}")

    def fetch(self, url: str) -> FetchedResponse:
        try:
            requested = canonicalize_url(url)
        except ValueError as exc:
            raise NetworkPolicyError("invalid_url", "URL is malformed", url=url) from exc
        current = requested
        redirects: list[str] = []
        for redirect_number in range(self.policy.max_redirects + 1):
            current = self.network_policy.validate(current)
            last_error: AcquisitionError | None = None
            redirected = False
            for attempt in range(self.policy.retries + 1):
                response: http.client.HTTPResponse | None = None
                connection: http.client.HTTPConnection | None = None
                try:
                    connection, response = self._open_pinned(current)
                    status = getattr(response, "status", 200)
                    if 300 <= status < 400:
                        location = response.headers.get("Location")
                        if location:
                            redirects.append(current)
                            current = urljoin(current, location)
                            redirected = True
                            break
                    if status in {408, 429, 500, 502, 503, 504} and attempt < self.policy.retries:
                        last_error = AcquisitionError("temporary_http_error", f"HTTP {status}", url=current)
                        continue
                    if status < 200 or status >= 400:
                        code = "authentication_required" if status in {401, 403} else "http_error"
                        raise AcquisitionError(code, f"HTTP {status} for {current}", url=current)
                    content_type = response.headers.get_content_type().casefold()
                    if content_type not in self.policy.allowed_content_types:
                        raise AcquisitionError("unsupported_content_type", f"content type is not supported: {content_type}", url=current)
                    content_length = response.headers.get("Content-Length")
                    if content_length and content_length.isdigit() and int(content_length) > self.policy.max_bytes:
                        raise AcquisitionError("payload_too_large", f"response exceeds {self.policy.max_bytes} bytes", url=current)
                    body = bytearray()
                    while True:
                        block = response.read(min(64 * 1024, self.policy.max_bytes - len(body) + 1))
                        if not block:
                            break
                        body.extend(block)
                        if len(body) > self.policy.max_bytes:
                            raise AcquisitionError("payload_too_large", f"response exceeds {self.policy.max_bytes} bytes", url=current)
                    return FetchedResponse(requested, current, status, content_type, bytes(body), tuple(redirects))
                except AcquisitionError:
                    raise
                except (OSError, http.client.HTTPException, TimeoutError, socket.timeout) as exc:
                    if attempt < self.policy.retries:
                        last_error = AcquisitionError("network_error", str(exc), url=current)
                        continue
                    raise AcquisitionError("network_error", f"could not fetch {current}: {exc}", url=current) from exc
                else:
                    if redirected:
                        break
                finally:
                    if response is not None:
                        response.close()
                    if connection is not None:
                        connection.close()
            if redirected:
                if len(redirects) > self.policy.max_redirects:
                    raise AcquisitionError("redirect_limit", "redirect limit exceeded", url=current)
                continue
            else:
                if last_error:
                    raise last_error
                raise AcquisitionError("network_error", f"could not fetch {current}", url=current)
        raise AcquisitionError("redirect_limit", "redirect limit exceeded", url=current)

    def acquire(self, start_url: str, *, options: CrawlOptions | None = None) -> WebAcquisitionResult:
        options = options or CrawlOptions()
        result = WebAcquisitionResult()
        try:
            start = canonicalize_url(start_url)
        except ValueError as exc:
            result.entries.append({
                "source": start_url,
                "canonical": str(start_url),
                "status": "error",
                "code": "invalid_url",
                "reason": str(exc),
            })
            return result
        robots, sitemap_origins = self._read_robots(start)
        candidates: list[str] = []
        sitemap_used = False
        if options.use_sitemap:
            candidates = self._discover_sitemap(start, sitemap_origins=sitemap_origins)
            sitemap_used = bool(candidates)
        if not candidates:
            candidates = [start]
            if options.use_sitemap:
                result.warnings.append("sitemap unavailable; using bounded internal-link crawl")

        seen: set[str] = set()
        canonical_seen: set[str] = set()
        queue: list[tuple[str, int]] = [(url, 0) for url in candidates]
        fetched_pages = 0
        while queue and fetched_pages < max(1, options.max_pages):
            candidate, depth = queue.pop(0)
            try:
                canonical_candidate = canonicalize_url(candidate)
            except ValueError as exc:
                result.entries.append({
                    "source": candidate,
                    "canonical": str(candidate),
                    "status": "error",
                    "code": "invalid_url",
                    "reason": str(exc),
                })
                continue
            if canonical_candidate in seen:
                continue
            seen.add(canonical_candidate)
            reason = self._skip_reason(
                canonical_candidate,
                start,
                options,
                robots=robots,
                user_agent=self.policy.user_agent,
            )
            if reason:
                result.entries.append({"source": candidate, "canonical": canonical_candidate, "status": "ignored", "reason": reason})
                continue
            fetched_pages += 1
            try:
                response = self.fetch(candidate)
                if response.content_type in {"text/html", "application/xhtml+xml"}:
                    document = normalize_html(response.body, response.final_url, content_type=response.content_type)
                elif response.content_type == "application/pdf":
                    try:
                        content = _extract_pdf_bytes(response.body)
                    except AcquisitionError as exc:
                        result.entries.append({
                            "source": candidate,
                            "canonical": canonical_candidate,
                            "status": "error",
                            "code": exc.code,
                            "reason": str(exc),
                        })
                        continue
                    document = NormalizedDocument(
                        content=content,
                        canonical=canonicalize_url(response.final_url),
                        title=None,
                        links=(),
                        content_type=response.content_type,
                    )
                else:
                    document = NormalizedDocument(
                        content=response.body.decode("utf-8", errors="replace"),
                        canonical=canonicalize_url(response.final_url),
                        title=None,
                        links=(),
                        content_type=response.content_type,
                    )
                if document.browser_required:
                    result.entries.append({
                        "source": candidate,
                        "canonical": document.canonical,
                        "status": "error",
                        "code": "browser_rendering_required",
                        "reason": "page contains little visible text and likely requires a browser renderer",
                    })
                    result.warnings.append(f"browser rendering required: {candidate}")
                    continue
                if not document.content:
                    result.entries.append({"source": candidate, "canonical": document.canonical, "status": "error", "code": "empty_document", "reason": "no text extracted"})
                    continue
                if document.canonical in canonical_seen:
                    result.entries.append({
                        "source": candidate,
                        "canonical": document.canonical,
                        "status": "ignored",
                        "reason": "duplicate-canonical",
                    })
                    continue
                canonical_seen.add(document.canonical)
                result.entries.append({
                    "source": candidate,
                    "canonical": document.canonical,
                    "status": "accepted",
                    "content_type": document.content_type,
                    "title": document.title,
                    "content": document.content,
                    "content_hash": hashlib.sha256(document.content.encode("utf-8")).hexdigest(),
                    "destination": destination_for_url(document.canonical),
                    "redirects": list(response.redirects),
                    "provenance": {"requested_url": response.requested_url, "final_url": response.final_url},
                })
                if not sitemap_used and options.follow_links_without_sitemap and depth < options.max_depth:
                    queue.extend((link, depth + 1) for link in document.links if link not in seen)
            except AcquisitionError as exc:
                result.entries.append({
                    "source": candidate,
                    "canonical": canonical_candidate,
                    "status": "error",
                    "code": exc.code,
                    "reason": str(exc),
                })
        if queue:
            result.warnings.append(f"crawl limit reached: max_pages={options.max_pages}")
        return result

    def _read_robots(self, start: str) -> tuple[RobotFileParser | None, list[str]]:
        parsed = urlsplit(start)
        robots_url = urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
        try:
            robots = self.fetch(robots_url)
        except AcquisitionError:
            return None, []
        parser = RobotFileParser()
        parser.set_url(robots_url)
        lines = robots.body.decode("utf-8", errors="replace").splitlines()
        parser.parse(lines)
        origins = [line.split(":", 1)[1].strip() for line in lines if line.casefold().startswith("sitemap:") and line.split(":", 1)[1].strip()]
        return parser, origins

    def _discover_sitemap(self, start: str, *, sitemap_origins: list[str] | None = None) -> list[str]:
        parsed = urlsplit(start)
        common = [urlunsplit((parsed.scheme, parsed.netloc, "/sitemap.xml", "", ""))]
        if parsed.path.rstrip("/") not in {"", "/sitemap.xml"}:
            common.append(urljoin(start, "sitemap.xml"))
        origins = list(sitemap_origins or [])
        origins.extend(common)
        urls: list[str] = []
        visited: set[str] = set()
        pending = origins
        while pending and len(urls) < 1000 and len(visited) < 1000:
            try:
                location = canonicalize_url(pending.pop(0))
            except ValueError:
                continue
            if location in visited:
                continue
            visited.add(location)
            try:
                response = self.fetch(location)
            except AcquisitionError:
                continue
            if response.content_type not in {"application/xml", "text/xml"} and not location.endswith(".xml"):
                continue
            page_urls, nested = _parse_sitemap(response.body)
            remaining = 1000 - len(urls)
            urls.extend(page_urls[:remaining])
            pending.extend(nested[: max(0, 1000 - len(visited) - len(pending))])
        return list(dict.fromkeys(urls))

    @staticmethod
    def _skip_reason(
        url: str,
        start: str,
        options: CrawlOptions,
        *,
        robots: RobotFileParser | None = None,
        user_agent: str = "*",
    ) -> str | None:
        if urlsplit(url).scheme not in {"http", "https"}:
            return "non-http-url"
        if _is_asset(url):
            return "asset"
        if robots is not None and not robots.can_fetch(user_agent, url):
            return "robots-disallow"
        source = urlsplit(start)
        target = urlsplit(url)
        if options.same_host and (target.hostname or "").casefold() != (source.hostname or "").casefold():
            return "external-host"
        if options.include_patterns and not any(_matches(url, pattern) for pattern in options.include_patterns):
            return "outside-include"
        if any(_matches(url, pattern) for pattern in options.exclude_patterns):
            return "excluded"
        return None


def _parse_sitemap(body: bytes) -> tuple[list[str], list[str]]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return [], []
    urls: list[str] = []
    nested: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].casefold()
        if tag != "loc" or not element.text:
            continue
        value = _safe_http_url(element.text.strip())
        if not value:
            continue
        # ElementTree in the stdlib has no parent pointers. The document kind
        # is inferred from the root, which is sufficient for sitemap indexes.
        if root.tag.rsplit("}", 1)[-1].casefold() == "sitemapindex":
            nested.append(value)
        else:
            urls.append(value)
    return urls, nested
