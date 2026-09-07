"""Deterministic conceptual-impact cursors and bounded enrichment triggers."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contracts import validate_artifact
from .revisions import content_hash
from .storage import write_json_atomic

TRIGGER_SCHEMA_VERSION = 1
DEFAULT_THRESHOLD = 10
DEFAULT_MAX_BATCHES_PER_DAY = 4
DEFAULT_CORPUS_DOCUMENTS = 100


class ConceptualTriggerError(ValueError):
    """Raised when an impact event cannot be admitted safely."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _parse_time(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ConceptualTriggerError("time_invalid", "impact times must be RFC3339") from exc
    if parsed.tzinfo is None:
        raise ConceptualTriggerError("time_invalid", "impact times must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _state_path(package_root: Path | str) -> Path:
    root = Path(package_root).resolve()
    if root.is_symlink():
        raise ConceptualTriggerError("unsafe_package", "package root must not be a symbolic link")
    metadata = root / ".docops"
    if metadata.is_symlink():
        raise ConceptualTriggerError("unsafe_package", "package metadata must not be a symbolic link")
    metadata.mkdir(parents=True, exist_ok=True)
    return metadata / "conceptual-impact.json"


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": TRIGGER_SCHEMA_VERSION,
            "package_id": None,
            "processed_event_ids": [],
            "documents": {},
            "batches": [],
            "revocations": [],
            "cursor": {"last_event_at": None, "last_event_id": None},
        }
    if path.is_symlink() or not path.is_file():
        raise ConceptualTriggerError("unsafe_state", "impact state must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConceptualTriggerError("state_unreadable", "impact state is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ConceptualTriggerError("state_invalid", "impact state must be an object")
    value.setdefault("schema_version", TRIGGER_SCHEMA_VERSION)
    value.setdefault("processed_event_ids", [])
    value.setdefault("documents", {})
    value.setdefault("batches", [])
    value.setdefault("revocations", [])
    value.setdefault("cursor", {"last_event_at": None, "last_event_id": None})
    if not isinstance(value["documents"], dict) or not isinstance(value["batches"], list):
        raise ConceptualTriggerError("state_invalid", "impact state has an invalid shape")
    return value


def _load_events(value: Mapping[str, Any] | Iterable[Mapping[str, Any]] | Path | str) -> list[dict[str, Any]]:
    if isinstance(value, (Path, str)):
        try:
            raw = json.loads(Path(value).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConceptualTriggerError("events_unreadable", "impact events could not be read") from exc
    else:
        raw = value
    if isinstance(raw, Mapping):
        raw_events = [raw]
    elif isinstance(raw, Iterable) and not isinstance(raw, (str, bytes)):
        raw_events = list(raw)
    else:
        raise ConceptualTriggerError("events_invalid", "impact events must be an object or array")
    events: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, Mapping):
            raise ConceptualTriggerError("event_invalid", "each impact event must be an object")
        event_value = dict(event)
        event_id = event_value.get("event_id")
        occurred_at = event_value.get("occurred_at")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ConceptualTriggerError("event_invalid", "impact event_id is required")
        _parse_time(str(occurred_at))
        events.append(event_value)
    return events


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    value = event.get("payload")
    return value if isinstance(value, Mapping) else event


def _document_identity(payload: Mapping[str, Any]) -> str | None:
    for key in ("document_id", "path", "filename", "source"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().replace("\\", "/")
    return None


def _current_documents(state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for document_id, raw in state.get("documents", {}).items():
        if not isinstance(raw, Mapping):
            continue
        if raw.get("revoked") is True:
            continue
        revision = str(raw.get("revision") or "")
        base_revision = str(raw.get("base_revision") or "")
        impact = str(raw.get("impact") or "")
        if revision and revision != base_revision and impact in {"conceptual", "uncertain"}:
            documents[str(document_id)] = dict(raw)
    return documents


def _batch_key(documents: Mapping[str, Mapping[str, Any]]) -> str:
    return content_hash(
        [
            {
                "document_id": document_id,
                "revision": str(value.get("revision") or ""),
                "base_revision": str(value.get("base_revision") or ""),
                "impact": str(value.get("impact") or ""),
            }
            for document_id, value in sorted(documents.items())
        ]
    )


def _batch_budget_count(batches: list[Mapping[str, Any]], now: datetime) -> int:
    cutoff = now - timedelta(hours=24)
    count = 0
    for batch in batches:
        status = str(batch.get("status") or "")
        if status not in {"candidate_requested", "review_required"}:
            continue
        try:
            if _parse_time(str(batch.get("created_at"))) >= cutoff:
                count += 1
        except ConceptualTriggerError:
            continue
    return count


def _public_documents(documents: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": document_id,
            "revision": str(value.get("revision") or ""),
            "base_revision": str(value.get("base_revision") or ""),
            "impact": str(value.get("impact") or ""),
            "support_valid": value.get("support_valid", True),
        }
        for document_id, value in sorted(documents.items())
    ]


def assess_conceptual_impact(
    package_root: Path | str,
    events: Mapping[str, Any] | Iterable[Mapping[str, Any]] | Path | str,
    *,
    now: str | datetime | None = None,
    threshold: int = DEFAULT_THRESHOLD,
    budget: int = DEFAULT_MAX_BATCHES_PER_DAY,
    corpus_documents: int = DEFAULT_CORPUS_DOCUMENTS,
    causation_id: str | None = None,
) -> dict[str, Any]:
    """Apply a batch of impact observations and return the public trigger report.

    The cursor is document/revision based rather than event-count based. This
    makes a reindex with no document diff a no-op and lets a later observation
    of the base revision remove a previous change from the counter.
    """

    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
        raise ConceptualTriggerError("threshold_invalid", "threshold must be a positive integer")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ConceptualTriggerError("budget_invalid", "budget must be a non-negative integer")
    if isinstance(corpus_documents, bool) or not isinstance(corpus_documents, int) or corpus_documents < 1:
        raise ConceptualTriggerError("corpus_invalid", "corpus_documents must be a positive integer")

    current = _parse_time(now)
    path = _state_path(package_root)
    state = _load_state(path)
    event_values = _load_events(events)
    processed = set(str(item) for item in state.get("processed_event_ids", []) if str(item))
    package_id: str | None = state.get("package_id") if isinstance(state.get("package_id"), str) else None
    reverted: set[str] = set()
    factual: set[str] = set()
    uncertain: set[str] = set()
    revocations: list[dict[str, Any]] = list(state.get("revocations") or [])

    for event in event_values:
        event_id = str(event["event_id"])
        if event_id in processed:
            continue
        event_package = event.get("package_id")
        if isinstance(event_package, str) and event_package:
            if package_id is None:
                package_id = event_package
            elif package_id != event_package:
                raise ConceptualTriggerError("package_mismatch", "impact events target different packages")
        payload = _payload(event)
        document_id = _document_identity(payload)
        processed.add(event_id)
        if document_id is None:
            if payload.get("document_diff") is False or event.get("type") in {"reindex_completed", "reindexed"}:
                continue
            continue
        revision = str(payload.get("document_revision") or event.get("observed_revision") or "")
        base_revision = str(payload.get("base_revision") or "")
        impact = str(payload.get("impact") or "uncertain").casefold()
        if impact not in {"conceptual", "factual", "uncertain"}:
            impact = "uncertain"
        is_revoked = payload.get("revoked") is True or event.get("type") in {"source_revoked", "document_revoked"}
        if is_revoked:
            previous = state["documents"].get(document_id, {})
            previous_record = dict(previous) if isinstance(previous, Mapping) else {}
            state["documents"][document_id] = {
                **previous_record,
                "revision": revision or str(previous_record.get("revision") or ""),
                "base_revision": base_revision or str(previous.get("base_revision") or "")
                if isinstance(previous, Mapping)
                else base_revision,
                "impact": impact,
                "revoked": True,
                "support_valid": False,
                "last_event_id": event_id,
            }
            revocations.append(
                {
                    "document_id": document_id,
                    "event_id": event_id,
                    "support_valid": False,
                    "revoked_at": _iso(_parse_time(str(event["occurred_at"]))),
                }
            )
        else:
            record = {
                "revision": revision,
                "base_revision": base_revision,
                "impact": impact,
                "revoked": False,
                "support_valid": True,
                "last_event_id": event_id,
            }
            state["documents"][document_id] = record
            if revision == base_revision and revision:
                reverted.add(document_id)
            elif impact == "factual":
                factual.add(document_id)
            elif impact == "uncertain":
                uncertain.add(document_id)
        occurred = _parse_time(str(event["occurred_at"]))
        cursor = state.get("cursor") or {}
        previous_cursor = cursor.get("last_event_at")
        if not previous_cursor or _parse_time(str(previous_cursor)) <= occurred:
            state["cursor"] = {"last_event_at": _iso(occurred), "last_event_id": event_id}

    relevant = _current_documents(state)
    key = _batch_key(relevant) if relevant else None
    existing_keys = {str(batch.get("batch_key")) for batch in state["batches"] if isinstance(batch, Mapping)}
    batch: dict[str, Any] = {
        "status": "none",
        "batch_id": None,
        "batch_key": key,
        "causation_id": causation_id,
        "document_ids": sorted(relevant),
        "publication_allowed": False,
        "reason": "no_conceptual_impact_threshold",
    }
    threshold_met = len(relevant) >= threshold or (len(relevant) >= 3 and len(relevant) / corpus_documents >= 0.10)
    if key and threshold_met and key not in existing_keys:
        has_uncertain = any(str(item.get("impact")) == "uncertain" for item in relevant.values())
        created_at = _iso(current)
        if has_uncertain:
            status = "review_required"
            reason = "impact_uncertain_requires_review"
        elif any(str(item.get("impact")) == "conceptual" for item in relevant.values()):
            status = "candidate_requested"
            reason = "conceptual_impact_threshold_reached"
        else:
            status = "none"
            reason = "factual_only"
        if status != "none":
            batch = {
                "status": status,
                "batch_id": f"conceptual-batch-{uuid.uuid4().hex}",
                "batch_key": key,
                "causation_id": causation_id,
                "document_ids": sorted(relevant),
                "publication_allowed": False,
                "reason": reason,
                "created_at": created_at,
            }
            if _batch_budget_count(state["batches"], current) >= budget:
                batch["status"] = "backlog"
                batch["reason"] = "enrichment_budget_exhausted"
                state.setdefault("backlog", []).append(batch)
            state["batches"].append(batch)

    state["package_id"] = package_id
    state["processed_event_ids"] = sorted(processed)
    state["revocations"] = revocations[-1000:]
    state["updated_at"] = _iso(current)
    state["schema_version"] = TRIGGER_SCHEMA_VERSION
    write_json_atomic(path, state)

    backlog = [item for item in state.get("batches", []) if item.get("status") == "backlog"]
    report = {
        "schema_version": TRIGGER_SCHEMA_VERSION,
        "ok": True,
        "package_id": package_id or "unknown",
        "cursor": dict(state["cursor"]),
        "relevant_count": len(relevant),
        "affected_ratio": round(len(relevant) / corpus_documents, 6),
        "documents": _public_documents(relevant),
        "reverted_documents": sorted(reverted),
        "factual_documents": sorted(factual),
        "uncertain_documents": sorted(uncertain),
        "batch": batch,
        "backlog_count": len(backlog),
        "backlog": [
            {
                "batch_id": item.get("batch_id"),
                "batch_key": item.get("batch_key"),
                "document_ids": item.get("document_ids", []),
                "reason": item.get("reason"),
            }
            for item in backlog
        ],
        "revocations": list(state["revocations"]),
    }
    contract = validate_artifact("conceptual-impact", report)
    if not contract.ok:
        raise ConceptualTriggerError("impact_contract_invalid", "impact report violates its public contract")
    return report


__all__ = ["ConceptualTriggerError", "assess_conceptual_impact"]
