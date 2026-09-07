# seam-scope: implementation-infrastructure (continuous knowledge public seams)
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import docops
import docops.rag_sync as rag_sync


def _request(
    source: Path,
    output: Path,
    *,
    mode: str = "run",
    layers: tuple[str, ...] = ("conceptual", "factual"),
    publication_policy: str = "direct",
    index_rag: bool = False,
    runtime_root: Path | None = None,
) -> docops.OperationRequest:
    return docops.OperationRequest(
        source,
        docops.OperationOptions(
            output_dir=output,
            source_root=source.parent,
            slug="continuous-guide",
            license="MIT",
            mode=mode,
            layers=layers,
            publication_policy=publication_policy,
            index_rag=index_rag,
            runtime_root=runtime_root,
        ),
    )


def test_document_update_does_not_overwrite_externally_enriched_skill(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial factual policy.\n", encoding="utf-8")
    output = tmp_path / "package"

    created = docops.apply(docops.plan(_request(source, output)))
    assert created.ok, created.errors

    skill = output / "skill" / "SKILL.md"
    enriched = skill.read_text(encoding="utf-8") + (
        "\n## Externally reviewed mental model\n\nKeep conceptual guidance stable while factual documents evolve.\n"
    )
    skill.write_text(enriched, encoding="utf-8")
    document.write_text("# Guide\nUpdated factual policy.\n", encoding="utf-8")

    update_plan = docops.plan(_request(source, output, mode="update"))
    result = docops.apply(update_plan)

    assert not result.ok
    assert result.outcome["code"] == "skill_update_requires_review"
    assert skill.read_text(encoding="utf-8") == enriched
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == (
        "# Guide\nInitial factual policy.\n"
    )


def test_unchanged_generated_scaffold_remains_updatable(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial facts.\n", encoding="utf-8")
    output = tmp_path / "package"

    created = docops.apply(docops.plan(_request(source, output)))
    assert created.ok, created.errors
    skill_before = (output / "skill" / "SKILL.md").read_bytes()

    document.write_text("# Guide\nUpdated facts only.\n", encoding="utf-8")
    updated = docops.apply(docops.plan(_request(source, output, mode="update")))

    assert updated.ok, updated.errors
    assert (output / "skill" / "SKILL.md").read_bytes() == skill_before
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == ("# Guide\nUpdated facts only.\n")


def test_extra_skill_chapter_requires_review_before_update(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial facts.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok

    extra = output / "skill" / "chapters" / "99-external.md"
    extra.write_text("# External review\nKeep this chapter.\n", encoding="utf-8")
    document.write_text("# Guide\nUpdated facts.\n", encoding="utf-8")

    result = docops.apply(docops.plan(_request(source, output, mode="update")))

    assert not result.ok
    assert result.outcome["code"] == "skill_update_requires_review"
    assert extra.read_text(encoding="utf-8") == "# External review\nKeep this chapter.\n"


def test_removed_generated_skill_artifact_requires_review_before_update(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial facts.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok

    removed = output / "skill" / "patterns.md"
    removed.unlink()
    document.write_text("# Guide\nUpdated facts.\n", encoding="utf-8")

    result = docops.apply(docops.plan(_request(source, output, mode="update")))

    assert not result.ok
    assert result.outcome["code"] == "skill_update_requires_review"
    assert not removed.exists()


def test_legacy_package_without_artifact_baseline_requires_explicit_migration(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial facts.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok
    (output / ".docops" / "generated-artifacts.json").unlink()
    previous = (output / "skill" / "SKILL.md").read_bytes()

    document.write_text("# Guide\nUpdated facts.\n", encoding="utf-8")
    result = docops.apply(docops.plan(_request(source, output, mode="update")))

    assert not result.ok
    assert result.outcome["code"] == "artifact_baseline_required"
    assert (output / "skill" / "SKILL.md").read_bytes() == previous


def test_evaluation_is_invalidated_when_a_composition_artifact_changes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nKnown facts.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "reviewed": True,
                "cases": [
                    {
                        "query": "Guide",
                        "expected_filepath": "guide.md",
                        "kind": "factual",
                        "reviewed": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    evaluated = subprocess.run(
        [
            sys.executable,
            "-m",
            "docops",
            "evaluate",
            "--package",
            str(output),
            "--cases",
            str(cases),
            "--adapter",
            "memory",
            "--recall-threshold",
            "0",
            "--mrr-threshold",
            "0",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert evaluated.returncode == 0, evaluated.stdout + evaluated.stderr
    assert json.loads(evaluated.stdout)["ok"] is True

    router = output / "router" / "SKILL.md"
    router.write_text(router.read_text(encoding="utf-8") + "\nOut-of-band policy edit.\n", encoding="utf-8")

    inspection = docops.inspect(output)
    readiness = inspection["active"]["readiness"]
    assert readiness["evaluation"] == "pending"
    assert readiness["evaluation_status"] == "invalidated"


def test_repeated_evaluation_keeps_the_same_content_revision_identity(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nKnown facts.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok
    cases = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [{"query": "Guide", "expected_filepath": "guide.md", "reviewed": True}],
    }

    from docops.evaluator import evaluate_package
    from docops.retrieval import InMemoryRetrievalAdapter

    first = evaluate_package(output, cases, adapter=InMemoryRetrievalAdapter({"guide.md": "Guide"}))
    first_evidence = json.loads((output / ".docops" / "evaluation.json").read_text(encoding="utf-8"))
    second = evaluate_package(output, cases, adapter=InMemoryRetrievalAdapter({"guide.md": "Guide"}))
    second_evidence = json.loads((output / ".docops" / "evaluation.json").read_text(encoding="utf-8"))

    assert first.ok and second.ok
    assert first_evidence["revisions"] == second_evidence["revisions"]
    assert first_evidence["composition_hash"] == second_evidence["composition_hash"]


def test_factual_update_preserves_externally_enriched_conceptual_layers(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial factual policy.\n", encoding="utf-8")
    output = tmp_path / "package"

    created = docops.apply(docops.plan(_request(source, output)))
    assert created.ok, created.errors
    skill = output / "skill" / "SKILL.md"
    router = output / "router" / "SKILL.md"
    skill_before = skill.read_bytes()
    router_before = router.read_bytes()
    skill.write_bytes(skill_before + b"\n## External mental model\n\nPreserve this.\n")
    enriched_skill = skill.read_bytes()
    document.write_text("# Guide\nUpdated factual policy.\n", encoding="utf-8")

    result = docops.apply(docops.plan(_request(source, output, mode="update", layers=("factual",))))

    assert result.ok, result.errors
    assert skill.read_bytes() == enriched_skill
    assert router.read_bytes() == router_before
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == (
        "# Guide\nUpdated factual policy.\n"
    )
    inspection = docops.inspect(output)
    assert inspection["active"]["layers"]["updated"] == ["factual"]
    assert inspection["active"]["conceptual_lag"]["status"] == "pending_review"


def test_factual_update_removes_deleted_source_support_without_regenerating_skill(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    guide = source / "guide.md"
    appendix = source / "appendix.md"
    guide.write_text("# Guide\nStable guidance.\n", encoding="utf-8")
    appendix.write_text("# Appendix\nTemporary support.\n", encoding="utf-8")
    output = tmp_path / "package"

    created = docops.apply(docops.plan(_request(source, output)))
    assert created.ok, created.errors
    skill_before = (output / "skill" / "SKILL.md").read_bytes()
    router_before = (output / "router" / "SKILL.md").read_bytes()
    assert (output / "rag" / "documents" / "appendix.md").is_file()

    appendix.unlink()
    result = docops.apply(docops.plan(_request(source, output, mode="update", layers=("factual",))))

    assert result.ok, result.errors
    assert not (output / "rag" / "documents" / "appendix.md").exists()
    assert (output / "skill" / "SKILL.md").read_bytes() == skill_before
    assert (output / "router" / "SKILL.md").read_bytes() == router_before
    inspection = docops.inspect(output)
    assert inspection["active"]["layers"]["conceptual"] == "preserved"
    assert inspection["active"]["conceptual_lag"]["coverage"] == "unknown"


def test_unindexed_factual_update_remains_corpus_ready_without_starting_mcp(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial factual policy.\n", encoding="utf-8")
    output = tmp_path / "package"

    assert docops.apply(docops.plan(_request(source, output))).ok
    document.write_text("# Guide\nUpdated factual policy.\n", encoding="utf-8")

    result = docops.apply(docops.plan(_request(source, output, mode="update", layers=("factual",))))

    assert result.ok, result.errors
    index = json.loads((output / "rag" / "index.json").read_text(encoding="utf-8"))
    assert index["mode"] == "corpus-ready"
    assert index["smoke"]["status"] == "not-run"
    inspection = docops.inspect(output)
    assert inspection["active"]["readiness"]["rag"] == "corpus-ready"


def test_candidate_policy_keeps_active_generation_and_exposes_reviewable_candidate(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial factual policy.\n", encoding="utf-8")
    output = tmp_path / "package"

    created = docops.apply(docops.plan(_request(source, output)))
    assert created.ok, created.errors
    active_manifest = (output / "manifest.json").read_bytes()
    active_document = (output / "rag" / "documents" / "guide.md").read_bytes()

    document.write_text("# Guide\nCandidate factual policy.\n", encoding="utf-8")
    candidate_result = docops.apply(
        docops.plan(
            _request(
                source,
                output,
                mode="update",
                publication_policy="candidate",
            )
        )
    )

    assert candidate_result.ok, candidate_result.errors
    assert candidate_result.outcome["code"] == "candidate_prepared"
    assert candidate_result.outcome["candidate_id"]
    assert (output / "manifest.json").read_bytes() == active_manifest
    assert (output / "rag" / "documents" / "guide.md").read_bytes() == active_document

    inspection = docops.inspect(output)
    assert inspection["active"]["outcome"]["code"] == "completed"
    assert len(inspection["candidates"]) == 1
    candidate = inspection["candidates"][0]
    assert candidate["candidate_id"] == candidate_result.outcome["candidate_id"]
    assert candidate["status"] == "review_required"
    assert candidate["base_release_id"]
    assert candidate["revisions"]["composition_hash"] != inspection["active"]["revisions"]["composition_hash"]


def test_interrupted_candidate_resumes_and_rejects_arbitrary_candidate_entries(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial factual policy.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok
    document.write_text("# Guide\nResumable candidate policy.\n", encoding="utf-8")

    environment = {**os.environ, "DOCOPS_TEST_CANDIDATE_FAILPOINT": "after-stage"}
    interrupted = subprocess.run(
        [
            sys.executable,
            "-m",
            "docops",
            "run",
            str(source),
            "--output",
            str(output),
            "--mode",
            "update",
            "--publication-policy",
            "candidate",
            "--license",
            "MIT",
            "--slug",
            "continuous-guide",
            "--source-root",
            str(source.parent),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert interrupted.returncode == 87
    interrupted_inspection = docops.inspect(output)
    assert interrupted_inspection["active"]["outcome"]["code"] == "completed"
    assert len(interrupted_inspection["staging"]) == 1

    resumed = docops.apply(docops.plan(_request(source, output, mode="update", publication_policy="candidate")))
    assert resumed.ok, resumed.errors
    resumed_inspection = docops.inspect(output)
    assert len(resumed_inspection["staging"]) == 0
    assert len(resumed_inspection["candidates"]) == 1

    candidate_root = output.parent / f".{output.name}.candidates"
    (candidate_root / "arbitrary-path").mkdir()
    rejected = [item for item in docops.inspect(output)["candidates"] if item.get("candidate_id") == "arbitrary-path"]
    assert rejected and rejected[0]["status"] == "rejected"
    assert rejected[0]["code"] == "unsafe_candidate_path"


def test_structurally_invalid_candidate_is_rejected_and_cannot_be_validated(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial factual policy.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok
    active_manifest = (output / "manifest.json").read_bytes()

    document.write_text("# Guide\nCandidate with a structural defect.\n", encoding="utf-8")
    candidate_result = docops.apply(
        docops.plan(_request(source, output, mode="update", publication_policy="candidate"))
    )
    assert candidate_result.ok, candidate_result.errors
    candidate_id = candidate_result.outcome["candidate_id"]
    candidate_path = output.parent / f".{output.name}.candidates" / candidate_id
    (candidate_path / "manifest.json").unlink()

    validation = subprocess.run(
        [sys.executable, "-m", "docops", "validate", str(candidate_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert validation.returncode != 0
    rejected = [item for item in docops.inspect(output)["candidates"] if item.get("candidate_id") == candidate_id]
    assert rejected and rejected[0]["status"] == "rejected"
    assert rejected[0]["code"] == "candidate_validation_failed"
    assert (output / "manifest.json").read_bytes() == active_manifest


def test_candidate_policy_rejects_arbitrary_publication_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="publication_policy"):
        docops.OperationOptions(output_dir=tmp_path / "package", publication_policy="arbitrary")


def test_embedding_configuration_change_requests_a_full_rebuild(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nKnown facts.\n", encoding="utf-8")
    output = tmp_path / "package"
    reindex_arguments: list[dict[str, object]] = []

    class RecordingClient:
        server_info = {"version": "4.8.5"}

        def call(self, _method: str, *, name: str, arguments: dict[str, object], **_kwargs: object) -> dict:
            if name == "reindex_documents":
                reindex_arguments.append(dict(arguments))
                operation = "nuclear_rebuild" if arguments.get("full_rebuild") else "smart_reindex"
                payload = {"status": "started", "operation": operation}
            elif name == "get_reindex_status":
                payload = {"active": False, "last_result": {"errors": 0, "total_files": 1}}
            elif name == "get_index_stats":
                payload = {
                    "stats": {
                        "total_documents": 1,
                        "total_chunks": 1,
                        "embedding_model": "fixture-model",
                        "embedding_dim": 3,
                    }
                }
            else:
                payload = {"results": [{"source": "guide.md"}]}
            return {"result": {"content": [{"text": json.dumps(payload)}]}}

        def diagnostics(self, *, status: str) -> dict[str, object]:
            return {"status": status, "events": []}

        def close(self) -> None:
            return

    monkeypatch.setenv("DOCOPS_RAG_PYTHON", sys.executable)
    monkeypatch.setattr(rag_sync, "start_mcp_server", lambda *_args, **_kwargs: RecordingClient())
    options = {"index_rag": True, "runtime_root": tmp_path}

    first = docops.apply(docops.plan(_request(source, output, **options)))
    assert first.ok, first.errors

    config = output / "config.yaml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("profile: compact", "profile: quality"), encoding="utf-8"
    )

    second = docops.apply(docops.plan(_request(source, output, mode="update", **options)))

    assert second.ok, second.errors
    assert reindex_arguments == [{"force": True}, {"full_rebuild": True}]
    index = json.loads((output / "rag" / "index.json").read_text(encoding="utf-8"))
    assert index["profile"] == "quality"
    assert index["configuration"]["effective"]["model"] == "fixture-model"


def test_failed_indexing_does_not_prepare_a_candidate_or_change_active(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nInitial facts.\n", encoding="utf-8")
    output = tmp_path / "package"
    initial = docops.apply(docops.plan(_request(source, output)))
    assert initial.ok, initial.errors
    active_manifest = (output / "manifest.json").read_bytes()
    active_document = (output / "rag" / "documents" / "guide.md").read_bytes()

    document.write_text("# Guide\nCandidate facts.\n", encoding="utf-8")

    class FailedClient:
        server_info = {"version": "4.8.5"}

        def call(self, _method: str, *, name: str, **_kwargs: object) -> dict:
            payload = {
                "reindex_documents": {"status": "started", "operation": "smart_reindex"},
                "get_reindex_status": {
                    "active": False,
                    "last_error": {"code": "fixture_failure", "message": "synthetic failure"},
                },
            }.get(name, {"stats": {"total_documents": 1, "total_chunks": 1}})
            if name == "search_knowledge":
                payload = {"results": [{"source": "guide.md"}]}
            return {"result": {"content": [{"text": json.dumps(payload)}]}}

        def close(self) -> None:
            return

    monkeypatch.setenv("DOCOPS_RAG_PYTHON", sys.executable)
    monkeypatch.setattr(rag_sync, "start_mcp_server", lambda *_args, **_kwargs: FailedClient())
    failed = docops.apply(
        docops.plan(
            _request(
                source,
                output,
                mode="update",
                publication_policy="candidate",
                index_rag=True,
                runtime_root=tmp_path,
            )
        )
    )

    assert not failed.ok
    assert failed.outcome["phase"] == "index"
    assert failed.outcome["code"] == "rag_reindex_terminal_error"
    assert (output / "manifest.json").read_bytes() == active_manifest
    assert (output / "rag" / "documents" / "guide.md").read_bytes() == active_document
    assert docops.inspect(output)["candidates"] == []
