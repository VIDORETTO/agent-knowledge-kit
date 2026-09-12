"""Knowledge backend seams and adapters."""

from .base import (
    BackendCandidate,
    BackendError,
    BackendReceipt,
    BackendUnavailable,
    EvidenceResult,
    IndexRevision,
    KnowledgeBackend,
    ProbeResult,
    QueryRequest,
    SnapshotIdentity,
)
from .legacy_knowledge_rag import KnowledgeRagLegacyAdapter
from .ragflow import RagFlowAdapter

__all__ = [
    "BackendCandidate",
    "BackendError",
    "BackendReceipt",
    "BackendUnavailable",
    "EvidenceResult",
    "IndexRevision",
    "KnowledgeBackend",
    "KnowledgeRagLegacyAdapter",
    "ProbeResult",
    "QueryRequest",
    "RagFlowAdapter",
    "SnapshotIdentity",
]
