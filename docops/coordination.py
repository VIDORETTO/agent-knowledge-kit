"""Durable local event coordination with idempotency and debounce."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .authorization import AuthorizationError, read_rag_authorization
from .contracts import validate_artifact
from .storage import write_json_atomic

SCHEMA_VERSION = 1
DEBOUNCE_SECONDS = 60
MAX_DEBOUNCE_SECONDS = 5 * 60
DEFAULT_LEASE_SECONDS = 120
MAX_ATTEMPTS = 5
RETRY_DELAYS_SECONDS = (60, 300, 900, 3600)


class CoordinationError(ValueError):
    """Raised when an event cannot be safely accepted by the queue."""

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
        raw = value.strip()
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise CoordinationError("time_invalid", f"invalid RFC3339 time: {value!r}") from exc
    if parsed.tzinfo is None:
        raise CoordinationError("time_invalid", "queue times must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _queue_path(path: Path | str) -> Path:
    value = Path(path)
    if value.is_symlink():
        raise CoordinationError("unsafe_queue_path", "queue database must not be a symbolic link")
    if value.exists() and not value.is_file():
        raise CoordinationError("queue_not_file", "queue path must be a file")
    if value.parent.is_symlink():
        raise CoordinationError("unsafe_queue_path", "queue parent must not be a symbolic link")
    value.parent.mkdir(parents=True, exist_ok=True)
    return value


def _connect(path: Path | str) -> sqlite3.Connection:
    queue = _queue_path(path)
    try:
        connection = sqlite3.connect(str(queue), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                payload_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                job_key TEXT
            );
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                job_key TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                package_id TEXT NOT NULL,
                target_revision TEXT NOT NULL,
                policy_revision TEXT,
                state TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0,
                due_at TEXT NOT NULL,
                first_event_at TEXT NOT NULL,
                last_event_at TEXT NOT NULL,
                event_count INTEGER NOT NULL DEFAULT 0,
                completed_files_json TEXT NOT NULL DEFAULT '[]',
                deferred_files_json TEXT NOT NULL DEFAULT '[]',
                lease_until TEXT,
                lease_token TEXT,
                lease_heartbeat TEXT,
                result_ref TEXT,
                error_code TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                worker_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS jobs_due_idx ON jobs(state, due_at);
            """
        )
        for column, definition in (
            ("completed_files_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("deferred_files_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("payload_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("worker_id", "TEXT"),
            ("lease_token", "TEXT"),
            ("lease_heartbeat", "TEXT"),
        ):
            try:
                connection.execute(f"SELECT {column} FROM jobs LIMIT 1")
            except sqlite3.OperationalError:
                connection.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")
        try:
            connection.execute("SELECT job_key FROM events LIMIT 1")
        except sqlite3.OperationalError:
            connection.execute("ALTER TABLE events ADD COLUMN job_key TEXT")
        return connection
    except sqlite3.Error as exc:
        raise CoordinationError("queue_unavailable", f"could not open durable queue: {exc}") from exc


def _read_event(value: Mapping[str, Any] | Path | str) -> dict[str, Any]:
    if isinstance(value, (Path, str)):
        try:
            raw = json.loads(Path(value).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CoordinationError("event_unreadable", f"could not read event: {exc}") from exc
    else:
        raw = dict(value)
    if not isinstance(raw, dict):
        raise CoordinationError("event_invalid", "event must be a JSON object")
    result = dict(raw)
    contract = validate_artifact("event", result)
    if not contract.ok:
        raise CoordinationError(
            "event_invalid", "event violates its public contract", details={"errors": contract.errors}
        )
    _parse_time(str(result["occurred_at"]))
    return result


def _event_hash(event: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(event), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _job_key(event: Mapping[str, Any]) -> str:
    payload = event.get("payload")
    policy_revision = payload.get("policy_revision") if isinstance(payload, Mapping) else None
    key = "\0".join(
        (
            str(event["package_id"]),
            str(event["type"]),
            str(event["observed_revision"]),
            str(policy_revision or ""),
        )
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _job_from_row(row: sqlite3.Row, *, now: datetime | None = None) -> dict[str, Any]:
    completed_files = json.loads(row["completed_files_json"] or "[]")
    deferred_files = json.loads(row["deferred_files_json"] or "[]")
    job = {
        "schema_version": SCHEMA_VERSION,
        "job_id": row["job_id"],
        "job_key": row["job_key"],
        "type": row["type"],
        "package_id": row["package_id"],
        "target_revision": row["target_revision"],
        "state": row["state"],
        "attempt": int(row["attempt"]),
        "due_at": row["due_at"],
        "first_event_at": row["first_event_at"],
        "last_event_at": row["last_event_at"],
        "event_count": int(row["event_count"]),
        "completed_files": completed_files,
        "deferred_files": deferred_files,
        "lease_until": row["lease_until"],
        "lease_token": row["lease_token"],
        "lease_heartbeat": row["lease_heartbeat"],
        "result_ref": row["result_ref"],
        "error_code": row["error_code"],
        "policy_revision": row["policy_revision"],
    }
    contract = validate_artifact("job", job)
    if not contract.ok:
        raise CoordinationError(
            "queue_corrupt", "durable queue contains an invalid job", details={"errors": contract.errors}
        )
    if now is not None:
        has_file_projection = bool(completed_files or deferred_files)
        job["ready"] = (
            job["state"] == "pending"
            and _parse_time(job["due_at"]) <= now
            and (not has_file_projection or bool(completed_files))
        )
    return job


def _due_at(first_event: datetime, last_event: datetime) -> datetime:
    return min(
        last_event + timedelta(seconds=DEBOUNCE_SECONDS),
        first_event + timedelta(seconds=MAX_DEBOUNCE_SECONDS),
    )


def _file_projection(payload: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    raw_files = payload.get("files")
    completed: set[str] = set()
    deferred: set[str] = set()
    if isinstance(raw_files, list):
        for item in raw_files:
            if not isinstance(item, Mapping):
                continue
            path = item.get("path") or item.get("filename")
            if not isinstance(path, str) or not path.strip():
                continue
            normalized = path.strip().replace("\\", "/")
            status = str(item.get("status") or "").casefold()
            stable = item.get("stable") is True or status in {"complete", "completed", "stable", "finished"}
            (completed if stable else deferred).add(normalized)
    for key, target in (("completed_files", completed), ("stable_files", completed)):
        values = payload.get(key)
        if isinstance(values, list):
            target.update(str(value).strip().replace("\\", "/") for value in values if str(value).strip())
    for key in ("deferred_files", "unstable_files"):
        values = payload.get(key)
        if isinstance(values, list):
            deferred.update(str(value).strip().replace("\\", "/") for value in values if str(value).strip())
    deferred -= completed
    return sorted(completed), sorted(deferred)


def _pending_job(connection: sqlite3.Connection, base_job_key: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM jobs
         WHERE (job_key = ? OR job_key LIKE ?)
           AND state = 'pending'
      ORDER BY created_at DESC, job_id DESC
         LIMIT 1
        """,
        (base_job_key, f"{base_job_key}:%"),
    ).fetchone()


def _job_request(row: sqlite3.Row) -> dict[str, Any]:
    try:
        value = json.loads(row["payload_json"] or "{}")
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CoordinationError("queue_corrupt", "durable queue contains invalid job payload") from exc
    if not isinstance(value, dict):
        raise CoordinationError("queue_corrupt", "durable job payload must be an object")
    return value


def submit_event(
    queue_path: Path | str,
    event: Mapping[str, Any] | Path | str,
    *,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Persist an event and coalesce it into one durable job."""

    payload = _read_event(event)
    current = _parse_time(now)
    occurred = _parse_time(str(payload["occurred_at"]))
    event_hash = _event_hash(payload)
    base_job_key = _job_key(payload)
    connection = _connect(queue_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing_event = connection.execute(
            "SELECT payload_hash, job_key FROM events WHERE event_id = ?",
            (payload["event_id"],),
        ).fetchone()
        if existing_event is not None:
            if existing_event["payload_hash"] != event_hash:
                raise CoordinationError(
                    "event_id_conflict",
                    "event_id was already persisted with a different payload",
                    details={"event_id": payload["event_id"]},
                )
            row = (
                connection.execute("SELECT * FROM jobs WHERE job_key = ?", (existing_event["job_key"],)).fetchone()
                if existing_event["job_key"]
                else connection.execute("SELECT * FROM jobs WHERE job_key = ?", (base_job_key,)).fetchone()
            )
            connection.commit()
            return {
                "schema_version": SCHEMA_VERSION,
                "ok": True,
                "code": "event_duplicate",
                "duplicate": True,
                "event_id": payload["event_id"],
                "job": _job_from_row(row) if row is not None else None,
            }

        row = connection.execute("SELECT * FROM jobs WHERE job_key = ?", (base_job_key,)).fetchone()
        pending = _pending_job(connection, base_job_key)
        target_row = pending
        target_job_key = str(pending["job_key"]) if pending is not None else base_job_key
        if pending is None and row is not None:
            target_job_key = f"{base_job_key}:{event_hash[:16]}"
        if target_job_key == base_job_key and row is not None:
            target_row = row
        policy_payload = payload.get("payload")
        policy_revision = (
            str(policy_payload.get("policy_revision"))
            if isinstance(policy_payload, Mapping) and policy_payload.get("policy_revision") is not None
            else None
        )
        completed_files, deferred_files = _file_projection(
            policy_payload if isinstance(policy_payload, Mapping) else {}
        )
        event_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        connection.execute(
            """
            INSERT INTO events(event_id, payload_hash, payload_json, occurred_at, received_at, job_key)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload["event_id"], event_hash, event_json, _iso(occurred), _iso(current), target_job_key),
        )
        if target_row is None:
            first = occurred
            last = occurred
            due = _due_at(first, last)
            job_id = f"job-{uuid.uuid4().hex}"
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id, job_key, type, package_id, target_revision, policy_revision,
                    state, attempt, due_at, first_event_at, last_event_at, event_count,
                    completed_files_json, deferred_files_json,
                    lease_until, result_ref, error_code, payload_json, worker_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, 1, ?, ?, NULL, NULL, NULL, ?, NULL, ?, ?)
                """,
                (
                    job_id,
                    target_job_key,
                    payload["type"],
                    payload["package_id"],
                    payload["observed_revision"],
                    policy_revision,
                    _iso(due),
                    _iso(first),
                    _iso(last),
                    json.dumps(completed_files, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(deferred_files, ensure_ascii=False, separators=(",", ":")),
                    event_json,
                    _iso(current),
                    _iso(current),
                ),
            )
            code = "event_accepted"
        else:
            first = _parse_time(target_row["first_event_at"])
            last = max(_parse_time(target_row["last_event_at"]), occurred)
            due = _due_at(first, last)
            prior_completed = set(json.loads(target_row["completed_files_json"] or "[]"))
            prior_deferred = set(json.loads(target_row["deferred_files_json"] or "[]"))
            prior_completed.update(completed_files)
            prior_deferred.update(deferred_files)
            prior_deferred -= prior_completed
            connection.execute(
                """
               UPDATE jobs
                   SET last_event_at = ?, due_at = ?, event_count = event_count + 1,
                        completed_files_json = ?, deferred_files_json = ?, payload_json = ?, updated_at = ?
                  WHERE job_key = ? AND state = 'pending'
                """,
                (
                    _iso(last),
                    _iso(due),
                    json.dumps(sorted(prior_completed), ensure_ascii=False, separators=(",", ":")),
                    json.dumps(sorted(prior_deferred), ensure_ascii=False, separators=(",", ":")),
                    event_json,
                    _iso(current),
                    target_job_key,
                ),
            )
            code = "event_coalesced"
        row = connection.execute("SELECT * FROM jobs WHERE job_key = ?", (target_job_key,)).fetchone()
        connection.commit()
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "code": code,
            "duplicate": False,
            "event_id": payload["event_id"],
            "job": _job_from_row(row),
        }
    except CoordinationError:
        connection.rollback()
        raise
    except sqlite3.Error as exc:
        connection.rollback()
        raise CoordinationError("queue_write_failed", f"could not persist event: {exc}") from exc
    finally:
        connection.close()


def list_jobs(
    queue_path: Path | str,
    *,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Return the public job projection without exposing SQLite internals."""

    current = _parse_time(now)
    connection = _connect(queue_path)
    try:
        rows = connection.execute("SELECT * FROM jobs ORDER BY due_at, created_at, job_id").fetchall()
        jobs = [_job_from_row(row, now=current) for row in rows]
    finally:
        connection.close()
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "now": _iso(current),
        "jobs": jobs,
        "ready_count": sum(1 for job in jobs if job.get("ready")),
    }


def _job_receipt_path(output_dir: Path, job_id: str) -> Path:
    return output_dir / ".docops" / "job-receipts" / f"{job_id}.json"


def _work_hash(work: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(work), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _claim_job(
    queue_path: Path | str,
    *,
    now: datetime,
    worker_id: str,
    lease_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    connection = _connect(queue_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            UPDATE jobs
               SET state = 'blocked',
                   lease_until = NULL,
                   worker_id = NULL,
                   lease_token = NULL,
                   error_code = COALESCE(error_code, 'lease_expired_after_attempt_limit'),
                   updated_at = ?
             WHERE state = 'running'
               AND lease_until IS NOT NULL
               AND lease_until <= ?
               AND attempt >= ?
            """,
            (_iso(now), _iso(now), MAX_ATTEMPTS),
        )
        candidates = connection.execute(
            """
            SELECT * FROM jobs
             WHERE state = 'pending' AND due_at <= ?
          ORDER BY due_at, created_at, job_id
            """,
            (_iso(now),),
        ).fetchall()
        row = next(
            (
                candidate
                for candidate in candidates
                if int(candidate["attempt"]) < MAX_ATTEMPTS and _job_from_row(candidate, now=now).get("ready") is True
            ),
            None,
        )
        if row is None:
            row = connection.execute(
                """
                SELECT * FROM jobs
                 WHERE state = 'running'
                   AND lease_until IS NOT NULL
                   AND lease_until <= ?
                   AND attempt < ?
              ORDER BY lease_until, created_at, job_id
                LIMIT 1
                """,
                (_iso(now), MAX_ATTEMPTS),
            ).fetchone()
        if row is None:
            connection.commit()
            return None
        lease_until = now + timedelta(seconds=lease_seconds)
        lease_token = uuid.uuid4().hex
        connection.execute(
            """
            UPDATE jobs
               SET state = 'running',
                   attempt = attempt + 1,
                   lease_until = ?,
                   worker_id = ?,
                   lease_token = ?,
                   lease_heartbeat = ?,
                   updated_at = ?
             WHERE job_id = ?
            """,
            (_iso(lease_until), worker_id, lease_token, _iso(now), _iso(now), row["job_id"]),
        )
        claimed = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (row["job_id"],)).fetchone()
        connection.commit()
        if claimed is None:
            raise CoordinationError("queue_corrupt", "claimed job disappeared from durable queue")
        return _job_from_row(claimed), _job_request(claimed)
    except CoordinationError:
        connection.rollback()
        raise
    except sqlite3.Error as exc:
        connection.rollback()
        raise CoordinationError("queue_claim_failed", f"could not claim durable job: {exc}") from exc
    finally:
        connection.close()


def _update_job(
    queue_path: Path | str,
    *,
    job_id: str,
    worker_id: str,
    state: str,
    now: datetime,
    result_ref: str | None = None,
    error_code: str | None = None,
    due_at: datetime | None = None,
    lease_token: str | None = None,
) -> dict[str, Any]:
    connection = _connect(queue_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        values = (
            state,
            _iso(due_at or now),
            result_ref,
            error_code,
            _iso(now),
            job_id,
            worker_id,
            lease_token,
        )
        updated = connection.execute(
            """
            UPDATE jobs
               SET state = ?, due_at = ?, lease_until = NULL, worker_id = NULL,
                   lease_token = NULL, lease_heartbeat = NULL,
                   result_ref = ?, error_code = ?, updated_at = ?
             WHERE job_id = ? AND state = 'running' AND worker_id = ?
               AND (lease_token = ? OR (? IS NULL AND lease_token IS NULL))
            """,
            (*values, lease_token),
        ).rowcount
        if updated != 1:
            raise CoordinationError("job_lease_lost", "job lease was lost before recognition")
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        connection.commit()
        if row is None:
            raise CoordinationError("queue_corrupt", "recognized job disappeared from durable queue")
        return _job_from_row(row, now=now)
    except CoordinationError:
        connection.rollback()
        raise
    except sqlite3.Error as exc:
        connection.rollback()
        raise CoordinationError("queue_update_failed", f"could not update durable job: {exc}") from exc
    finally:
        connection.close()


def _load_job_receipt(path: Path, *, job: Mapping[str, Any], work: Mapping[str, Any]) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CoordinationError("job_receipt_invalid", "job effect receipt is unreadable") from exc
    if not isinstance(payload, dict) or not validate_artifact("job-receipt", payload).ok:
        raise CoordinationError("job_receipt_invalid", "job effect receipt violates its contract")
    if (
        payload["job_id"] != job["job_id"]
        or payload["package_id"] != job["package_id"]
        or payload["target_revision"] != job["target_revision"]
        or payload["request_hash"] != _work_hash(work)
    ):
        raise CoordinationError("job_receipt_stale", "job effect receipt does not match the current job")
    return payload


def _work_options(work: Mapping[str, Any]) -> tuple[str, Any]:
    from .operations import OperationOptions, OperationRequest

    source = work.get("source")
    output_dir = work.get("output_dir")
    if not isinstance(source, str) or not source.strip() or not isinstance(output_dir, str) or not output_dir.strip():
        raise CoordinationError("job_invalid", "worker job requires source and output_dir")
    options = OperationOptions(
        output_dir=Path(output_dir),
        catalog=Path(str(work["catalog"])) if work.get("catalog") else None,
        slug=str(work["slug"]) if work.get("slug") is not None else None,
        version=str(work["version"]) if work.get("version") is not None else None,
        scope=str(work["scope"]) if work.get("scope") is not None else None,
        language=str(work["language"]) if work.get("language") is not None else None,
        mode=str(work.get("mode", "run")),
        layers=tuple(work.get("layers") or ("conceptual", "factual")),
        publication_policy=str(work.get("publication_policy", "candidate")),
        license=str(work["license"]) if work.get("license") is not None else None,
        redistribution=str(work.get("redistribution", "private-only")),
        index_rag=bool(work.get("index_rag", False)),
        max_pages=int(work.get("max_pages", 50)),
        max_depth=int(work.get("max_depth", 2)),
        include_patterns=tuple(str(value) for value in work.get("include_patterns", ())),
        exclude_patterns=tuple(str(value) for value in work.get("exclude_patterns", ())),
        allow_private_network=bool(work.get("allow_private_network", False)),
        runtime_root=Path(str(work["runtime_root"])) if work.get("runtime_root") else None,
        source_root=Path(str(work["source_root"])) if work.get("source_root") else None,
        lease_policy="fail",
    )
    return source, OperationRequest(source, options)


def _execute_work(
    queue_path: Path | str,
    *,
    job: Mapping[str, Any],
    payload: Mapping[str, Any],
    now: datetime,
) -> tuple[str, str | None, dict[str, Any]]:
    event_payload = payload.get("payload")
    if not isinstance(event_payload, Mapping):
        event_payload = payload
    work = event_payload.get("work")
    if not isinstance(work, Mapping):
        raise CoordinationError("job_invalid", "source job does not contain a work request")
    if str(work.get("publication_policy", "candidate")) != "candidate":
        raise CoordinationError(
            "auto_publication_disabled",
            "automatic workers prepare candidates; publication requires the explicit gate",
        )
    if str(work.get("kind") or "") == "feedback_report":
        output_dir_value = work.get("output_dir")
        if not isinstance(output_dir_value, str) or not output_dir_value.strip():
            raise CoordinationError("job_invalid", "feedback report job requires output_dir")
        output_dir = Path(output_dir_value)
        receipt_path = _job_receipt_path(output_dir, str(job["job_id"]))
        existing_receipt = _load_job_receipt(receipt_path, job=job, work=work)
        if existing_receipt is not None:
            return "effect_reconciled", existing_receipt.get("result_ref"), existing_receipt
        from .feedback import FeedbackError, build_feedback_report

        try:
            report = build_feedback_report(output_dir, now=now)
        except FeedbackError as exc:
            raise CoordinationError(exc.code, str(exc), details=exc.details) from exc
        result_ref = str(report["report_id"])
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "job_id": job["job_id"],
            "package_id": job["package_id"],
            "target_revision": job["target_revision"],
            "request_hash": _work_hash(work),
            "status": "succeeded",
            "effect_code": "feedback_reported",
            "result_ref": result_ref,
            "recorded_at": _iso(now),
        }
        write_json_atomic(receipt_path, receipt)
        if os.environ.get("DOCOPS_TEST_WORKER_CRASH_AFTER_EFFECT") == "1":
            raise RuntimeError("synthetic worker crash after effect receipt")
        return "feedback_reported", result_ref, report
    source, request = _work_options(work)
    output_dir = request.options.output_dir
    policy_revision = str(event_payload.get("policy_revision") or job.get("policy_revision") or "")
    if request.options.index_rag:
        try:
            read_rag_authorization(
                output_dir,
                package_id=str(job["package_id"]),
                target_revision=str(job["target_revision"]),
                policy_revision=policy_revision,
                now=now,
            )
        except AuthorizationError as exc:
            raise CoordinationError(exc.code, str(exc)) from exc
    receipt_path = _job_receipt_path(output_dir, str(job["job_id"]))
    existing_receipt = _load_job_receipt(receipt_path, job=job, work=work)
    if existing_receipt is not None:
        return "effect_reconciled", existing_receipt.get("result_ref"), existing_receipt
    from .operations import apply as apply_operation
    from .operations import plan as build_plan

    result = apply_operation(build_plan(source, options=request.options))
    outcome = dict(result.outcome)
    if not result.ok:
        return str(outcome.get("code") or "job_failed"), None, result.to_dict()
    effect_code = str(outcome.get("code") or "completed")
    result_ref = outcome.get("candidate_id") or outcome.get("release_id")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "job_id": job["job_id"],
        "package_id": job["package_id"],
        "target_revision": job["target_revision"],
        "request_hash": _work_hash(work),
        "status": "succeeded",
        "effect_code": effect_code,
        "result_ref": result_ref,
        "recorded_at": _iso(now),
    }
    write_json_atomic(receipt_path, receipt)
    if os.environ.get("DOCOPS_TEST_WORKER_CRASH_AFTER_EFFECT") == "1":
        raise RuntimeError("synthetic worker crash after effect receipt")
    return effect_code, result_ref, result.to_dict()


def _is_transient(code: str) -> bool:
    return code in {
        "queue_busy",
        "queue_claim_failed",
        "queue_update_failed",
        "writer_busy",
        "lease_unavailable",
        "plan_refresh_failed",
        "mcp_timeout",
        "rag_backend_unavailable",
        "reindex_timeout",
    }


def work_once(
    queue_path: Path | str,
    *,
    now: str | datetime | None = None,
    worker_id: str | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    """Claim and execute at most one eligible job, preserving resumable effects."""

    current = _parse_time(now)
    if isinstance(lease_seconds, bool) or lease_seconds <= 0:
        raise CoordinationError("lease_invalid", "lease_seconds must be positive")
    identity = worker_id or f"worker-{os.getpid()}-{uuid.uuid4().hex[:12]}"
    claimed = _claim_job(queue_path, now=current, worker_id=identity, lease_seconds=lease_seconds)
    if claimed is None:
        return {"schema_version": SCHEMA_VERSION, "ok": True, "code": "no_job", "job": None}
    job, payload = claimed
    try:
        code, result_ref, effect = _execute_work(queue_path, job=job, payload=payload, now=current)
    except RuntimeError:
        raise
    except CoordinationError as exc:
        code = exc.code
        result_ref = None
        effect = {"ok": False, "errors": [{"code": exc.code, "message": str(exc)}]}
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        code = "worker_failed"
        result_ref = None
        effect = {"ok": False, "errors": [{"code": code, "message": str(exc)}]}

    attempt = int(job["attempt"])
    if code in {"completed", "candidate_prepared", "feedback_reported", "effect_reconciled"}:
        state = "succeeded"
        next_due = current
        job_result = _update_job(
            queue_path,
            job_id=str(job["job_id"]),
            worker_id=identity,
            state=state,
            now=current,
            result_ref=str(result_ref) if result_ref is not None else None,
            lease_token=str(job.get("lease_token")) if job.get("lease_token") else None,
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "code": code,
            "job": job_result,
            "effect": effect,
            "result_ref": result_ref,
            "candidate_id": result_ref if code == "candidate_prepared" else None,
        }
    if _is_transient(code) and attempt < MAX_ATTEMPTS:
        delay = RETRY_DELAYS_SECONDS[min(attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)]
        next_due = current + timedelta(seconds=delay)
        job_result = _update_job(
            queue_path,
            job_id=str(job["job_id"]),
            worker_id=identity,
            state="pending",
            now=current,
            error_code=code,
            due_at=next_due,
            lease_token=str(job.get("lease_token")) if job.get("lease_token") else None,
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "code": "retry_scheduled",
            "job": job_result,
            "effect": effect,
        }
    job_result = _update_job(
        queue_path,
        job_id=str(job["job_id"]),
        worker_id=identity,
        state="blocked",
        now=current,
        error_code=code,
        lease_token=str(job.get("lease_token")) if job.get("lease_token") else None,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "code": "job_blocked",
        "job": job_result,
        "effect": effect,
    }


def renew_job_lease(
    queue_path: Path | str,
    job_id: str,
    *,
    worker_id: str,
    lease_token: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Renew ownership only when the current worker still holds the fencing token."""

    current = _parse_time(now)
    if isinstance(lease_seconds, bool) or lease_seconds <= 0:
        raise CoordinationError("lease_invalid", "lease_seconds must be positive")
    connection = _connect(queue_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        lease_until = current + timedelta(seconds=lease_seconds)
        changed = connection.execute(
            """
            UPDATE jobs
               SET lease_until = ?, lease_heartbeat = ?, updated_at = ?
             WHERE job_id = ? AND state = 'running' AND worker_id = ? AND lease_token = ?
            """,
            (_iso(lease_until), _iso(current), _iso(current), job_id, worker_id, lease_token),
        ).rowcount
        if changed != 1:
            connection.rollback()
            raise CoordinationError("job_lease_lost", "job lease cannot be renewed by this owner")
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        connection.commit()
        if row is None:
            raise CoordinationError("queue_corrupt", "renewed job disappeared from durable queue")
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "code": "lease_renewed",
            "job": _job_from_row(row, now=current),
        }
    except CoordinationError:
        raise
    except sqlite3.Error as exc:
        connection.rollback()
        raise CoordinationError("queue_update_failed", f"could not renew durable job lease: {exc}") from exc
    finally:
        connection.close()


__all__ = [
    "CoordinationError",
    "DEBOUNCE_SECONDS",
    "DEFAULT_LEASE_SECONDS",
    "MAX_ATTEMPTS",
    "MAX_DEBOUNCE_SECONDS",
    "list_jobs",
    "submit_event",
    "work_once",
    "renew_job_lease",
]
