# seam-scope: implementation-infrastructure (adapter/evaluator unit tests)
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import docops.retrieval as retrieval_module
from docops.evaluator import evaluate_package, generate_golden_candidates
from docops.pipeline import PipelineOptions, run_pipeline
from docops.rag_sync import RagSynchronizer, package_rag_config_text
from docops.retrieval import InMemoryRetrievalAdapter, McpRetrievalAdapter, RetrievalError
from docops.revisions import package_revisions


def _package(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Authentication\nToken validation and errors.", encoding="utf-8")
    output = tmp_path / "package"
    result = run_pipeline(str(source), options=PipelineOptions(output_dir=output, slug="fixture", license="MIT"))
    assert result.ok
    return output


def _runtime_root(tmp_path: Path) -> Path:
    runtime = tmp_path / "runtime"
    vendor = runtime / "skills" / "vendor" / "knowledge-rag" / "mcp_server"
    vendor.mkdir(parents=True)
    (vendor / "__init__.py").write_text('__version__ = "4.8.5"\n', encoding="utf-8")
    return runtime


def test_real_mcp_reader_keeps_package_generation_immutable_during_query(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    root = Path(__file__).resolve().parents[1]
    package = _package(tmp_path)
    (package / "config.yaml").write_text(package_rag_config_text(), encoding="utf-8")

    indexed = RagSynchronizer(python=Path(sys.executable), runtime_root=root, timeout_seconds=120).sync(package)
    assert indexed.ok, indexed.error
    index_path = package / "rag" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["mode"] = "indexed"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    before = package_revisions(package)

    adapter = McpRetrievalAdapter(package, python=Path(sys.executable), runtime_root=root, timeout_seconds=120)
    try:
        hits = adapter.search("authentication token", max_results=1)
    finally:
        adapter.close()

    assert hits and hits[0]["source"] == "guide.md"
    assert package_revisions(package) == before


def test_evaluator_requires_reviewed_cases_and_reports_recall_and_mrr(tmp_path: Path) -> None:
    package = _package(tmp_path)
    cases = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [
            {
                "query": "Authentication token validation",
                "expected_filepath": "guide.md",
                "kind": "factual",
                "reviewed": True,
            }
        ],
    }

    result = evaluate_package(package, cases)

    assert result.ok
    assert result.metrics["recall_at_5"] == 1.0
    assert result.metrics["mrr_at_5"] == 1.0
    assert result.cases[0]["expected_found"] is True
    assert result.thresholds == {"recall_at_5": 0.85, "mrr_at_5": 0.7}


def test_memory_adapter_reports_a_real_adapter_contract(tmp_path: Path) -> None:
    package = _package(tmp_path)
    adapter = InMemoryRetrievalAdapter({"guide.md": "Authentication token validation and errors."})
    cases = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [{"query": "Authentication", "expected_filepath": "guide.md", "reviewed": True}],
    }

    result = evaluate_package(package, cases, adapter=adapter)

    assert result.ok, result.errors
    assert result.metadata["backend"] == "memory"
    assert result.metadata["mode"] == "gate"
    assert result.metadata["top_k"] == 5


def test_router_cases_measure_the_real_routing_decision(tmp_path: Path) -> None:
    package = _package(tmp_path)
    cases = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [
            {"query": "What is the exact default version?", "kind": "router", "expected_route": "rag", "reviewed": True}
        ],
    }

    result = evaluate_package(package, cases, adapter=InMemoryRetrievalAdapter({}))

    assert result.ok, result.errors
    assert result.metrics["route_accuracy"] == 1.0
    assert result.cases[0]["route"] == "rag"


def test_evaluator_metric_names_follow_the_requested_top_k(tmp_path: Path) -> None:
    package = _package(tmp_path)
    cases = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [{"query": "Authentication", "expected_filepath": "guide.md", "reviewed": True}],
    }

    result = evaluate_package(
        package,
        cases,
        top_k=1,
        thresholds={"recall_at_1": 1.0, "mrr_at_1": 1.0},
    )

    assert result.ok, result.errors
    assert result.metrics == {"recall_at_1": 1.0, "mrr_at_1": 1.0}
    assert result.thresholds == {"recall_at_1": 1.0, "mrr_at_1": 1.0}


