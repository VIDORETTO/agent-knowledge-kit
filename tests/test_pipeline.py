from __future__ import annotations

import json
import subprocess
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from docops.package_validator import validate_package
from docops.pipeline import PipelineOptions, run_pipeline


@contextmanager
def _server() -> str:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] != "/docs":
                self.send_response(404)
                self.end_headers()
                return
            body = b"<html><head><link rel='canonical' href='/docs'></head><body><h1>Fixture Docs</h1><p>Use this page.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/docs"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_folder_produces_valid_skill_router_rag_and_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text(
        "# Acme Guide\n\n## Authentication\nUse a token.\n\n## Errors\nReturn JSON errors.",
        encoding="utf-8",
    )
    (source / "ignored.png").write_bytes(b"binary")
    output = tmp_path / "package"

    result = run_pipeline(
        str(source),
        options=PipelineOptions(output_dir=output, slug="acme", license="MIT"),
    )

    assert result.ok, result.errors
    assert validate_package(output).ok
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["slug"] == "acme"
    assert manifest["source"]["license"] == "MIT"
    assert manifest["counts"]["accepted"] == 1
    assert (output / "skill" / "SKILL.md").is_file()
    assert (output / "router" / "SKILL.md").is_file()
    assert (output / "harness.json").is_file()
    assert (output / "rag" / "documents" / "guide.md").is_file()


def test_repeating_the_same_local_run_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nStable content.", encoding="utf-8")
    output = tmp_path / "package"
    options = PipelineOptions(output_dir=output, slug="acme", license="MIT")

    first = run_pipeline(str(source), options=options)
    second = run_pipeline(str(source), options=options)

    assert first.ok and second.ok
    assert second.state_diff["added"] == 0
    assert second.state_diff["updated"] == 0
    assert second.state_diff["removed"] == 0
    assert second.written_files == 0


def test_absolute_source_paths_do_not_enter_package_checkpoints(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nStable content.", encoding="utf-8")
    output = tmp_path / "package"

    result = run_pipeline(
        str(source.resolve()),
        options=PipelineOptions(output_dir=output, slug="acme", license="MIT"),
    )

    assert result.ok, result.errors
    checkpoint_text = (output / ".docops" / "checkpoints.json").read_text(encoding="utf-8")
    assert str(source.resolve()) not in checkpoint_text


def test_local_files_with_the_same_basename_keep_unique_manifest_sources(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "one").mkdir(parents=True)
    (source / "two").mkdir()
    (source / "one" / "guide.md").write_text("# One\n", encoding="utf-8")
    (source / "two" / "guide.md").write_text("# Two\n", encoding="utf-8")
    output = tmp_path / "package"

    result = run_pipeline(
        str(source),
        options=PipelineOptions(output_dir=output, slug="acme", license="MIT"),
    )

    assert result.ok, result.errors
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    canonical_sources = [entry["canonical"] for entry in manifest["entries"] if entry["status"] == "accepted"]
    assert len(canonical_sources) == 2
    assert len(set(canonical_sources)) == 2


def test_single_web_page_produces_queryable_provenance_package(tmp_path: Path) -> None:
    with _server() as url:
        result = run_pipeline(
            url,
            options=PipelineOptions(
                output_dir=tmp_path / "package",
                slug="web-fixture",
                license="fixture",
                allow_private_network=True,
                max_pages=1,
            ),
        )

    assert result.ok, result.errors
    assert validate_package(tmp_path / "package").ok
    manifest = json.loads((tmp_path / "package" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["kind"] == "web"
    assert manifest["entries"][0]["canonical"].endswith("/docs")
    assert "Fixture Docs" in (tmp_path / "package" / "rag" / "documents" / "docs.md").read_text(encoding="utf-8")


def test_local_repository_input_uses_only_detected_documentation_tree(tmp_path: Path) -> None:
    source = tmp_path / "repo"
    (source / "docs").mkdir(parents=True)
    (source / "docs" / "guide.md").write_text("# Repo Guide\n", encoding="utf-8")
    (source / "README.md").write_text("# Repository\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=source, check=True, capture_output=True)

    result = run_pipeline(
        source,
        options=PipelineOptions(output_dir=tmp_path / "package", slug="repo", license="MIT"),
    )

    assert result.ok, result.errors
    assert (tmp_path / "package" / "rag" / "documents" / "guide.md").is_file()
    assert not (tmp_path / "package" / "rag" / "documents" / "README.md").is_file()


def test_public_redistribution_fails_closed_when_license_is_unknown(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\n", encoding="utf-8")

    result = run_pipeline(
        source,
        options=PipelineOptions(output_dir=tmp_path / "package", slug="guide", redistribution="public"),
    )

    assert not result.ok
    assert any(error["code"] == "license_required" for error in result.errors)
