"""Pure policy for deciding when factual changes merit conceptual review.

The policy is intentionally independent from SQLite and from any language
model. The lifecycle store supplies an event projection and records the
resulting request durably; this module only classifies impact and applies the
documented thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class TriggerPolicy:
    """Defaults for the pilot's conceptual-enrichment batching policy."""

    min_documents: int = 10
    min_documents_with_fraction: int = 3
    corpus_fraction: float = 0.10
    max_wait_seconds: float = 24 * 60 * 60
    min_changed_chars: int = 20_000
    max_requests_per_day: int = 4

    def __post_init__(self) -> None:
        if self.min_documents < 1 or self.min_documents_with_fraction < 1:
            raise ValueError("document thresholds must be positive")
        if not 0 < self.corpus_fraction <= 1:
            raise ValueError("corpus_fraction must be in (0, 1]")
        if self.max_wait_seconds <= 0 or self.min_changed_chars < 1 or self.max_requests_per_day < 1:
            raise ValueError("trigger limits must be positive")


@dataclass(frozen=True)
class TriggerDecision:
    """Explainable result of one trigger-policy evaluation."""

    requested: bool
    reasons: tuple[str, ...] = ()
    affected_documents: int = 0
    affected_chars: int = 0
    critical: bool = False
    oldest_event_at: float | None = None
    policy: TriggerPolicy = field(default_factory=TriggerPolicy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "reasons": list(self.reasons),
            "affected_documents": self.affected_documents,
            "affected_chars": self.affected_chars,
            "critical": self.critical,
            "oldest_event_at": self.oldest_event_at,
            "thresholds": {
                "min_documents": self.policy.min_documents,
                "min_documents_with_fraction": self.policy.min_documents_with_fraction,
                "corpus_fraction": self.policy.corpus_fraction,
                "max_wait_seconds": self.policy.max_wait_seconds,
                "min_changed_chars": self.policy.min_changed_chars,
                "max_requests_per_day": self.policy.max_requests_per_day,
            },
        }


def _event_time(event: Mapping[str, Any]) -> float | None:
    value = event.get("occurred_at") or event.get("created_at")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = event.get("payload")
    return raw if isinstance(raw, Mapping) else {}


def _is_conceptual_candidate(event: Mapping[str, Any]) -> bool:
    event_type = str(event.get("event_type") or event.get("type") or "")
    if event_type not in {"document.changed", "source.reconcile", "source.revoked", "source.conflict"}:
        return False
    payload = _payload(event)
    if payload.get("reindex_only") is True or payload.get("facts_only") is True:
        return False
    if payload.get("conceptual_impact") is False:
        return False
    return True


def assess_skill_trigger(
    events: Sequence[Mapping[str, Any]],
    *,
    corpus_documents: int,
    now: float,
    last_trigger_at: float | None = None,
    policy: TriggerPolicy | None = None,
) -> TriggerDecision:
    """Evaluate net, distinct conceptual impact in a bounded event window.

    Events are deduplicated by stable source identity. Reindex-only events,
    known factual-only changes and events before the last trigger do not count.
    A caller can run this function after every event without double-counting a
    burst.
    """

    selected: dict[str, Mapping[str, Any]] = {}
    active_policy = policy or TriggerPolicy()
    for event in events:
        if not _is_conceptual_candidate(event):
            continue
        timestamp = _event_time(event)
        if last_trigger_at is not None and timestamp is not None and timestamp <= last_trigger_at:
            continue
        payload = _payload(event)
        identity = str(
            event.get("source_id")
            or payload.get("document_identity")
            or payload.get("source")
            or event.get("observed_revision")
            or event.get("event_id")
        )
        if payload.get("reverted") is True:
            selected.pop(identity, None)
            continue
        selected[identity] = event

    if not selected:
        return TriggerDecision(False, policy=active_policy)
    affected_documents = len(selected)
    affected_chars = 0
    critical = False
    timestamps: list[float] = []
    for event in selected.values():
        payload = _payload(event)
        raw_chars = payload.get("normalized_chars", 0)
        if isinstance(raw_chars, (int, float)) and not isinstance(raw_chars, bool):
            affected_chars += max(0, int(raw_chars))
        event_type = str(event.get("event_type") or event.get("type") or "")
        critical = critical or bool(
            payload.get("critical") is True or event_type in {"source.revoked", "source.conflict"}
        )
        timestamp = _event_time(event)
        if timestamp is not None:
            timestamps.append(timestamp)

    oldest = min(timestamps) if timestamps else None
    reasons: list[str] = []
    if affected_documents >= active_policy.min_documents:
        reasons.append("document_count")
    if (
        affected_documents >= active_policy.min_documents_with_fraction
        and corpus_documents > 0
        and affected_documents / corpus_documents >= active_policy.corpus_fraction
    ):
        reasons.append("corpus_fraction")
    if affected_chars >= active_policy.min_changed_chars:
        reasons.append("changed_characters")
    if oldest is not None and now - oldest >= active_policy.max_wait_seconds:
        reasons.append("max_wait")
    if critical:
        reasons.append("critical_impact")
    return TriggerDecision(
        bool(reasons),
        tuple(reasons),
        affected_documents,
        affected_chars,
        critical,
        oldest,
        active_policy,
    )
