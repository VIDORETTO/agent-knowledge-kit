"""Redacted usage feedback, investigation signals, and Golden candidates."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contracts import validate_artifact
from .observability import redact_report
from .storage import write_json_atomic

SCHEMA_VERSION = 1
INVESTIGATION_THRESHOLD = 3
REGRESSION_THRESHOLD = 0.03
ABSTENTION_THRESHOLD = 0.10
ABSTENTION_MIN_DENOMINATOR = 100
FEEDBACK_RATE_LIMIT = 20
FEEDBACK_RATE_WINDOW = timedelta(minutes=1)
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_COMPARISON_FIELDS = (
    "dataset_id",
    "corpus_revision",
    "index_revision",
    "golden_revision",
    "harness_revision",
    "configuration_hash",
)


class FeedbackError(ValueError):
    """Raised when feedback cannot be safely normalized or reported."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
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
            raise FeedbackError("time_invalid", "feedback time must be RFC3339") from exc
    if parsed.tzinfo is None:
        raise FeedbackError("time_invalid", "feedback time must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    else:
        payload = _canonical(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(value: Mapping[str, Any] | Path | str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        payload = dict(value)
    else:
        try:
            payload = json.loads(Path(value).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FeedbackError("feedback_unreadable", "feedback input is not readable JSON") from exc
    if not isinstance(payload, dict):
        raise FeedbackError("feedback_invalid", "feedback input must be a JSON object")
    return payload


def _safe_id(value: Any, *, field: str) -> str:
    result = str(value or "").strip()
    if not _SAFE_ID.fullmatch(result):
        raise FeedbackError("feedback_id_invalid", f"{field} must be a bounded identifier")
    return result


def _safe_string(value: Any, *, field: str, default: str | None = None) -> str | None:
    if value is None:
        return default
    result = str(value).strip()
    if not result:
        return default
    if len(result) > 512:
        raise FeedbackError("feedback_field_too_large", f"{field} is too large")
    return result


def _nonnegative_number(value: Any, *, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise FeedbackError("feedback_metric_invalid", f"{field} must be a non-negative number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise FeedbackError("feedback_metric_invalid", f"{field} must be a non-negative number") from exc
    if not math.isfinite(result) or result < 0:
        raise FeedbackError("feedback_metric_invalid", f"{field} must be a non-negative number")
    return result


def _nonnegative_integer(value: Any, *, field: str, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise FeedbackError("feedback_metric_invalid", f"{field} must be a non-negative integer")
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise FeedbackError("feedback_metric_invalid", f"{field} must be a non-negative integer") from exc
    if result < 0 or str(result) != str(value).strip() and not isinstance(value, int):
        raise FeedbackError("feedback_metric_invalid", f"{field} must be a non-negative integer")
    return result


def _generation(value: Any) -> dict[str, str | None]:
    source = value if isinstance(value, Mapping) else {}
    return {
        key: _safe_string(source.get(key), field=f"generation.{key}")
        for key in (
            "release_id",
            "composition_hash",
            "corpus_revision",
            "index_revision",
            "golden_revision",
            "harness_revision",
            "configuration_hash",
        )
    }


def _metric_side(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FeedbackError("comparison_invalid", "comparison sides must be objects")
    result: dict[str, Any] = {
        "value": _nonnegative_number(value.get("value"), field="comparison.value"),
        "denominator": _nonnegative_integer(value.get("denominator"), field="comparison.denominator"),
    }
    for field in ("dataset_id", "corpus_revision", "index_revision", "golden_revision", "harness_revision"):
        result[field] = _safe_string(value.get(field), field=f"comparison.{field}")
    result["configuration_hash"] = _safe_string(value.get("configuration_hash"), field="comparison.configuration_hash")
    return result


def _comparison(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise FeedbackError("comparison_invalid", "comparison must be an object")
    metric = _safe_string(value.get("metric"), field="comparison.metric")
    baseline = _metric_side(value.get("baseline"))
    current = _metric_side(value.get("current"))
    if metric is None:
        raise FeedbackError("comparison_invalid", "comparison.metric is required")
    return {"metric": metric, "baseline": baseline, "current": current}


def _normalize_authentication(
    value: Any,
    *,
    reporter: str,
    reporter_was_supplied: bool,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("authenticated") is not True:
        raise FeedbackError(
            "feedback_authentication_required",
            "feedback requires an authenticated origin attestation",
        )
    source = _safe_string(value.get("source"), field="authentication.source")
    subject = _safe_string(value.get("subject"), field="authentication.subject")
    proof = _safe_string(value.get("proof") or value.get("signature"), field="authentication.proof")
    if source is None or subject is None or proof is None:
        raise FeedbackError(
            "feedback_authentication_invalid",
            "authenticated feedback requires source, subject and proof",
        )
    if reporter_was_supplied and subject != reporter:
        raise FeedbackError(
            "feedback_authentication_subject_mismatch",
            "feedback authentication subject must match reporter_id",
        )
    return {
        "authenticated": True,
        "source": source,
        "subject_hash": _sha256(subject),
        "proof_hash": _sha256(proof),
    }


def _normalize_feedback(value: Mapping[str, Any] | Path | str, *, now: str | datetime | None) -> dict[str, Any]:
    raw = _read_json(value)
    feedback_id = _safe_id(raw.get("feedback_id"), field="feedback_id")
    package_id = _safe_string(raw.get("package_id"), field="package_id")
    if package_id is None:
        raise FeedbackError("feedback_invalid", "package_id is required")
    kind = _safe_string(raw.get("kind"), field="kind")
    if kind not in {"wrong_answer", "retrieval_miss", "unhelpful", "abstention", "latency", "cost"}:
        raise FeedbackError("feedback_kind_invalid", "unsupported feedback kind")
    occurred_at = _parse_time(raw.get("occurred_at") or now)
    question = raw.get("question", raw.get("query", raw.get("private_question")))
    question_text = "" if question is None else str(question).strip()
    if len(question_text) > 8000:
        raise FeedbackError("feedback_field_too_large", "private question is too large")
    question_hash = _safe_string(raw.get("question_hash"), field="question_hash")
    if question_hash is None:
        question_hash = _sha256(question_text or "<missing-question>")
    event_id = _safe_id(raw.get("event_id"), field="event_id")
    reporter_was_supplied = any(key in raw for key in ("reporter_id", "actor_id", "user_id"))
    reporter = _safe_string(
        raw.get("reporter_id", raw.get("actor_id", raw.get("user_id"))),
        field="reporter_id",
        default="anonymous",
    )
    session = _safe_string(raw.get("session_id"), field="session_id", default="anonymous")
    authentication = _normalize_authentication(
        raw.get("authentication"),
        reporter=reporter or "anonymous",
        reporter_was_supplied=reporter_was_supplied,
    )
    generation = _generation(raw.get("generation"))
    occurrence_hash = _sha256(
        {
            "package_id": package_id,
            "generation": generation,
            "kind": kind,
            "question_hash": question_hash,
            "independence": session or reporter or "anonymous",
        }
    )
    usage_raw = raw.get("usage") if isinstance(raw.get("usage"), Mapping) else {}
    usage = {
        "latency_ms": _nonnegative_number(usage_raw.get("latency_ms"), field="usage.latency_ms"),
        "cost_units": _nonnegative_number(usage_raw.get("cost_units"), field="usage.cost_units"),
        "denominator": max(1, _nonnegative_integer(usage_raw.get("denominator"), field="usage.denominator", default=1)),
    }
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "feedback_id": feedback_id,
        "event_id": event_id,
        "package_id": package_id,
        "generation": generation,
        "kind": kind,
        "question": "<redacted-query>",
        "question_hash": question_hash,
        "privacy": "redacted",
        "source": {
            "channel": _safe_string(raw.get("channel"), field="channel", default="operator"),
            "reporter_hash": _sha256(reporter or "anonymous"),
            "session_hash": _sha256(session or "anonymous"),
        },
        "authentication": authentication,
        "usage": usage,
        "comparison": _comparison(raw.get("comparison")),
        "occurred_at": _iso(occurred_at),
        "state": "received",
        "occurrence_hash": occurrence_hash,
    }
    record["feedback_hash"] = _sha256(record)
    contract = validate_artifact("feedback", record)
    if not contract.ok:
        raise FeedbackError(
            "feedback_contract_invalid", "normalized feedback violates its contract", details=contract.errors
        )
    return record


def _feedback_root(package_root: Path | str) -> Path:
    root = Path(package_root).resolve()
    if not root.is_dir():
        raise FeedbackError("package_unavailable", "package directory does not exist")
    return root / ".docops" / "feedback"


def _submission_path(package_root: Path | str, feedback_id: str) -> Path:
    return _feedback_root(package_root) / "submissions" / f"{feedback_id}.json"


def _read_record(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FeedbackError("feedback_record_invalid", "stored feedback is unreadable") from exc
    if not isinstance(payload, dict):
        raise FeedbackError("feedback_record_invalid", "stored feedback must be an object")
    result = validate_artifact("feedback", payload)
    if not result.ok:
        raise FeedbackError("feedback_record_invalid", "stored feedback violates its contract", details=result.errors)
    return payload


def _load_records(package_root: Path | str) -> list[dict[str, Any]]:
    directory = _feedback_root(package_root) / "submissions"
    if not directory.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.is_symlink() or not path.is_file():
            continue
        records.append(_read_record(path))
    return records


def _public_submission(
    record: Mapping[str, Any], *, code: str, queued_job: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "code": code,
        "feedback_id": record["feedback_id"],
        "occurrence_id": str(record["occurrence_hash"])[:16],
        "question": "<redacted-query>",
        "question_hash": record["question_hash"],
        "state": record["state"],
        "publication_allowed": False,
        "active_knowledge_changed": False,
        "expected_response_changed": False,
    }
    if queued_job is not None:
        payload["job"] = redact_report(dict(queued_job))
    return payload


def submit_feedback(
    package_root: Path | str,
    feedback: Mapping[str, Any] | Path | str,
    *,
    now: str | datetime | None = None,
    queue_path: Path | str | None = None,
) -> dict[str, Any]:
    """Persist one redacted usage signal and optionally enqueue its report."""

    record = _normalize_feedback(feedback, now=now)
    target = _submission_path(package_root, record["feedback_id"])
    if target.exists():
        existing = _read_record(target)
        if existing["feedback_hash"] != record["feedback_hash"]:
            raise FeedbackError("feedback_id_conflict", "feedback_id already exists with different content")
        return _public_submission(existing, code="feedback_duplicate")
    records = _load_records(package_root)
    replay = next((item for item in records if item.get("event_id") == record["event_id"]), None)
    if replay is not None:
        raise FeedbackError(
            "feedback_replay",
            "feedback event_id has already been submitted",
            details={"event_id": record["event_id"]},
        )
    subject_hash = record["authentication"]["subject_hash"]
    occurred_at = _parse_time(str(record["occurred_at"]))
    recent_count = sum(
        1
        for item in records
        if isinstance(item.get("authentication"), Mapping)
        and item["authentication"].get("subject_hash") == subject_hash
        and occurred_at - FEEDBACK_RATE_WINDOW <= _parse_time(str(item["occurred_at"])) <= occurred_at
    )
    if recent_count >= FEEDBACK_RATE_LIMIT:
        raise FeedbackError(
            "feedback_rate_limited",
            "feedback origin exceeded the submission rate limit",
            details={"window_seconds": int(FEEDBACK_RATE_WINDOW.total_seconds()), "limit": FEEDBACK_RATE_LIMIT},
        )
    write_json_atomic(target, record)
    queued_job: Mapping[str, Any] | None = None
    if queue_path is not None:
        from .coordination import submit_event

        event = {
            "schema_version": 1,
            "event_id": f"feedback-report-{record['feedback_id']}",
            "type": "feedback_report",
            "package_id": record["package_id"],
            "observed_revision": str(record["generation"].get("release_id") or record["feedback_hash"]),
            "occurred_at": record["occurred_at"],
            "origin": "usage_feedback",
            "causation_id": record["feedback_id"],
            "payload": {
                "policy_revision": "feedback-v1",
                "work": {"kind": "feedback_report", "output_dir": str(Path(package_root).resolve())},
            },
        }
        queued = submit_event(queue_path, event, now=now)
        queued_job = queued.get("job") if isinstance(queued, Mapping) else None
    return _public_submission(record, code="feedback_accepted", queued_job=queued_job)


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "total": None, "mean": None, "p50": None, "p95": None}
    ordered = sorted(values)

    def percentile(ratio: float) -> float:
        index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * ratio) - 1))
        return round(ordered[index], 6)

    total = sum(ordered)
    return {
        "count": len(ordered),
        "total": round(total, 6),
        "mean": round(total / len(ordered), 6),
        "p50": percentile(0.50),
        "p95": percentile(0.95),
    }


def _comparison_report(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    comparisons = [item.get("comparison") for item in records if isinstance(item.get("comparison"), Mapping)]
    result: dict[str, Any] = {
        "status": "not_provided",
        "controlled_regression": None,
        "metric": None,
        "delta": None,
        "reason": "no comparable metric supplied",
        "denominators": {"samples": len(comparisons), "comparable": 0},
    }
    if not comparisons:
        return result
    statuses: list[dict[str, Any]] = []
    for comparison in comparisons:
        baseline = comparison.get("baseline")
        current = comparison.get("current")
        metric = comparison.get("metric")
        if not isinstance(baseline, Mapping) or not isinstance(current, Mapping):
            statuses.append({"status": "not_comparable", "reason": "metric sides are incomplete", "metric": metric})
            continue
        mismatch = next(
            (
                field
                for field in _COMPARISON_FIELDS
                if baseline.get(field) is None
                or current.get(field) is None
                or baseline.get(field) != current.get(field)
            ),
            None,
        )
        if mismatch is not None:
            statuses.append(
                {
                    "status": "not_comparable",
                    "reason": f"comparison field differs: {mismatch}",
                    "metric": metric,
                }
            )
            continue
        baseline_value = baseline.get("value")
        current_value = current.get("value")
        baseline_denominator = int(baseline.get("denominator") or 0)
        current_denominator = int(current.get("denominator") or 0)
        if baseline_value is None or current_value is None or min(baseline_denominator, current_denominator) <= 0:
            statuses.append(
                {
                    "status": "insufficient_denominator",
                    "reason": "metric value or denominator is unavailable",
                    "metric": metric,
                }
            )
            continue
        delta = float(current_value) - float(baseline_value)
        threshold = ABSTENTION_THRESHOLD if str(metric).casefold().startswith("abstention") else REGRESSION_THRESHOLD
        enough = (
            current_denominator >= ABSTENTION_MIN_DENOMINATOR
            if str(metric).casefold().startswith("abstention")
            else True
        )
        statuses.append(
            {
                "status": "comparable" if enough else "insufficient_denominator",
                "reason": "same dataset and generation fingerprints" if enough else "denominator below policy minimum",
                "metric": metric,
                "delta": round(delta, 6),
                "controlled_regression": bool(enough and delta < -threshold),
                "baseline_denominator": baseline_denominator,
                "current_denominator": current_denominator,
            }
        )
    non_comparable = next((item for item in statuses if item["status"] == "not_comparable"), None)
    if non_comparable is not None:
        result.update(
            {
                "status": "not_comparable",
                "controlled_regression": False,
                "metric": non_comparable.get("metric"),
                "reason": non_comparable["reason"],
                "denominators": {"samples": len(comparisons), "comparable": 0},
            }
        )
        return result
    insufficient = next((item for item in statuses if item["status"] == "insufficient_denominator"), None)
    comparable = [item for item in statuses if item["status"] == "comparable"]
    if insufficient is not None and not comparable:
        result.update(
            {
                "status": "insufficient_denominator",
                "controlled_regression": False,
                "metric": insufficient.get("metric"),
                "reason": insufficient["reason"],
                "denominators": {"samples": len(comparisons), "comparable": 0},
            }
        )
        return result
    signal = next(
        (item for item in comparable if item.get("controlled_regression")), comparable[0] if comparable else {}
    )
    result.update(
        {
            "status": "comparable",
            "controlled_regression": bool(signal.get("controlled_regression", False)),
            "metric": signal.get("metric"),
            "delta": signal.get("delta"),
            "reason": signal.get("reason", "comparable metric"),
            "denominators": {"samples": len(comparisons), "comparable": len(comparable)},
        }
    )
    return result


def _investigation_for_group(
    package_root: Path | str,
    *,
    package_id: str,
    kind: str,
    occurrences: list[Mapping[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    occurrence_ids = [str(item["occurrence_hash"])[:16] for item in occurrences]
    seed = {
        "package_id": package_id,
        "kind": kind,
        "occurrences": [item["occurrence_hash"] for item in occurrences],
    }
    investigation_id = f"investigation-{_sha256(seed)[:24]}"
    candidate_id = f"golden-feedback-{_sha256(seed)[:24]}"
    golden_candidate = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "reviewed": False,
        "publication_allowed": False,
        "origin": {
            "kind": "usage_feedback",
            "investigation_id": investigation_id,
            "occurrence_ids": occurrence_ids,
        },
        "cases": [
            {
                "query": "<redacted-query>",
                "query_hashes": sorted({str(item["question_hash"]) for item in occurrences}),
                "expected_filepath": "<review-required>",
                "kind": "factual",
                "reviewed": False,
                "review_note": "Feedback is an operational signal; verify the question and expected source independently.",
            }
        ],
    }
    investigation = {
        "schema_version": SCHEMA_VERSION,
        "investigation_id": investigation_id,
        "package_id": package_id,
        "kind": kind,
        "status": "candidate_requested",
        "reviewed": False,
        "occurrence_ids": occurrence_ids,
        "golden_candidate": golden_candidate,
        "publication_allowed": False,
        "created_at": _iso(now),
    }
    contract = validate_artifact("investigation", investigation)
    if not contract.ok:
        raise FeedbackError(
            "investigation_contract_invalid", "investigation violates its contract", details=contract.errors
        )
    root = _feedback_root(package_root)
    write_json_atomic(root / "golden-candidates" / f"{candidate_id}.json", golden_candidate)
    write_json_atomic(root / "investigations" / f"{investigation_id}.json", investigation)
    return investigation


def build_feedback_report(
    package_root: Path | str,
    *,
    now: str | datetime | None = None,
    window_days: int = 7,
) -> dict[str, Any]:
    """Aggregate redacted signals and create review-only investigations."""

    if isinstance(window_days, bool) or not isinstance(window_days, int) or not 1 <= window_days <= 365:
        raise FeedbackError("window_invalid", "window_days must be an integer from 1 through 365")
    current = _parse_time(now)
    start = current - timedelta(days=window_days)
    all_records = _load_records(package_root)
    scoped = [record for record in all_records if start <= _parse_time(str(record["occurred_at"])) <= current]
    package_ids = {str(record["package_id"]) for record in scoped}
    if len(package_ids) > 1:
        raise FeedbackError("feedback_package_mismatch", "feedback records belong to multiple packages")
    package_id = next(iter(package_ids), "package-unknown")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in scoped:
        groups[str(record["occurrence_hash"])].append(record)
    occurrences: list[dict[str, Any]] = []
    for occurrence_hash, records in sorted(groups.items()):
        ordered = sorted(records, key=lambda item: str(item["occurred_at"]))
        first = ordered[0]
        occurrences.append(
            {
                "occurrence_id": occurrence_hash[:16],
                "occurrence_hash": occurrence_hash,
                "kind": first["kind"],
                "question": "<redacted-query>",
                "question_hash": first["question_hash"],
                "feedback_count": len(records),
                "first_seen": ordered[0]["occurred_at"],
                "last_seen": ordered[-1]["occurred_at"],
                "generation": redact_report(first["generation"]),
            }
        )
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in occurrences:
        by_kind[str(occurrence["kind"])].append(occurrence)
    investigations = [
        _investigation_for_group(
            package_root,
            package_id=package_id,
            kind=kind,
            occurrences=sorted(items, key=lambda item: str(item["first_seen"])),
            now=current,
        )
        for kind, items in sorted(by_kind.items())
        if len(items) >= INVESTIGATION_THRESHOLD
    ]
    latency_values = [
        float(record["usage"]["latency_ms"]) for record in scoped if record["usage"].get("latency_ms") is not None
    ]
    cost_values = [
        float(record["usage"]["cost_units"]) for record in scoped if record["usage"].get("cost_units") is not None
    ]
    comparison = _comparison_report(scoped)
    report_seed = {
        "package_id": package_id,
        "window": [_iso(start), _iso(current), window_days],
        "feedback_hashes": sorted(str(record["feedback_hash"]) for record in scoped),
    }
    report_id = f"feedback-report-{_sha256(report_seed)[:24]}"
    report = {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "report_id": report_id,
        "package_id": package_id,
        "window": {"start": _iso(start), "end": _iso(current), "days": window_days},
        "counts": {
            "submissions": len(scoped),
            "unique_occurrences": len(occurrences),
            "duplicate_submissions": sum(max(0, len(items) - 1) for items in groups.values()),
            "investigations": len(investigations),
        },
        "usage": {
            "latency_ms": _stats(latency_values),
            "cost_units": _stats(cost_values),
            "denominators": {
                "submissions": len(scoped),
                "unique_occurrences": len(occurrences),
                "latency_samples": len(latency_values),
                "cost_samples": len(cost_values),
                "comparison_samples": comparison["denominators"]["samples"],
                "comparable_metric_samples": comparison["denominators"]["comparable"],
            },
        },
        "comparison": comparison,
        "occurrences": occurrences,
        "investigations": investigations,
        "publication_allowed": False,
        "golden_changed": False,
        "expected_response_changed": False,
        "active_knowledge_changed": False,
        "reviewed": False,
    }
    contract = validate_artifact("feedback-report", report)
    if not contract.ok:
        raise FeedbackError("feedback_report_invalid", "feedback report violates its contract", details=contract.errors)
    write_json_atomic(_feedback_root(package_root) / "reports" / f"{report_id}.json", report)
    return redact_report(report)


def report_feedback(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility alias for callers that name the report operation directly."""

    return build_feedback_report(*args, **kwargs)
