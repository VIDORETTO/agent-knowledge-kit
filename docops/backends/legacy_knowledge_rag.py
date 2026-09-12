"""Compatibility adapter for the 1.x knowledge-rag/MCP implementation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from ..rag_sync import RagSynchronizer
from ..retrieval import InMemoryRetrievalAdapter, RetrievalAdapter, RetrievalError
from ..revisions import content_hash
from ..runtime import runtime_provenance
from .base import (
    BackendCandidate,
    BackendReceipt,
    BackendUnavailable,
    EvidenceResult,
    IndexRevision,
    ProbeResult,
    QueryRequest,
    SnapshotIdentity,
)


class KnowledgeRagLegacyAdapter:
    """Keep legacy process/vendor details behind the v2 backend seam.

    The adapter is intentionally injectable.  Production compatibility uses
    ``RagSynchronizer`` and ``McpRetrievalAdapter``; tests and the provider-free
    fixture can use the public in-memory adapter without mocking internals.
    """

    backend_name = "knowledge-rag"

    def __init__(
        self,
        package_root: Path | str,
        *,
        retrieval: RetrievalAdapter | None = None,
        synchronizer: RagSynchronizer | None = None,
        runtime_root: Path | str | None = None,
    ) -> None:
        self.package_root = Path(package_root).resolve()
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else self.package_root
        self.retrieval = retrieval
        self.synchronizer = synchronizer or RagSynchronizer(runtime_root=self.runtime_root)
        self._closed = False
        self._candidates: dict[str, BackendCandidate] = {}

    def probe(self, config: Mapping[str, Any] | None = None) -> ProbeResult:
        if self._closed:
            return ProbeResult(self.backend_name, "closed")
        configured = dict(config or {})
        runtime = runtime_provenance(self.runtime_root, expected_version=configured.get("expected_version"))
        available = self.retrieval is not None or runtime.get("backend_version") is not None
        return ProbeResult(
            self.backend_name,
            "healthy" if available else "unavailable",
            version=str(runtime.get("backend_version")) if runtime.get("backend_version") else None,
            capabilities=("prepare", "apply", "query", "snapshot", "discard", "close") if available else (),
            health={"available": available},
            diagnostics={"source": runtime.get("backend_source", "unavailable")},
        )

    def prepare(self, project_revision: str, ir_revision: str) -> BackendCandidate:
        self._ensure_open()
        if not project_revision or not ir_revision:
            raise ValueError("project_revision and ir_revision are required")
        candidate_id = (
            "backend-candidate-"
            + hashlib.sha256(f"{self.backend_name}:{project_revision}:{ir_revision}".encode("utf-8")).hexdigest()[:24]
        )
        candidate = BackendCandidate(candidate_id, project_revision, ir_revision, self.backend_name, "prepared")
        existing = self._candidates.get(candidate_id)
        if existing is not None:
            return existing
        self._candidates[candidate_id] = candidate
        return candidate

    def apply(self, candidate: BackendCandidate) -> IndexRevision:
        self._ensure_open()
        self._assert_owned_candidate(candidate)
        if self.retrieval is None:
            result = self.synchronizer.sync(self.package_root)
            if not result.ok:
                error = result.error or {"code": "backend_unavailable", "message": "legacy backend failed"}
                raise BackendUnavailable(str(error.get("code", "backend_unavailable")), "legacy backend unavailable")
        identity = content_hash(
            {
                "backend": self.backend_name,
                "candidate_id": candidate.candidate_id,
                "project_revision": candidate.project_revision,
                "ir_revision": candidate.ir_revision,
            }
        )
        return IndexRevision(
            index_revision=f"index-{identity[:24]}",
            project_revision=candidate.project_revision,
            ir_revision=candidate.ir_revision,
            backend=self.backend_name,
            backend_version="4.8.5",
            state="queryable",
            mapping_hash=identity,
            external_ids={},
            fingerprints={"adapter": "knowledge-rag-legacy-v1"},
        )

    def query(self, index_revision: IndexRevision, query_request: QueryRequest) -> EvidenceResult:
        self._ensure_open()
        if index_revision.backend != self.backend_name:
            raise BackendUnavailable("backend_mismatch", "index revision belongs to another backend")
        if index_revision.state != "queryable":
            raise BackendUnavailable("index_not_queryable", "index revision is not queryable")
        adapter = self.retrieval or InMemoryRetrievalAdapter.from_package(self.package_root)
        try:
            hits = adapter.search(query_request.query, max_results=query_request.top_k)
        except RetrievalError as exc:
            raise BackendUnavailable(exc.code, "legacy backend query failed") from exc
        return EvidenceResult(
            index_revision=index_revision.index_revision,
            query=query_request,
            hits=hits,
            outcome="ok" if hits else "insufficient_evidence",
            metadata={"backend": self.backend_name, "adapter": "legacy"},
        )

    def snapshot(self, index_revision: IndexRevision) -> SnapshotIdentity:
        self._ensure_open()
        return SnapshotIdentity(
            snapshot_id=f"snapshot-{index_revision.index_revision}",
            index_revision=index_revision.index_revision,
            content_hash=content_hash(index_revision.to_dict()),
        )

    def discard(self, candidate: BackendCandidate) -> BackendReceipt:
        self._ensure_open()
        self._assert_owned_candidate(candidate)
        self._candidates.pop(candidate.candidate_id, None)
        return BackendReceipt("discarded", "discard", candidate_id=candidate.candidate_id)

    def close(self) -> BackendReceipt:
        if not self._closed:
            if self.retrieval is not None:
                self.retrieval.close()
            self._closed = True
        return BackendReceipt("closed", "close")

    def _ensure_open(self) -> None:
        if self._closed:
            raise BackendUnavailable("backend_closed", "backend is closed")

    def _assert_owned_candidate(self, candidate: BackendCandidate) -> None:
        if self._candidates.get(candidate.candidate_id) != candidate:
            raise BackendUnavailable("candidate_unknown", "backend candidate is not owned by this adapter")


# Name used in the plan and the shorter public spelling used by callers.
KnowledgeRagLegacyAdapter = KnowledgeRagLegacyAdapter
