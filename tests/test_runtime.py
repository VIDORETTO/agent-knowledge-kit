from __future__ import annotations

from pathlib import Path

from docops.runtime import discover_rag_python, runtime_environment


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