def test_unreviewed_golden_candidates_cannot_be_used_as_a_quality_gate(tmp_path: Path) -> None:
    package = _package(tmp_path)
    candidates = generate_golden_candidates(package)
    result = evaluate_package(package, {"schema_version": 1, "cases": candidates})

    assert not result.ok
    assert any(error["code"] == "golden_not_reviewed" for error in result.errors)


def test_each_golden_case_must_be_reviewed_even_when_the_envelope_is_reviewed(tmp_path: Path) -> None:
    package = _package(tmp_path)
    result = evaluate_package(
        package,
        {
            "schema_version": 1,
            "reviewed": True,
            "cases": [{"query": "Authentication", "expected_filepath": "guide.md", "reviewed": False}],
        },
    )

    assert not result.ok
    assert any(error["code"] == "golden_not_reviewed" for error in result.errors)


def test_evaluator_includes_normalized_code_documents(tmp_path: Path) -> None:
    from docops.pipeline import PipelineOptions

    source = tmp_path / "source"
    source.mkdir()
    (source / "client.py").write_text("# Client\nBearer token validation.", encoding="utf-8")
    package = tmp_path / "package"
    assert run_pipeline(source, options=PipelineOptions(output_dir=package, slug="code", license="MIT")).ok

    result = evaluate_package(
        package,
        {
            "schema_version": 1,
            "reviewed": True,
            "cases": [{"query": "Bearer token validation", "expected_filepath": "client.py", "reviewed": True}],
        },
    )

    assert result.ok, result.errors


def test_evaluator_rejects_invalid_quality_gate_parameters(tmp_path: Path) -> None:
    package = _package(tmp_path)
    cases = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [
            {
                "query": "guide",
                "expected_filepath": "guide.md",
                "kind": "factual",
                "reviewed": True,
            }
        ],
    }

    result = evaluate_package(
        package,
        cases,
        thresholds={"recall_at_5": 1.1, "mrr_at_5": float("nan")},
        top_k=0,
    )

    assert not result.ok
    codes = {error["code"] for error in result.errors}
    assert {"top_k_out_of_range", "threshold_out_of_range"} <= codes


def test_evaluator_rejects_windows_absolute_golden_paths(tmp_path: Path) -> None:
    package = _package(tmp_path)
    result = evaluate_package(
        package,
        {
            "schema_version": 1,
            "reviewed": True,
            "cases": [
                {
                    "query": "Authentication",
                    "expected_filepath": "C:\\outside\\guide.md",
                    "reviewed": True,
                }
            ],
        },
    )

    assert not result.ok
    assert any(error["code"] == "golden_case_path" for error in result.errors)


def test_mcp_adapter_rejects_server_version_drift_before_search(tmp_path: Path, monkeypatch) -> None:
    package = _package(tmp_path)
    index_path = package / "rag" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["mode"] = "indexed"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    executable = tmp_path / "python.exe"
    executable.touch()

    class FakeClient:
        server_info = {"name": "knowledge-rag", "version": "4.6.0"}

        def call(self, *_args: object, **_kwargs: object) -> dict:
            return {"result": {"content": [{"text": json.dumps({"results": []})}]}}

        def close(self) -> None:
            return

    monkeypatch.setattr(retrieval_module, "start_mcp_server", lambda *_args, **_kwargs: FakeClient())
    adapter = McpRetrievalAdapter(package, python=executable, runtime_root=_runtime_root(tmp_path))

    with pytest.raises(RetrievalError) as caught:
        adapter.search("authentication", max_results=1)

    assert caught.value.code == "rag_version_mismatch"
    adapter.close()


