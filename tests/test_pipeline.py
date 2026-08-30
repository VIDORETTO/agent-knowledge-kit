from __future__ import annotations

import json
import subprocess
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

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
    assert (output / "config.yaml").is_file()
    assert (output / "rag" / "documents" / "guide.md").is_file()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"]["config"] == "config.yaml"


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


def test_pipeline_preserves_an_existing_package_rag_configuration(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nStable content.", encoding="utf-8")
    output = tmp_path / "package"
    first = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))
    assert first.ok, first.errors

    custom_config = "server:\n  transport: stdio\n# custom package setting\n"
    (output / "config.yaml").write_text(custom_config, encoding="utf-8")
    second = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT", mode="update"))

    assert second.ok, second.errors
    assert (output / "config.yaml").read_text(encoding="utf-8") == custom_config


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


def test_update_removes_a_previous_destination_when_source_format_changes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    original = source / "guide.html"
    original.write_text("<html><body><h1>Guide</h1><p>HTML version.</p></body></html>", encoding="utf-8")
    output = tmp_path / "package"

    first = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))
    assert first.ok, first.errors
    assert (output / "rag" / "documents" / "guide.md").is_file()

    original.unlink()
    (source / "guide.md").write_text("# Guide\nMarkdown version.", encoding="utf-8")
    second = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT", mode="update"))

    assert second.ok, second.errors
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8").endswith("Markdown version.\n")
    assert second.state_diff["removed"] == 0
    assert validate_package(output).ok


def test_local_documents_with_colliding_normalized_names_are_kept_separately(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.html").write_text("<html><body><h1>HTML Guide</h1><p>HTML.</p></body></html>", encoding="utf-8")
    (source / "guide.md").write_text("# Markdown Guide\nMarkdown.", encoding="utf-8")
    output = tmp_path / "package"

    result = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))

    assert result.ok, result.errors
    documents = [path for path in (output / "rag" / "documents").rglob("*") if path.is_file()]
    assert len(documents) == 2
    assert len({path.name for path in documents}) == 2
    assert validate_package(output).ok


def test_pipeline_rejects_an_output_directory_inside_the_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    guide = source / "guide.md"
    guide.write_text("# Guide\n", encoding="utf-8")
    output = source / "generated"

    result = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))

    assert not result.ok
    assert any(error["code"] == "output_inside_source" for error in result.errors)
    assert not output.exists()
    assert guide.read_text(encoding="utf-8") == "# Guide\n"


def test_pipeline_rejects_an_output_path_equal_to_the_source_file(tmp_path: Path) -> None:
    source = tmp_path / "guide.md"
    source.write_text("# Guide\n", encoding="utf-8")

    result = run_pipeline(source, options=PipelineOptions(output_dir=source, slug="guide", license="MIT"))

    assert not result.ok
    assert any(error["code"] == "output_inside_source" for error in result.errors)
    assert source.read_text(encoding="utf-8") == "# Guide\n"


def test_symlinked_documents_are_not_ingested_from_outside_the_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside secret\n", encoding="utf-8")
    link = source / "linked.md"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this host")

    output = tmp_path / "package"
    result = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))

    assert not result.ok
    assert any(error["code"] == "no_accepted_documents" for error in result.errors)
    documents = output / "rag" / "documents"
    assert not documents.is_file()
    assert not list(documents.rglob("*")) if documents.is_dir() else True


def test_update_keeps_new_content_when_old_source_has_the_same_destination(tmp_path: Path) -> None:
    first_source = tmp_path / "first"
    second_source = tmp_path / "second"
    first_source.mkdir()
    second_source.mkdir()
    (first_source / "guide.md").write_text("# First\n", encoding="utf-8")
    (second_source / "guide.md").write_text("# Second\n", encoding="utf-8")
    output = tmp_path / "package"

    first = run_pipeline(first_source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))
    assert first.ok, first.errors
    second = run_pipeline(second_source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT", mode="update"))

    assert second.ok, second.errors
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == "# Second\n"


def test_update_removes_generated_chapters_for_deleted_sources(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "one.md").write_text("# One\n", encoding="utf-8")
    (source / "two.md").write_text("# Two\n", encoding="utf-8")
    output = tmp_path / "package"

    first = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))
    assert first.ok, first.errors
    generated = sorted((output / "skill" / "chapters").glob("*.md"))
    assert len(generated) == 2

    (source / "two.md").unlink()
    second = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT", mode="update"))

    assert second.ok, second.errors
    remaining = sorted((output / "skill" / "chapters").glob("*.md"))
    assert len(remaining) == 1
    assert generated[1] not in remaining


def test_failed_normalization_does_not_delete_an_existing_package(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    guide = source / "guide.md"
    guide.write_text("# Guide\nKeep this version.", encoding="utf-8")
    output = tmp_path / "package"

    first = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT"))
    assert first.ok, first.errors
    previous = (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8")

    (source / "broken.xlsx").write_bytes(b"not an OOXML workbook")
    second = run_pipeline(source, options=PipelineOptions(output_dir=output, slug="guide", license="MIT", mode="update"))

    assert not second.ok
    assert any(error["code"] == "invalid_document" for error in second.errors)
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == previous
