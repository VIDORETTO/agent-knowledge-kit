from __future__ import annotations

import json
from pathlib import Path

from docops.manifest import build_manifest, redact_url, write_manifest
from docops.source_resolver import SourceResolver


def test_manifest_preserves_resolution_provenance_and_entry_outcomes(tmp_path: Path) -> None:
    resolution = SourceResolver(root=tmp_path).resolve("https://docs.example.test/guide#section")
    manifest = build_manifest(
        resolution,
        entries=[
            {"source": "https://docs.example.test/guide", "status": "accepted", "destination": "guide.md"},
            {"source": "https://docs.example.test/logo.svg", "status": "ignored", "reason": "asset"},
        ],
        provenance={"license": "unknown", "redistribution": "private-only"},
        artifacts={"skill": "skill", "router": "router", "rag": "rag"},
        run_id="run-test",
        created_at="2026-08-28T12:00:00Z",
    )

    assert manifest["schema_version"] == 1
    assert manifest["run_id"] == "run-test"
    assert manifest["source"]["canonical"] == "https://docs.example.test/guide"
    assert manifest["counts"] == {"accepted": 1, "ignored": 1, "errors": 0}
    assert manifest["provenance"]["license"] == "unknown"

    output = tmp_path / "manifest.json"
    write_manifest(output, manifest)
    assert json.loads(output.read_text(encoding="utf-8"))["run_id"] == "run-test"


def test_manifest_redacts_credentials_even_when_input_url_contains_userinfo(tmp_path: Path) -> None:
    resolution = SourceResolver(root=tmp_path).resolve("https://user:secret@example.test/docs")

    manifest = build_manifest(resolution, entries=[], provenance={"license": "unknown"}, artifacts={})

    text = json.dumps(manifest)
    assert "secret" not in text
    assert "user:" not in text


def test_manifest_redacts_credentials_in_catalog_candidates(tmp_path: Path) -> None:
    resolution = SourceResolver(
        [{
            "names": ["private"],
            "slug": "private",
            "docs_url": "https://user:secret@example.test/docs",
            "official": True,
            "confidence": 0.9,
        }]
    ).resolve("private")

    text = json.dumps(build_manifest(resolution, entries=[], provenance={"license": "unknown"}, artifacts={}))

    assert "secret" not in text
    assert "user:" not in text


def test_manifest_redacts_sensitive_query_parameters() -> None:
    value = redact_url("https://docs.example.test/guide?api_key=secret-value&lang=en")

    assert "secret-value" not in value
    assert "REDACTED" in value
    assert "lang=en" in value


def test_manifest_redacts_local_machine_paths(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    resolution = SourceResolver(root=tmp_path).resolve(str(source))

    text = json.dumps(build_manifest(resolution, entries=[], provenance={"license": "MIT"}, artifacts={}))

    assert str(tmp_path) not in text
    assert "file://local/docs" in text
