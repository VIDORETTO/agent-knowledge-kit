"""Durable, review-first coordination for continuously maintained packages.

The active DOCOPS package remains a filesystem generation.  This module keeps
events, jobs, candidates and approvals in a private SQLite runtime directory
next to (or explicitly outside) that generation.  It deliberately prepares
candidates by default; publishing is a separate, explicit operation.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .lease import PackageLease
from .manifest import redact_metadata, utc_now
from .observability import redact_report, redact_text
from .operations import OperationOptions, _promote, _remove_generated_path
from .operations import apply as apply_operation
from .operations import plan as build_plan
from .package_validator import validate_package
from .revisions import compute_revisions

SCHEMA_VERSION = 1
DEBOUNCE_SECONDS = 60.0
MAX_DEBOUNCE_SECONDS = 5 * 60.0
JOB_LEASE_SECONDS = 5 * 60.0
MAX_ATTEMPTS = 5


def _timestamp() -> float:
    return time.time()


def _iso_timestamp(value: float | None = None) -> str:
    instant = datetime.fromtimestamp(value if value is not None else _timestamp(), timezone.utc)
    return instant.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _package_id(package_root: Path) -> str:
    return f"package-{hashlib.sha256(str(package_root.resolve()).encode('utf-8')).hexdigest()[:16]}"


def runtime_directory(package_root: Path | str, runtime_root: Path | str | None = None) -> Path:
    """Return the private lifecycle directory without exposing its path publicly."""

    package = Path(package_root).expanduser().resolve()
    if runtime_root is not None:
        runtime = Path(runtime_root).expanduser().resolve()
    else:
        runtime = package.parent / f".{package.name}.docops-runtime"
    if runtime == package or package in runtime.parents:
        raise ValueError("lifecycle runtime must not be inside the active package")
    runtime.mkdir(parents=True, exist_ok=True)
    return runtime


class LifecycleStore:
    """Small durable store whose public projections contain no private paths."""

    def __init__(self, package_root: Path | str, runtime_root: Path | str | None = None) -> None:
        self.package_root = Path(package_root).expanduser().resolve()
        self.package_id = _package_id(self.package_root)
        self.runtime_root = runtime_directory(self.package_root, runtime_root)
        self.database = self.runtime_root / "lifecycle.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    canonical TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    scope TEXT,
                    version_policy TEXT NOT NULL,
                    language TEXT,
                    rights_json TEXT NOT NULL,
                    privacy_json TEXT NOT NULL,
                    authority_json TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    package_id TEXT NOT NULL,
                    source_id TEXT,
                    observed_revision TEXT,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    causation_id TEXT,
                    occurred_at TEXT NOT NULL,
                    first_observed REAL NOT NULL,
                    not_before REAL NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_due ON events(status, not_before);
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL REFERENCES events(event_id),
                    job_type TEXT NOT NULL,
                    package_id TEXT NOT NULL,
                    target_revision TEXT,
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    due_at REAL NOT NULL,
                    lease_id TEXT,
                    lease_until REAL,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_due ON jobs(state, due_at, lease_until);
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    base_release_id TEXT,
                    base_fingerprint TEXT NOT NULL,
                    target_revision TEXT,
                    status TEXT NOT NULL,
                    path TEXT NOT NULL,
                    revisions_json TEXT,
                    evidence_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
                    candidate_fingerprint TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    role TEXT NOT NULL,
                    policy_revision TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS releases (
                    release_id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    candidate_id TEXT,
                    parent_release_id TEXT,
                    fingerprint TEXT NOT NULL,
                    archive_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    claim_type TEXT NOT NULL,
                    scope TEXT,
                    version TEXT,
                    origin_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    privacy TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    generation TEXT,
                    kind TEXT NOT NULL,
                    query_hash TEXT,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS feedback_window ON feedback(package_id, kind, query_hash, created_at);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    @staticmethod
    def _public_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for key in ("payload_json", "origin_json", "evidence_json", "decision_json", "result_json", "revisions_json"):
            if key in result:
                try:
                    result[key.removesuffix("_json")] = json.loads(result.pop(key)) if result[key] else None
                except (TypeError, json.JSONDecodeError):
                    result[key.removesuffix("_json")] = None
        result.pop("path", None)
        result.pop("archive_path", None)
        result.pop("package_id", None)
        return redact_report(redact_metadata(result))

    def register_source(self, registration: Mapping[str, Any]) -> dict[str, Any]:
        required = ("source_id", "canonical", "kind", "owner")
        missing = [key for key in required if not str(registration.get(key) or "").strip()]
        if missing:
            return {"ok": False, "code": "source_registration_invalid", "missing": missing}
        now = utc_now()
        source_id = str(registration["source_id"])
        payload = redact_report(dict(registration))
        values = (
            source_id,
            str(registration["canonical"]),
            str(registration["kind"]),
            registration.get("scope"),
            str(registration.get("version_policy") or "explicit"),
            registration.get("language"),
            _json(redact_report(registration.get("rights") or {})),
            _json(redact_report(registration.get("privacy") or {})),
            _json(redact_report(registration.get("authority") or {})),
            str(registration["owner"]),
            str(registration.get("status") or "admitted"),
            _json(payload),
            now,
            now,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sources(source_id, canonical, kind, scope, version_policy, language,
                    rights_json, privacy_json, authority_json, owner, status, payload_json, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET canonical=excluded.canonical,
                    kind=excluded.kind, scope=excluded.scope, version_policy=excluded.version_policy,
                    language=excluded.language, rights_json=excluded.rights_json,
                    privacy_json=excluded.privacy_json, authority_json=excluded.authority_json,
                    owner=excluded.owner, status=excluded.status, payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                values,
            )
            row = connection.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()
        return {"ok": True, "source": self._public_row(row) if row else None}

    def submit_event(
        self,
        *,
        event_type: str,
        source_id: str | None = None,
        observed_revision: str | None = None,
        payload: Mapping[str, Any] | None = None,
        event_id: str | None = None,
        causation_id: str | None = None,
        debounce_seconds: float = DEBOUNCE_SECONDS,
    ) -> dict[str, Any]:
        if not event_type.strip():
            return {"ok": False, "code": "event_type_required"}
        if isinstance(debounce_seconds, bool) or not 0 <= debounce_seconds <= MAX_DEBOUNCE_SECONDS:
            return {"ok": False, "code": "debounce_invalid"}
        now = _timestamp()
        event_id = event_id or f"event-{uuid.uuid4().hex}"
        # The queue is private operational state: retain the source reference
        # needed by the worker, while every public projection remains redacted.
        safe_payload = dict(payload or {})
        payload_hash = _hash(safe_payload)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
            if existing is not None:
                if existing["payload_hash"] != payload_hash:
                    connection.rollback()
                    return {"ok": False, "code": "event_conflict", "event_id": event_id}
                connection.commit()
                return {"ok": True, "duplicate": True, "event_id": event_id, "job_id": self._job_for_event(event_id)}
            existing = connection.execute(
                """SELECT * FROM events WHERE package_id = ? AND event_type = ?
                   AND source_id IS ? AND observed_revision IS ? AND status IN ('pending','running')
                   ORDER BY first_observed ASC LIMIT 1""",
                (self.package_id, event_type, source_id, observed_revision),
            ).fetchone()
            if existing is not None:
                due = min(existing["first_observed"] + MAX_DEBOUNCE_SECONDS, now + debounce_seconds)
                connection.execute(
                    "UPDATE events SET not_before = ?, payload_json = ?, payload_hash = ? WHERE event_id = ?",
                    (due, _json(safe_payload), payload_hash, existing["event_id"]),
                )
                connection.execute(
                    "UPDATE jobs SET due_at = ?, updated_at = ? WHERE event_id = ?",
                    (due, _iso_timestamp(), existing["event_id"]),
                )
                connection.commit()
                return {
                    "ok": True,
                    "duplicate": True,
                    "event_id": existing["event_id"],
                    "job_id": self._job_for_event(existing["event_id"]),
                }
            connection.execute(
                """INSERT INTO events(event_id,event_type,package_id,source_id,observed_revision,
                   payload_json,payload_hash,causation_id,occurred_at,first_observed,not_before,status)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?, 'pending')""",
                (
                    event_id,
                    event_type,
                    self.package_id,
                    source_id,
                    observed_revision,
                    _json(safe_payload),
                    payload_hash,
                    causation_id,
                    _iso_timestamp(),
                    now,
                    now + debounce_seconds,
                ),
            )
            job_id = f"job-{uuid.uuid4().hex}"
            connection.execute(
                """INSERT INTO jobs(job_id,event_id,job_type,package_id,target_revision,payload_json,state,
                   attempt,due_at,created_at,updated_at) VALUES(?,?,?,?,?,?, 'pending',0,?,?,?)""",
                (
                    job_id,
                    event_id,
                    event_type,
                    self.package_id,
                    observed_revision,
                    _json(safe_payload),
                    now + debounce_seconds,
                    _iso_timestamp(),
                    _iso_timestamp(),
                ),
            )
            connection.commit()
        return {
            "ok": True,
            "duplicate": False,
            "event_id": event_id,
            "job_id": job_id,
            "not_before": _iso_timestamp(now + debounce_seconds),
        }

    def _job_for_event(self, event_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT job_id FROM jobs WHERE event_id = ?", (event_id,)).fetchone()
        return str(row["job_id"]) if row else None

    def claim_job(self, *, force: bool = False) -> dict[str, Any] | None:
        now = _timestamp()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if force:
                row = connection.execute(
                    "SELECT * FROM jobs WHERE state = 'pending' ORDER BY due_at, created_at LIMIT 1"
                ).fetchone()
            else:
                row = connection.execute(
                    """SELECT * FROM jobs WHERE (state = 'pending' AND due_at <= ?)
                       OR (state = 'running' AND lease_until < ?)
                       ORDER BY due_at, created_at LIMIT 1""",
                    (now, now),
                ).fetchone()
            if row is None:
                connection.commit()
                return None
            lease_id = f"job-lease-{uuid.uuid4().hex}"
            attempt = int(row["attempt"]) + 1
            if attempt > MAX_ATTEMPTS:
                connection.execute(
                    "UPDATE jobs SET state='blocked', error_code='retry_exhausted', updated_at=? WHERE job_id=?",
                    (_iso_timestamp(), row["job_id"]),
                )
                connection.commit()
                return None
            connection.execute(
                "UPDATE jobs SET state='running', attempt=?, lease_id=?, lease_until=?, updated_at=? WHERE job_id=?",
                (attempt, lease_id, now + JOB_LEASE_SECONDS, _iso_timestamp(), row["job_id"]),
            )
            connection.execute("UPDATE events SET status='running' WHERE event_id = ?", (row["event_id"],))
            connection.commit()
            result = dict(row)
            result.update({"attempt": attempt, "lease_id": lease_id})
            try:
                result["payload"] = json.loads(result.pop("payload_json"))
            except (TypeError, json.JSONDecodeError):
                result["payload"] = {}
            return result

    def complete_job(self, job_id: str, lease_id: str, result: Mapping[str, Any]) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET state='succeeded', result_json=?, lease_id=NULL, lease_until=NULL, updated_at=? WHERE job_id=? AND lease_id=?",
                (_json(redact_report(dict(result))), _iso_timestamp(), job_id, lease_id),
            )
            if cursor.rowcount:
                event_id = connection.execute("SELECT event_id FROM jobs WHERE job_id = ?", (job_id,)).fetchone()[
                    "event_id"
                ]
                connection.execute("UPDATE events SET status='succeeded' WHERE event_id = ?", (event_id,))
            return bool(cursor.rowcount)

    def fail_job(self, job_id: str, lease_id: str, *, code: str, message: str, retry: bool = False) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT attempt,event_id FROM jobs WHERE job_id=? AND lease_id=?", (job_id, lease_id)
            ).fetchone()
            if row is None:
                return False
            retry_allowed = retry and int(row["attempt"]) < MAX_ATTEMPTS
            state = "pending" if retry_allowed else "failed"
            due = _timestamp() + (60.0 * (2 ** max(0, int(row["attempt"]) - 1))) if retry_allowed else _timestamp()
            connection.execute(
                "UPDATE jobs SET state=?, due_at=?, lease_id=NULL, lease_until=NULL, error_code=?, error_message=?, updated_at=? WHERE job_id=?",
                (state, due, code, redact_text(message), _iso_timestamp(), job_id),
            )
            connection.execute(
                "UPDATE events SET status=? WHERE event_id=?",
                ("pending" if retry_allowed else "failed", row["event_id"]),
            )
            return True

    def submit_learning(
        self,
        *,
        claim: str,
        claim_type: str,
        origin: Mapping[str, Any],
        evidence: list[Mapping[str, Any]],
        scope: str | None = None,
        version: str | None = None,
        privacy: str = "private",
    ) -> dict[str, Any]:
        if not claim.strip() or len(claim) > 20_000:
            return {"ok": False, "code": "claim_invalid"}
        allowed = {"fact", "decision", "correction", "experiment", "opinion", "preference", "question"}
        if claim_type not in allowed:
            return {"ok": False, "code": "claim_type_invalid"}
        if not isinstance(evidence, list):
            return {"ok": False, "code": "evidence_invalid"}
        proposal_id = f"proposal-{uuid.uuid4().hex}"
        now = utc_now()
        safe_origin = redact_report(dict(origin))
        safe_evidence = redact_report(evidence)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO proposals(proposal_id,package_id,claim,claim_type,scope,version,origin_json,
                   evidence_json,privacy,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,'proposed',?,?)""",
                (
                    proposal_id,
                    self.package_id,
                    redact_text(claim),
                    claim_type,
                    scope,
                    version,
                    _json(safe_origin),
                    _json(safe_evidence),
                    privacy,
                    now,
                    now,
                ),
            )
        return {"ok": True, "proposal_id": proposal_id, "status": "proposed", "claim_hash": _hash(claim)}

    def review_learning(self, proposal_id: str, *, decision: str, reviewer: str, note: str = "") -> dict[str, Any]:
        if decision not in {"admit", "reject", "quarantine"} or not reviewer.strip():
            return {"ok": False, "code": "review_invalid"}
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if row is None:
                return {"ok": False, "code": "proposal_not_found"}
            evidence = json.loads(row["evidence_json"])
            if decision == "admit" and (not evidence or row["claim_type"] in {"preference", "opinion"}):
                return {"ok": False, "code": "admission_requires_independent_evidence"}
            status = "admitted" if decision == "admit" else "rejected" if decision == "reject" else "quarantined"
            payload = {
                "decision": decision,
                "reviewer": redact_text(reviewer),
                "note": redact_text(note),
                "at": utc_now(),
            }
            connection.execute(
                "UPDATE proposals SET status=?,decision_json=?,updated_at=? WHERE proposal_id=?",
                (status, _json(payload), utc_now(), proposal_id),
            )
        return {"ok": True, "proposal_id": proposal_id, "status": status}

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            counts: dict[str, dict[str, int]] = {}
            for table, key, state_column in (
                ("events", "events", "status"),
                ("jobs", "jobs", "state"),
                ("candidates", "candidates", "status"),
                ("proposals", "proposals", "status"),
            ):
                rows = connection.execute(
                    f"SELECT {state_column} AS state, COUNT(*) AS count FROM {table} GROUP BY {state_column}"
                ).fetchall()
                counts[key] = {str(row["state"]): int(row["count"]) for row in rows}
            release = connection.execute(
                "SELECT release_id,status,created_at FROM releases ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        revisions = compute_revisions(self.package_root) if (self.package_root / "manifest.json").is_file() else None
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "package_id": self.package_id,
            "events": {"pending": counts["events"].get("pending", 0), **counts["events"]},
            "jobs": {"pending": counts["jobs"].get("pending", 0), **counts["jobs"]},
            "candidates": counts["candidates"],
            "proposals": counts["proposals"],
            "active_revisions": revisions,
            "latest_release": dict(release) if release else None,
        }

    def create_candidate_record(self, *, base_fingerprint: str, path: Path, target_revision: str | None) -> str:
        candidate_id = f"candidate-{uuid.uuid4().hex}"
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO candidates(candidate_id,package_id,base_release_id,base_fingerprint,target_revision,
                   status,path,created_at,updated_at) VALUES(?,?,NULL,?,?, 'draft',?,?,?)""",
                (candidate_id, self.package_id, base_fingerprint, target_revision, str(path), now, now),
            )
        return candidate_id

    def update_candidate(
        self,
        candidate_id: str,
        *,
        status: str,
        revisions: Mapping[str, Any] | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE candidates SET status=?,revisions_json=?,evidence_json=?,updated_at=? WHERE candidate_id=?",
                (
                    _status_value(status),
                    _json(dict(revisions)) if revisions else None,
                    _json(dict(evidence)) if evidence else None,
                    utc_now(),
                    candidate_id,
                ),
            )

    def candidate(self, candidate_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
        return self._public_row(row) if row else None

    def approve_candidate(self, candidate_id: str, *, actor: str, role: str, policy_revision: str) -> dict[str, Any]:
        row = self.candidate(candidate_id)
        if row is None:
            return {"ok": False, "code": "candidate_not_found"}
        path = self._candidate_path(candidate_id)
        validation = validate_package(path)
        if not validation.ok:
            return {"ok": False, "code": "candidate_invalid", "errors": validation.errors}
        fingerprint = compute_revisions(path)["composition"]
        approval_id = f"approval-{uuid.uuid4().hex}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO approvals(approval_id,candidate_id,candidate_fingerprint,actor,role,policy_revision,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    approval_id,
                    candidate_id,
                    fingerprint,
                    redact_text(actor),
                    redact_text(role),
                    redact_text(policy_revision),
                    utc_now(),
                ),
            )
            connection.execute(
                "UPDATE candidates SET status='approved',updated_at=? WHERE candidate_id=?", (utc_now(), candidate_id)
            )
        return {"ok": True, "approval_id": approval_id, "candidate_id": candidate_id, "fingerprint": fingerprint}

    def _candidate_path(self, candidate_id: str) -> Path:
        with self._connect() as connection:
            row = connection.execute("SELECT path FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
        if row is None:
            raise ValueError("candidate not found")
        path = Path(row["path"]).resolve()
        path.relative_to(self.runtime_root.resolve())
        return path

    def publish_candidate(self, candidate_id: str) -> dict[str, Any]:
        row = self.candidate(candidate_id)
        if row is None:
            return {"ok": False, "code": "candidate_not_found"}
        if row.get("status") != "approved":
            return {"ok": False, "code": "candidate_not_approved"}
        candidate_path = self._candidate_path(candidate_id)
        validation = validate_package(candidate_path)
        if not validation.ok:
            return {"ok": False, "code": "candidate_invalid", "errors": validation.errors}
        fingerprint = compute_revisions(candidate_path)["composition"]
        with self._connect() as connection:
            approval = connection.execute(
                "SELECT * FROM approvals WHERE candidate_id=? ORDER BY created_at DESC LIMIT 1", (candidate_id,)
            ).fetchone()
        if approval is None or approval["candidate_fingerprint"] != fingerprint:
            return {"ok": False, "code": "approval_invalidated"}
        release_id = f"release-{fingerprint[:16]}-{uuid.uuid4().hex[:8]}"
        active = self.package_root
        active.parent.mkdir(parents=True, exist_ok=True)
        lease = PackageLease(active, policy="fail", wait_seconds=0.0, stale_after_seconds=300.0)
        try:
            lease.acquire()
        except Exception as exc:
            return {"ok": False, "code": "writer_busy", "message": redact_text(exc)}
        stage = active.parent / f".{active.name}.lifecycle-{uuid.uuid4().hex}"
        archive = self.runtime_root / "releases" / release_id / "package"
        backup = None
        try:
            shutil.copytree(candidate_path, stage)
            parent_release = self._latest_release_id()
            backup = _promote(stage, active, f".{active.name}.backup-{release_id}", plan_hash=fingerprint)
            published_validation = validate_package(active)
            if not published_validation.ok:
                if backup is not None and backup.exists():
                    _remove_generated_path(active)
                    os.replace(backup, active)
                return {"ok": False, "code": "publication_validation_failed", "errors": published_validation.errors}
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(active, archive)
            if backup is not None and backup.exists():
                _remove_generated_path(backup)
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO releases(release_id,package_id,candidate_id,parent_release_id,fingerprint,archive_path,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        release_id,
                        self.package_id,
                        candidate_id,
                        parent_release,
                        fingerprint,
                        str(archive),
                        "published",
                        utc_now(),
                    ),
                )
                connection.execute(
                    "UPDATE candidates SET status='published',updated_at=? WHERE candidate_id=?",
                    (utc_now(), candidate_id),
                )
            return {"ok": True, "release_id": release_id, "candidate_id": candidate_id, "fingerprint": fingerprint}
        except Exception as exc:
            if stage.exists():
                _remove_generated_path(stage)
            return {"ok": False, "code": "publication_failed", "message": redact_text(exc)}
        finally:
            lease.release()

    def _latest_release_id(self) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT release_id FROM releases WHERE status='published' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return str(row["release_id"]) if row else None

    def rollback(self, release_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM releases WHERE release_id=? AND status='published'", (release_id,)
            ).fetchone()
        if row is None:
            return {"ok": False, "code": "release_not_found"}
        archive = Path(row["archive_path"])
        if not archive.is_dir() or not validate_package(archive).ok:
            return {"ok": False, "code": "release_archive_invalid"}
        candidate_id = self.create_candidate_record(
            base_fingerprint=compute_revisions(self.package_root).get("composition", "absent"),
            path=archive,
            target_revision=release_id,
        )
        self.update_candidate(
            candidate_id, status="approved", revisions=compute_revisions(archive), evidence={"rollback_of": release_id}
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO approvals(approval_id,candidate_id,candidate_fingerprint,actor,role,policy_revision,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    f"approval-{uuid.uuid4().hex}",
                    candidate_id,
                    compute_revisions(archive)["composition"],
                    "rollback",
                    "operator",
                    "rollback",
                    utc_now(),
                ),
            )
        return self.publish_candidate(candidate_id)

    def _candidate_path_for_new(self, candidate_id: str) -> Path:
        path = self.runtime_root / "candidates" / candidate_id / "package"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def _status_value(value: str) -> str:
    return value if value in {"draft", "review_required", "approved", "published", "failed", "blocked"} else "blocked"


def prepare_candidate(
    package_root: Path | str,
    *,
    source: str | Path,
    options: Mapping[str, Any] | None = None,
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    """Build an isolated candidate using the existing DOCOPS operation seam."""

    store = LifecycleStore(package_root, runtime_root)
    active = store.package_root
    base_revisions = compute_revisions(active) if (active / "manifest.json").is_file() else {}
    candidate_id = f"candidate-{uuid.uuid4().hex}"
    candidate_path = store.runtime_root / "candidates" / candidate_id / "package"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    if active.is_dir() and (active / "manifest.json").is_file():
        shutil.copytree(active, candidate_path)
        mode = "update"
    else:
        candidate_path.mkdir(parents=True, exist_ok=True)
        mode = "run"
    values = dict(options or {})
    operation_options = OperationOptions(
        output_dir=candidate_path,
        source_root=Path(values["source_root"]).expanduser().resolve() if values.get("source_root") else None,
        slug=values.get("slug"),
        version=values.get("version"),
        scope=values.get("scope"),
        language=values.get("language"),
        mode=mode,
        license=values.get("license"),
        redistribution=values.get("redistribution", "private-only"),
        index_rag=bool(values.get("index_rag", False)),
        runtime_root=Path(values["runtime_root"]).expanduser().resolve() if values.get("runtime_root") else None,
        lease_policy="fail",
    )
    operation = build_plan(str(source), options=operation_options)
    result = apply_operation(operation)
    if not result.ok:
        return {
            "ok": False,
            "code": "candidate_build_failed",
            "candidate_id": candidate_id,
            "errors": result.errors,
            "outcome": result.outcome,
        }
    revisions = compute_revisions(candidate_path)
    store.create_candidate_record(
        base_fingerprint=base_revisions.get("composition", "absent"),
        path=candidate_path,
        target_revision=revisions["composition"],
    )
    # The row is inserted with a generated id; keep the public id stable by
    # moving the record when the store generated a different value.
    with store._connect() as connection:
        row = connection.execute("SELECT candidate_id FROM candidates WHERE path=?", (str(candidate_path),)).fetchone()
        actual_id = str(row["candidate_id"]) if row else candidate_id
    store.update_candidate(
        actual_id, status="review_required", revisions=revisions, evidence={"operation": result.to_dict()}
    )
    return {"ok": True, "candidate_id": actual_id, "base_revisions": base_revisions, "revisions": revisions}


def reconcile_source(
    package_root: Path | str,
    *,
    source: str | Path,
    options: Mapping[str, Any] | None = None,
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    """Compare a source through the existing plan seam and enqueue only a real diff."""

    store = LifecycleStore(package_root, runtime_root)
    values = dict(options or {})
    operation_options = OperationOptions(
        output_dir=Path(package_root).expanduser().resolve(),
        source_root=Path(values["source_root"]).expanduser().resolve() if values.get("source_root") else None,
        slug=values.get("slug"),
        version=values.get("version"),
        scope=values.get("scope"),
        language=values.get("language"),
        mode="update",
        license=values.get("license"),
        redistribution=values.get("redistribution", "private-only"),
        index_rag=bool(values.get("index_rag", False)),
        runtime_root=Path(values["runtime_root"]).expanduser().resolve() if values.get("runtime_root") else None,
    )
    operation = build_plan(str(source), options=operation_options)
    if not operation.ok:
        return {"ok": False, "code": "reconcile_blocked", "blockers": list(operation.blockers)}
    diff = dict(operation.state_diff)
    if not any(diff.values()):
        return {"ok": True, "changed": False, "state_diff": diff, "source_revision": operation.source_fingerprint}
    event = store.submit_event(
        event_type="source.reconcile",
        observed_revision=operation.source_fingerprint,
        debounce_seconds=DEBOUNCE_SECONDS,
        payload={"source": str(source), "options": values},
    )
    return {
        "ok": bool(event.get("ok")),
        "changed": True,
        "state_diff": diff,
        "source_revision": operation.source_fingerprint,
        "event": event,
    }


def work_once(
    package_root: Path | str, *, runtime_root: Path | str | None = None, force: bool = False
) -> dict[str, Any]:
    store = LifecycleStore(package_root, runtime_root)
    job = store.claim_job(force=force)
    if job is None:
        return {"ok": True, "worked": False, "reason": "no_due_job"}
    payload = job.get("payload") if isinstance(job.get("payload"), Mapping) else {}
    try:
        if not payload.get("source"):
            raise ValueError("event payload requires source for document processing")
        result = prepare_candidate(
            package_root,
            source=str(payload["source"]),
            options=payload.get("options") if isinstance(payload.get("options"), Mapping) else {},
            runtime_root=runtime_root,
        )
        if result.get("ok"):
            store.complete_job(job["job_id"], job["lease_id"], result)
        else:
            store.fail_job(
                job["job_id"],
                job["lease_id"],
                code=str(result.get("code", "candidate_failed")),
                message=str(result.get("errors", result)),
                retry=False,
            )
        return {"ok": bool(result.get("ok")), "worked": True, "job_id": job["job_id"], "result": result}
    except Exception as exc:
        store.fail_job(job["job_id"], job["lease_id"], code="worker_failed", message=str(exc), retry=False)
        return {
            "ok": False,
            "worked": True,
            "job_id": job["job_id"],
            "code": "worker_failed",
            "message": redact_text(exc),
        }
