# seam-scope: implementation-infrastructure (public backend contract fixtures)
from __future__ import annotations

from pathlib import Path

import pytest

from docops.backends import (
    BackendCandidate,
    BackendUnavailable,
    EvidenceResult,
    IndexRevision,
    KnowledgeRagLegacyAdapter,
    QueryRequest,
    SnapshotIdentity,
)
from docops.contracts import validate_artifact
from docops.retrieval import InMemoryRetrievalAdapter
from docops.revisions import content_hash


def test_legacy_adapter_exposes_only_the_v2_backend_lifecycle() -> None:
    package = Path("fixture-package")
    retrieval = InMemoryRetrievalAdapter({"guide.md": "A stable factual guide."})
    adapter = KnowledgeRagLegacyAdapter(package, retrieval=retrieval)

    probe = adapter.probe({"backend": "memory"})
    candidate = adapter.prepare("project-revision-1", "ir-revision-1")
    index = adapter.apply(candidate)
    result = adapter.query(index, QueryRequest(query="stable factual", top_k=3, project_revision="project-revision-1"))
    snapshot = adapter.snapshot(index)
    discarded = adapter.discard(candidate)
    closed = adapter.close()

    assert probe.backend == "knowledge-rag"
    assert candidate.state == "prepared"
    assert index.state == "queryable"
    assert result.hits[0]["source"] == "guide.md"
    assert snapshot.index_revision == index.index_revision
    assert discarded.status == "discarded"
    assert closed.status == "closed"


def test_legacy_adapter_rejects_query_after_close_without_leaking_runtime_details() -> None:
    adapter = KnowledgeRagLegacyAdapter(Path("fixture-package"), retrieval=InMemoryRetrievalAdapter({"a": "b"}))
    candidate = adapter.prepare("project", "ir")
    index = adapter.apply(candidate)
    adapter.close()

    with pytest.raises(BackendUnavailable) as caught:
        adapter.query(index, QueryRequest(query="b", top_k=1, project_revision="project"))

    assert caught.value.code == "backend_closed"
    assert "fixture-package" not in str(caught.value)


def test_backend_dtos_use_canonical_identity_not_external_ids() -> None:
    candidate = BackendCandidate(
        candidate_id="candidate-1",
        project_revision="project-1",
        ir_revision="ir-1",
        backend="knowledge-rag",
        state="prepared",
    )
    index = IndexRevision(
        index_revision="index-1",
        project_revision="project-1",
        ir_revision="ir-1",
        backend="knowledge-rag",
        backend_version="4.8.5",
        state="queryable",
        mapping_hash=content_hash({"canonical": "block-1"}),
        external_ids={"dataset": "opaque-dataset-id"},
    )
    evidence = EvidenceResult(
        index_revision=index.index_revision,
        query=QueryRequest(query="guide", top_k=1, project_revision="project-1"),
        hits=[{"block_id": "block-1", "source": "guide.md", "locator": {"kind": "line", "label": "1"}}],
    )
    snapshot = SnapshotIdentity(
        snapshot_id="snapshot-1",
        index_revision=index.index_revision,
        content_hash=content_hash(index.to_dict()),
    )

    assert candidate.to_dict()["candidate_id"] == "candidate-1"
    assert index.to_dict()["external_ids"] == {"dataset": "opaque-dataset-id"}
    assert evidence.to_dict()["hits"][0]["block_id"] == "block-1"
    assert snapshot.to_dict()["content_hash"] == content_hash(index.to_dict())
    assert validate_artifact("backend-candidate", candidate.to_dict()).ok
    assert validate_artifact("index-revision", index.to_dict()).ok
    assert validate_artifact("query-request-v2", evidence.query.to_dict()).ok
    assert validate_artifact("evidence-result-v2", evidence.to_dict()).ok
