from __future__ import annotations

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from docops.web_acquirer import CrawlOptions, FetchPolicy, NetworkPolicyError, WebAcquirer, destination_for_url


@contextmanager
def fixture_server() -> str:
    pages = {
        "/": b'<html><head><link rel="canonical" href="/canonical"></head><body><h1>Home</h1><p>Useful documentation.</p><a href="/guide">Guide</a><a href="/canonical">Canonical</a></body></html>',
        "/canonical": b"<html><body><h1>Canonical</h1><p>Same content.</p></body></html>",
        "/guide": b"<html><body><h1>Guide</h1><p>More documentation.</p><a href='/guide'>loop</a><a href='https://outside.test/x'>external</a><a href='/asset.js'>asset</a></body></html>",
        "/allowed": b"<html><body><h1>Allowed</h1><p>Included page.</p></body></html>",
        "/blocked": b"<html><body><h1>Blocked</h1><p>Should not be crawled.</p></body></html>",
        "/asset.js": b"console.log('not docs')",
        "/large": b"x" * 128,
        "/sitemap.xml": b"""<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>{base}/allowed</loc></url><url><loc>{base}/allowed#fragment</loc></url><url><loc>{base}/blocked</loc></url><url><loc>{base}/asset.js</loc></url><url><loc>https://outside.test/no</loc></url></urlset>""",
        "/robots.txt": b"User-agent: *\nDisallow: /blocked\nSitemap: {base}/custom-sitemap.xml\n",
        "/custom-sitemap.xml": b"""<?xml version='1.0'?><urlset><url><loc>{base}/allowed</loc></url></urlset>""",
    }
    current: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            body = pages.get(path)
            if path == "/sitemap.xml":
                body = pages[path].replace(b"{base}", current["base"].encode())
            if path in {"/robots.txt", "/custom-sitemap.xml"}:
                body = pages[path].replace(b"{base}", current["base"].encode())
            if body is None:
                if path == "/private":
                    self.send_response(401)
                    self.end_headers()
                    return
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            content_type = "text/plain" if path == "/robots.txt" else "application/xml" if path.endswith(".xml") else "text/html"
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    current["base"] = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield current["base"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_default_policy_blocks_loopback_and_fixture_policy_must_opt_in() -> None:
    with pytest.raises(NetworkPolicyError) as caught:
        WebAcquirer().fetch("http://127.0.0.1:1/")

    assert caught.value.code == "ssrf_blocked"
    assert FetchPolicy(allow_private=True).allow_private is True


def test_network_policy_rejects_credentials_and_cloud_metadata() -> None:
    policy = WebAcquirer().network_policy

    with pytest.raises(NetworkPolicyError) as credentials:
        policy.validate("https://user:secret@example.test/docs")
    with pytest.raises(NetworkPolicyError) as metadata:
        policy.validate("http://169.254.169.254/latest/meta-data")
    with pytest.raises(NetworkPolicyError) as query_credentials:
        policy.validate("https://docs.example.test/guide?api_key=secret-value")

    assert credentials.value.code == "credentials_in_url"
    assert metadata.value.code == "ssrf_blocked"
    assert query_credentials.value.code == "credentials_in_url"


def test_network_policy_reports_malformed_ports_as_structured_errors() -> None:
    policy = WebAcquirer().network_policy

    with pytest.raises(NetworkPolicyError) as caught:
        policy.validate("https://docs.example.test:bad/docs")

    assert caught.value.code == "invalid_url"


def test_fetches_one_html_page_and_preserves_canonical_origin() -> None:
    with fixture_server() as base:
        result = WebAcquirer(policy=FetchPolicy(allow_private=True)).acquire(
            f"{base}/",
            options=CrawlOptions(use_sitemap=False, max_pages=1),
        )

    assert result.entries[0]["status"] == "accepted"
    assert result.entries[0]["canonical"] == f"{base}/canonical"
    assert result.entries[0]["source"] == f"{base}/"
    assert "Useful documentation." in result.entries[0]["content"]


def test_payload_and_authentication_fail_closed_with_structured_entries() -> None:
    with fixture_server() as base:
        large = WebAcquirer(policy=FetchPolicy(allow_private=True, max_bytes=32)).acquire(
            f"{base}/large", options=CrawlOptions(use_sitemap=False, max_pages=1)
        )
        private = WebAcquirer(policy=FetchPolicy(allow_private=True)).acquire(
            f"{base}/private", options=CrawlOptions(use_sitemap=False, max_pages=1)
        )

    assert large.entries[0]["code"] == "payload_too_large"
    assert private.entries[0]["code"] == "authentication_required"


def test_sitemap_crawl_applies_limits_filters_and_deduplication() -> None:
    with fixture_server() as base:
        result = WebAcquirer(policy=FetchPolicy(allow_private=True)).acquire(
            f"{base}/",
            options=CrawlOptions(
                use_sitemap=True,
                max_pages=2,
                include_patterns=("*/allowed",),
                exclude_patterns=("*/blocked",),
            ),
        )

    accepted = [entry for entry in result.entries if entry["status"] == "accepted"]
    assert len(accepted) == 1
    assert accepted[0]["canonical"] == f"{base}/allowed"
    assert result.counts["ignored"] >= 2
    assert all(
        entry["status"] != "accepted" or "outside.test" not in str(entry)
        for entry in result.entries
    )
    assert any(entry.get("reason") == "external-host" for entry in result.entries)


def test_crawl_respects_robots_disallow_rules() -> None:
    with fixture_server() as base:
        result = WebAcquirer(policy=FetchPolicy(allow_private=True)).acquire(
            f"{base}/",
            options=CrawlOptions(use_sitemap=True, max_pages=5),
        )

    blocked = [entry for entry in result.entries if entry.get("canonical") == f"{base}/blocked"]
    assert blocked
    assert blocked[0]["status"] == "ignored"
    assert blocked[0]["reason"] == "robots-disallow"


def test_url_destinations_are_safe_and_distinguish_query_variants() -> None:
    traversal = destination_for_url("https://docs.example.test/../secret")
    first_query = destination_for_url("https://docs.example.test/guide?lang=en")
    second_query = destination_for_url("https://docs.example.test/guide?lang=pt")

    assert ".." not in traversal.split("/")
    assert first_query != second_query


def test_link_crawl_deduplicates_pages_by_declared_canonical_url() -> None:
    with fixture_server() as base:
        result = WebAcquirer(policy=FetchPolicy(allow_private=True)).acquire(
            f"{base}/", options=CrawlOptions(use_sitemap=False, max_pages=3)
        )

    accepted = [entry for entry in result.entries if entry["status"] == "accepted"]
    assert len({entry["canonical"] for entry in accepted}) == len(accepted)
    assert any(entry.get("reason") == "duplicate-canonical" for entry in result.entries)


def test_html_normalization_does_not_emit_non_http_links() -> None:
    from docops.web_acquirer import normalize_html

    document = normalize_html(
        b"<html><body><a href='javascript:alert(1)'>bad</a><a href='mailto:x@example.test'>mail</a><a href='/guide'>good</a></body></html>",
        "https://docs.example.test/",
    )

    assert document.links == ("https://docs.example.test/guide",)
    assert "javascript:" not in document.content
    assert "mailto:" not in document.content


def test_malformed_sitemap_locations_are_ignored() -> None:
    from docops.web_acquirer import _parse_sitemap

    urls, nested = _parse_sitemap(
        b"<urlset><url><loc>https://docs.example.test:bad/guide</loc></url>"
        b"<url><loc>https://docs.example.test/good</loc></url></urlset>"
    )

    assert urls == ["https://docs.example.test/good"]
    assert nested == []


def test_fetched_pdf_is_not_accepted_as_raw_binary_text(monkeypatch) -> None:
    from docops.web_acquirer import FetchedResponse

    acquirer = WebAcquirer(policy=FetchPolicy(allow_private=True))
    monkeypatch.setattr(
        acquirer,
        "fetch",
        lambda _url: FetchedResponse(
            requested_url="https://docs.example.test/guide.pdf",
            final_url="https://docs.example.test/guide.pdf",
            status=200,
            content_type="application/pdf",
            body=b"not a pdf",
        ),
    )

    result = acquirer.acquire(
        "https://docs.example.test/guide.pdf",
        options=CrawlOptions(use_sitemap=False, max_pages=1),
    )

    assert result.entries[0]["status"] == "error"
    assert result.entries[0]["code"] in {"dependency_missing", "ocr_required"}