def test_mcp_adapter_does_not_return_external_source_paths(tmp_path: Path, monkeypatch) -> None:
    package = _package(tmp_path)
    index_path = package / "rag" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["mode"] = "indexed"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    executable = tmp_path / "python.exe"
    executable.touch()

    class FakeClient:
        server_info = {"name": "knowledge-rag", "version": "4.8.5"}

        def call(self, *_args: object, **_kwargs: object) -> dict:
            return {
                "result": {
                    "content": [
                        {
                            "text": json.dumps(
                                {
                                    "results": [
                                        {
                                            "source": str(tmp_path / "outside" / "private.md"),
                                            "content": "private corpus",
                                            "score": 1.0,
                                        }
                                    ]
                                }
                            )
                        }
                    ]
                }
            }

        def close(self) -> None:
            return

    monkeypatch.setattr(retrieval_module, "start_mcp_server", lambda *_args, **_kwargs: FakeClient())
    adapter = McpRetrievalAdapter(package, python=executable, runtime_root=_runtime_root(tmp_path))

    hits = adapter.search("private", max_results=1)

    assert hits[0]["source"] == "<external-source>"
    assert str(tmp_path) not in json.dumps(hits)
    adapter.close()


def test_mcp_adapter_pins_generation_and_starts_a_reader_session(tmp_path: Path, monkeypatch) -> None:
    package = _package(tmp_path)
    index_path = package / "rag" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["mode"] = "indexed"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    executable = tmp_path / "python.exe"
    executable.touch()
    runtime = _runtime_root(tmp_path)
    captured: dict[str, object] = {}

    class FakeClient:
        server_info = {"name": "knowledge-rag", "version": "4.8.5"}

        def call(self, *_args: object, **_kwargs: object) -> dict:
            return {"result": {"content": [{"text": json.dumps({"results": []})}]}}

        def close(self) -> None:
            return

    def fake_start(*_args: object, **kwargs: object) -> FakeClient:
        captured["start_kwargs"] = kwargs
        return FakeClient()

    monkeypatch.setattr(retrieval_module, "start_mcp_server", fake_start)
    adapter = McpRetrievalAdapter(package, python=executable, runtime_root=runtime)

    assert adapter.search("authentication", max_results=1) == []
    assert captured["start_kwargs"]
    environment = captured["start_kwargs"]
    assert isinstance(environment, dict)
    # The adapter passes the environment to start_mcp_server as a keyword.
    assert environment["env"]["KNOWLEDGE_RAG_READ_ONLY"] == "1"

    skill_file = next((package / "skill").rglob("*.md"))
    skill_file.write_text(skill_file.read_text(encoding="utf-8") + "\nGeneration changed.\n", encoding="utf-8")
    with pytest.raises(RetrievalError) as caught:
        adapter.search("authentication", max_results=1)
    assert caught.value.code == "generation_changed"
    adapter.close()


def test_mcp_adapter_filters_revoked_sources_from_backend_results(tmp_path: Path, monkeypatch) -> None:
    package = _package(tmp_path)
    index_path = package / "rag" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["mode"] = "indexed"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    revocations = package / ".docops" / "revocations.json"
    revocations.parent.mkdir(exist_ok=True)
    revocations.write_text(json.dumps({"sources": [{"destinations": ["guide.md"]}]}), encoding="utf-8")
    executable = tmp_path / "python.exe"
    executable.touch()
    runtime = _runtime_root(tmp_path)

    class FakeClient:
        server_info = {"name": "knowledge-rag", "version": "4.8.5"}

        def call(self, *_args: object, **_kwargs: object) -> dict:
            return {
                "result": {
                    "content": [
                        {"text": json.dumps({"results": [{"source": "guide.md", "content": "revoked", "score": 1.0}]})}
                    ]
                }
            }

        def close(self) -> None:
            return

    monkeypatch.setattr(retrieval_module, "start_mcp_server", lambda *_args, **_kwargs: FakeClient())
    adapter = McpRetrievalAdapter(package, python=executable, runtime_root=runtime)

    assert adapter.search("authentication", max_results=1) == []
    adapter.close()
