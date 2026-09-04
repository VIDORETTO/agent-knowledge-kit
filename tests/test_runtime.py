# seam-scope: implementation-infrastructure (runtime discovery unit tests)
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from docops.pipeline import PipelineOptions, run_pipeline
from docops.runtime import discover_rag_python, runtime_contract, runtime_environment


def test_rag_python_discovery_accepts_explicit_override(tmp_path: Path) -> None:
    executable = tmp_path / "custom-python"
    executable.touch()

    result = discover_rag_python(tmp_path, environ={"DOCOPS_RAG_PYTHON": str(executable)})

    assert result.path == executable
    assert result.source == "environment"


def test_runtime_environment_does_not_embed_the_author_machine_path(tmp_path: Path) -> None:
    environment = runtime_environment(tmp_path, environ={"PATH": "fixture"})

    assert environment["KNOWLEDGE_RAG_DIR"] == str(tmp_path.resolve())
    assert environment["KNOWLEDGE_RAG_WATCHER_DISABLED"] == "1"
    assert "Documents\\Sistemas\\consulta-documentacao" not in environment["KNOWLEDGE_RAG_DIR"]


def test_runtime_environment_prefers_the_reviewed_vendor_server() -> None:
    root = Path(__file__).parents[1].resolve()
    environment = runtime_environment(root, environ={"PYTHONPATH": "inherited"})

    pythonpath = environment["PYTHONPATH"].split(os.pathsep)
    assert pythonpath[0] == str(root / "skills" / "vendor" / "knowledge-rag")
    assert pythonpath[1] == "inherited"


def test_runtime_environment_can_use_the_repo_vendor_for_a_generated_package(tmp_path: Path) -> None:
    root = Path(__file__).parents[1].resolve()
    vendor = root / "skills" / "vendor" / "knowledge-rag"
    environment = runtime_environment(tmp_path, vendor_root=vendor)

    assert environment["PYTHONPATH"].split(os.pathsep)[0] == str(root / "skills" / "vendor" / "knowledge-rag")


def test_runtime_contract_reads_version_from_the_selected_interpreter(tmp_path: Path) -> None:
    module = tmp_path / "mcp_server"
    module.mkdir()
    (module / "__init__.py").write_text('__version__ = "4.6.0"\n', encoding="utf-8")

    contract = runtime_contract(
        tmp_path,
        python=sys.executable,
        environ={"PYTHONPATH": str(tmp_path)},
    )

    assert contract["selected_version"] == "4.6.0"
    assert contract["expected_version"] == "4.6.0"
    assert contract["python_source"] == "explicit"


def test_generated_package_records_runtime_backend_provenance_without_author_paths(tmp_path: Path) -> None:
    source = tmp_path / "relative-source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\n", encoding="utf-8")
    output = tmp_path / "package"
    root = Path(__file__).parents[1].resolve()

    result = run_pipeline(
        "relative-source",
        options=PipelineOptions(
            output_dir=output, source_root=tmp_path, runtime_root=root, slug="guide", license="MIT"
        ),
    )

    assert result.ok, result.errors
    provenance = result.manifest["provenance"]["runtime"]
    assert provenance["backend_source"] == "reviewed-vendor"
    assert str(root) not in json.dumps(result.manifest)
