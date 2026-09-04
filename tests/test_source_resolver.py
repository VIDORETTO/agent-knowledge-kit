# seam-scope: implementation-infrastructure (resolver unit tests)
from __future__ import annotations

import json
from pathlib import Path

from docops.source_resolver import SourceCandidate, SourceResolver


def test_resolves_a_local_directory_without_network_access(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()

    result = SourceResolver().resolve(str(source))

    assert result.kind == "local"
    assert result.selected is not None
    assert result.selected.canonical == source.resolve().as_uri()
    assert result.selected.official is None


def test_classifies_github_tree_url_and_keeps_version_and_scope() -> None:
    result = SourceResolver().resolve(
        "https://github.com/acme/project/tree/v2.4/docs/reference",
    )

    assert result.kind == "repository"
    assert result.selected is not None
    assert result.selected.version == "v2.4"
    assert result.selected.scope == "docs/reference"
    assert result.selected.canonical == "https://github.com/acme/project"
    assert result.selected.official is None


def test_catalog_resolution_preserves_requested_language_and_version() -> None:
    resolver = SourceResolver(
        [
            {
                "names": ["manual"],
                "slug": "manual",
                "docs_url": "https://docs.example.test/manual",
                "official": True,
                "confidence": 1.0,
                "license": "MIT",
            }
        ]
    )

    result = resolver.resolve("manual", version="v2", language="pt-BR")

    assert result.selected is not None
    assert result.selected.version == "v2"
    assert result.selected.language == "pt-BR"
    assert result.selected.license == "MIT"


def test_resolves_catalog_name_with_official_evidence(tmp_path: Path) -> None:
    catalog = tmp_path / "sources.json"
    catalog.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "names": ["Acme API", "acme"],
                        "slug": "acme-api",
                        "docs_url": "https://docs.example.test/acme",
                        "official": True,
                        "confidence": 0.98,
                        "evidence": ["vendor catalog", "official docs"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = SourceResolver.from_catalog_file(catalog).resolve("Acme API")

    assert result.selected is not None
    assert result.selected.slug == "acme-api"
    assert result.selected.official is True
    assert result.requires_decision is False


def test_does_not_silently_choose_between_materially_ambiguous_candidates() -> None:
    resolver = SourceResolver(
        [
            {
                "names": ["thing"],
                "slug": "thing-a",
                "docs_url": "https://a.example.test",
                "official": True,
                "confidence": 0.91,
                "evidence": ["official"],
            },
            {
                "names": ["thing"],
                "slug": "thing-b",
                "docs_url": "https://b.example.test",
                "official": True,
                "confidence": 0.9,
                "evidence": ["official"],
            },
        ]
    )

    result = resolver.resolve("thing")

    assert result.selected is None
    assert result.requires_decision is True
    assert len(result.candidates) == 2


def test_malformed_url_returns_a_structured_resolution_error() -> None:
    result = SourceResolver().resolve("https://docs.example.test:bad/docs")

    assert result.selected is None
    assert result.error is not None
    assert result.error["code"] == "invalid_url"


def test_serialized_resolution_redacts_sensitive_url_values() -> None:
    result = SourceResolver().resolve("https://docs.example.test/guide?api_key=super-secret-value")

    serialized = json.dumps(result.to_dict())

    assert "super-secret-value" not in serialized
    assert "REDACTED" in serialized


def test_serialized_provider_evidence_does_not_leak_secrets_or_local_paths() -> None:
    secret = "x" * 24
    private_path = "C:" + r"\Users\gabri\private\evidence.txt"

    class Provider:
        name = "fixture-provider"

        def resolve(self, _value: str, **_kwargs: object):
            return [
                SourceCandidate(
                    kind="web",
                    slug="custom-framework",
                    canonical="https://docs.example.test/custom",
                    official=True,
                    confidence=0.99,
                    evidence=("token=" + secret, private_path),
                )
            ]

    result = SourceResolver(providers=[Provider()]).resolve("custom framework")
    serialized = json.dumps(result.to_dict())

    assert secret not in serialized
    assert private_path not in serialized


def test_serialized_resolution_redacts_token_like_input_without_url_scheme() -> None:
    secret = "s" * 24

    result = SourceResolver().resolve("token=" + secret)

    assert secret not in json.dumps(result.to_dict())


def test_harness_can_supply_a_name_provider_without_network_discovery() -> None:
    class Provider:
        name = "fixture-provider"

        def resolve(self, value: str, **_kwargs: object):
            if value == "custom framework":
                return [
                    SourceCandidate(
                        kind="web",
                        slug="custom-framework",
                        canonical="https://docs.example.test/custom",
                        url="https://docs.example.test/custom",
                        official=True,
                        confidence=0.99,
                        evidence=("fixture provider",),
                    )
                ]
            return []

    result = SourceResolver(providers=[Provider()]).resolve("custom framework")

    assert result.selected is not None
    assert result.selected.slug == "custom-framework"
    assert result.selected.provider == "fixture-provider"


def test_failed_name_provider_is_reported_without_crashing_resolution() -> None:
    class BrokenProvider:
        name = "broken-provider"

        def resolve(self, _value: str, **_kwargs: object):
            raise LookupError("provider unavailable")

    result = SourceResolver(providers=[BrokenProvider()]).resolve("unknown framework")

    assert result.selected is None
    assert result.error["code"] == "resolver_provider_failed"


def test_malformed_name_provider_fails_as_a_structured_resolution_result() -> None:
    class BrokenProvider:
        name = "broken-provider"

        def resolve(self, _value: str, **_kwargs: object):
            return 42

    result = SourceResolver(providers=[BrokenProvider()]).resolve("unknown framework")

    assert result.selected is None
    assert result.error is not None
    assert result.error["code"] == "resolver_provider_failed"
