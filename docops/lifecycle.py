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

from .coordination import TriggerPolicy, assess_skill_trigger
from .lease import PackageLease
from .manifest import redact_metadata, utc_now
from .observability import redact_report, redact_text
from .operations import OperationOptions, _promote, _remove_generated_path
from .operations import apply as apply_operation
from .operations import plan as build_plan
from .package_validator import validate_package
from .rag_sync import RagSynchronizer
from .readiness import assess_readiness, record_skill_enrichment, skill_fingerprint
from .revisions import compute_revisions
from .state import SourceRecord, StateStore
from .storage import write_json_atomic, write_text_atomic

SCHEMA_VERSION = 1
DEBOUNCE_SECONDS = 60.0
MAX_DEBOUNCE_SECONDS = 5 * 60.0
JOB_LEASE_SECONDS = 5 * 60.0
MAX_ATTEMPTS = 5
MAX_ENRICHMENT_BYTES = 4 * 1024 * 1024
CONCEPTUAL_EVENT_TYPES = frozenset({"document.changed", "source.reconcile", "source.revoked", "source.conflict"})


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

    def revoke_source(self, source_id: str, *, actor: str, reason: str = "") -> dict[str, Any]:
        """Create an explicit tombstone and immediately block derived readers."""

        if not source_id.strip() or not actor.strip():
            return {"ok": False, "code": "source_revoke_invalid"}
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM sources WHERE source_id=?", (source_id,)).fetchone()
            if row is None:
                return {"ok": False, "code": "source_not_found"}
            connection.execute(
                "UPDATE sources SET status='revoked',updated_at=? WHERE source_id=?",
                (utc_now(), source_id),
            )
        canonical = str(row["canonical"])
        local_prefix = ""
        if str(row["kind"]) == "local":
            local_prefix = f"file://local/{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}/"
        destinations: list[str] = []
        manifest_path = self.package_root / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            manifest = {}
        entries = manifest.get("entries") if isinstance(manifest, dict) else []
        package_source = manifest.get("source", {}).get("canonical") if isinstance(manifest, dict) else None
        if isinstance(entries, list):
            destinations = sorted(
                {
                    str(entry.get("destination"))
                    for entry in entries
                    if isinstance(entry, Mapping)
                    and entry.get("destination")
                    and (
                        str(entry.get("canonical") or "") == canonical
                        or str(entry.get("canonical") or "").startswith(canonical.rstrip("/") + "/")
                        or (local_prefix and str(entry.get("canonical") or "").startswith(local_prefix))
                        or (str(package_source or "").startswith("file://local/") and str(row["kind"]) == "local")
                        or (package_source and canonical == str(package_source))
                    )
                }
            )
        revocations_path = self.package_root / ".docops" / "revocations.json"
        try:
            current = json.loads(revocations_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            current = {"schema_version": 1, "sources": []}
        records = current.get("sources") if isinstance(current, dict) else []
        if not isinstance(records, list):
            records = []
        records = [item for item in records if not (isinstance(item, Mapping) and item.get("source_id") == source_id)]
        records.append(
            {
                "source_id": source_id,
                "canonical": canonical,
                "destinations": destinations,
                "actor": redact_text(actor),
                "reason": redact_text(reason),
                "revoked_at": utc_now(),
            }
        )
        revocations_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(revocations_path, {"schema_version": 1, "sources": records})
        if isinstance(manifest, dict):
            manifest["revocations"] = {"source_ids": sorted({str(item.get("source_id")) for item in records})}
            manifest["revisions"] = compute_revisions(self.package_root)
            write_json_atomic(manifest_path, manifest)
        event = self.submit_event(
            event_type="source.revoked",
            source_id=source_id,
            observed_revision=_hash({"source_id": source_id, "canonical": canonical, "destinations": destinations}),
            debounce_seconds=0.0,
            payload={
                "source": canonical,
                "destinations": destinations,
                "critical": True,
                "reason": redact_text(reason),
            },
        )
        return {
            "ok": True,
            "source_id": source_id,
            "status": "revoked",
            "destinations": destinations,
            "event": event,
        }

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
        result = {
            "ok": True,
            "duplicate": False,
            "event_id": event_id,
            "job_id": job_id,
            "not_before": _iso_timestamp(now + debounce_seconds),
        }
        if event_type in CONCEPTUAL_EVENT_TYPES:
            result["skill_trigger"] = self._maybe_request_skill_trigger()
        return result

    def _job_for_event(self, event_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT job_id FROM jobs WHERE event_id = ?", (event_id,)).fetchone()
        return str(row["job_id"]) if row else None

    def _metadata_value(self, key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def _set_metadata_value(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def _active_corpus_documents(self) -> int:
        root = self.package_root / "rag" / "documents"
        if not root.is_dir():
            return 0
        return sum(1 for path in root.rglob("*") if path.is_file() and not path.is_symlink())

    def _maybe_request_skill_trigger(self) -> dict[str, Any] | None:
        """Queue one explainable enrichment request when policy thresholds fire."""

        last_raw = self._metadata_value("last_skill_trigger_at")
        try:
            last_trigger_at = float(last_raw) if last_raw else None
        except ValueError:
            last_trigger_at = None
        now = _timestamp()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE event_type IN ('document.changed','source.reconcile','source.revoked','source.conflict') "
                "AND status != 'failed' ORDER BY first_observed"
            ).fetchall()
            recent_requests = connection.execute(
                "SELECT COUNT(*) AS count FROM events WHERE event_type='skill.enrichment.requested' AND first_observed>=?",
                (now - 24 * 60 * 60,),
            ).fetchone()
        events: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                payload = {}
            events.append(
                {
                    "event_id": row["event_id"],
                    "event_type": row["event_type"],
                    "source_id": row["source_id"],
                    "observed_revision": row["observed_revision"],
                    "occurred_at": row["occurred_at"],
                    "payload": payload,
                }
            )
        decision = assess_skill_trigger(
            events,
            corpus_documents=self._active_corpus_documents(),
            now=now,
            last_trigger_at=last_trigger_at,
            policy=TriggerPolicy(),
        )
        result = decision.to_dict()
        if not decision.requested:
            return result
        if recent_requests and int(recent_requests["count"]) >= decision.policy.max_requests_per_day:
            result["suppressed"] = "daily_budget"
            self._set_metadata_value("skill_trigger_backlog", _json(result))
            return result
        event = self.submit_event(
            event_type="skill.enrichment.requested",
            observed_revision=_hash(
                {
                    "affected_documents": decision.affected_documents,
                    "affected_chars": decision.affected_chars,
                    "reasons": decision.reasons,
                }
            ),
            causation_id=str(events[-1].get("event_id") or "") if events else None,
            debounce_seconds=0.0,
            payload={
                "reasons": list(decision.reasons),
                "affected_documents": decision.affected_documents,
                "affected_chars": decision.affected_chars,
                "critical": decision.critical,
                "action": "prepare_external_enrichment_request",
            },
        )
        self._set_metadata_value("last_skill_trigger_at", str(now))
        result["event"] = event
        return result

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
        if privacy not in {"private", "shared", "restricted"}:
            return {"ok": False, "code": "privacy_invalid"}
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

    def _admitted_proposals(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM proposals WHERE status='admitted' ORDER BY created_at, proposal_id"
            ).fetchall()

    def materialize_admitted_learning(self, candidate_root: Path) -> list[str]:
        """Materialize reviewed claims into a candidate's corpus only."""

        proposals = self._admitted_proposals()
        if not proposals:
            return []
        documents = candidate_root / "rag" / "documents" / "learning"
        documents.mkdir(parents=True, exist_ok=True)
        state = StateStore(candidate_root / ".docops" / "state.json")
        records = state.records()
        sources_path = candidate_root / "rag" / "sources.json"
        try:
            sources_payload = json.loads(sources_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            sources_payload = {"schema_version": 1, "sources": []}
        sources = sources_payload.get("sources") if isinstance(sources_payload, dict) else []
        if not isinstance(sources, list):
            sources = []
        manifest_path = candidate_root / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            manifest = None
        entries = manifest.get("entries") if isinstance(manifest, dict) else []
        if not isinstance(entries, list):
            entries = []
        materialized: list[str] = []
        for proposal in proposals:
            # Private and restricted proposals may be useful to a caller's
            # memory layer, but are never copied into the shared package.
            if str(proposal["privacy"]) != "shared":
                continue
            proposal_id = str(proposal["proposal_id"])
            relative = f"learning/{proposal_id}.md"
            content = [
                "# Reviewed knowledge proposal",
                "",
                str(proposal["claim"]),
                "",
                f"Proposal: `{proposal_id}`",
                f"Claim type: `{proposal['claim_type']}`",
            ]
            if proposal["scope"]:
                content.append(f"Scope: `{proposal['scope']}`")
            if proposal["version"]:
                content.append(f"Version: `{proposal['version']}`")
            try:
                evidence = json.loads(proposal["evidence_json"])
            except (TypeError, json.JSONDecodeError):
                evidence = []
            if isinstance(evidence, list) and evidence:
                content.extend(["", "## Evidence", "", *[f"- `{redact_text(_json(item))}`" for item in evidence]])
            text = "\n".join(content).rstrip() + "\n"
            destination = documents / f"{proposal_id}.md"
            write_text_atomic(destination, text)
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            record = SourceRecord(f"conversation://{proposal_id}", proposal["version"], content_hash, relative)
            records = [existing for existing in records if existing.logical_key != record.logical_key]
            records.append(record)
            sources = [
                existing
                for existing in sources
                if not (isinstance(existing, dict) and existing.get("canonical") == record.canonical)
            ]
            sources.append(
                {
                    "source": f"conversation://{proposal_id}",
                    "canonical": f"conversation://{proposal_id}",
                    "destination": relative,
                    "title": "Reviewed knowledge proposal",
                    "format": "markdown",
                    "status": "accepted",
                    "content_hash": content_hash,
                    "version": proposal["version"],
                    "proposal_id": proposal_id,
                }
            )
            entries = [
                existing
                for existing in entries
                if not (isinstance(existing, dict) and existing.get("proposal_id") == proposal_id)
            ]
            entries.append(
                {
                    "source": f"conversation://{proposal_id}",
                    "canonical": f"conversation://{proposal_id}",
                    "destination": relative,
                    "title": "Reviewed knowledge proposal",
                    "format": "markdown",
                    "status": "accepted",
                    "content_hash": content_hash,
                    "proposal_id": proposal_id,
                }
            )
            materialized.append(proposal_id)
        state.commit(records)
        write_json_atomic(
            sources_path,
            {"schema_version": 1, "sources": sorted(sources, key=lambda item: str(item.get("canonical", "")))},
        )
        if isinstance(manifest, dict):
            manifest["entries"] = sorted(entries, key=lambda item: str(item.get("canonical", "")))
            counts = manifest.setdefault("counts", {})
            if isinstance(counts, dict):
                counts["accepted"] = sum(1 for item in manifest["entries"] if item.get("status") == "accepted")
            metrics = manifest.setdefault("metrics", {})
            if isinstance(metrics, dict):
                metrics["learning"] = {"materialized_proposals": materialized, "index_rebuild_required": True}
            manifest["readiness"] = assess_readiness(candidate_root)
            manifest["revisions"] = compute_revisions(candidate_root)
            write_json_atomic(manifest_path, manifest)
        index_path = candidate_root / "rag" / "index.json"
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            index = None
        if isinstance(index, dict):
            index["mode"] = "corpus-ready"
            index["backend_total_documents"] = None
            index["backend_total_chunks"] = None
            index["reindex_required"] = True
            index.setdefault("metrics", {})["learning"] = {"materialized_proposals": materialized}
            write_json_atomic(index_path, index)
        if isinstance(manifest, dict):
            manifest["readiness"] = assess_readiness(candidate_root)
            manifest["revisions"] = compute_revisions(candidate_root)
            write_json_atomic(manifest_path, manifest)
        return materialized

    def revoke_learning(self, proposal_id: str, *, reviewer: str, reason: str = "") -> dict[str, Any]:
        """Revoke a previously admitted proposal and block its candidates."""

        if not reviewer.strip():
            return {"ok": False, "code": "reviewer_required"}
        with self._connect() as connection:
            row = connection.execute("SELECT status FROM proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if row is None:
                return {"ok": False, "code": "proposal_not_found"}
            decision = {
                "decision": "revoke",
                "reviewer": redact_text(reviewer),
                "note": redact_text(reason),
                "at": utc_now(),
            }
            connection.execute(
                "UPDATE proposals SET status='revoked',decision_json=?,updated_at=? WHERE proposal_id=?",
                (_json(decision), utc_now(), proposal_id),
            )
            candidate_rows = connection.execute(
                "SELECT candidate_id,evidence_json FROM candidates WHERE status IN ('draft','review_required','approved')"
            ).fetchall()
            blocked: list[str] = []
            for candidate in candidate_rows:
                try:
                    evidence = json.loads(candidate["evidence_json"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    evidence = {}
                if proposal_id in _proposal_ids_from_evidence(evidence):
                    connection.execute(
                        "UPDATE candidates SET status='blocked',updated_at=? WHERE candidate_id=?",
                        (utc_now(), candidate["candidate_id"]),
                    )
                    blocked.append(str(candidate["candidate_id"]))
        return {"ok": True, "proposal_id": proposal_id, "status": "revoked", "blocked_candidates": blocked}

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
            feedback_rows = connection.execute("SELECT kind, COUNT(*) AS count FROM feedback GROUP BY kind").fetchall()
        revisions = compute_revisions(self.package_root) if (self.package_root / "manifest.json").is_file() else None
        backlog_raw = self._metadata_value("skill_trigger_backlog")
        try:
            skill_backlog = json.loads(backlog_raw) if backlog_raw else None
        except (TypeError, json.JSONDecodeError):
            skill_backlog = None
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "package_id": self.package_id,
            "events": {"pending": counts["events"].get("pending", 0), **counts["events"]},
            "jobs": {"pending": counts["jobs"].get("pending", 0), **counts["jobs"]},
            "candidates": counts["candidates"],
            "proposals": counts["proposals"],
            "feedback": {str(row["kind"]): int(row["count"]) for row in feedback_rows},
            "skill_trigger_backlog": skill_backlog,
            "active_revisions": revisions,
            "latest_release": dict(release) if release else None,
        }

    def submit_feedback(
        self,
        *,
        kind: str,
        query: str | None = None,
        generation: str | None = None,
        occurrence_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        allowed = {"unanswered", "conflict", "low_quality", "citation", "abstention"}
        if kind not in allowed:
            return {"ok": False, "code": "feedback_kind_invalid"}
        if query is not None and len(query) > 20_000:
            return {"ok": False, "code": "feedback_query_invalid"}
        feedback_id = f"feedback-{uuid.uuid4().hex}"
        occurrence = occurrence_id or feedback_id
        safe_payload = redact_report({**dict(payload or {}), "occurrence_id": occurrence})
        now = _timestamp()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO feedback(feedback_id,package_id,generation,kind,query_hash,payload_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    feedback_id,
                    self.package_id,
                    generation,
                    kind,
                    _hash(query) if query else None,
                    _json(safe_payload),
                    now,
                ),
            )
            window_start = now - 7 * 24 * 60 * 60
            rows = connection.execute(
                "SELECT payload_json FROM feedback WHERE package_id=? AND kind=? AND query_hash IS ? AND created_at>=?",
                (self.package_id, kind, _hash(query) if query else None, window_start),
            ).fetchall()
        occurrences: set[str] = set()
        for row in rows:
            try:
                value = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                value = {}
            if isinstance(value, dict) and value.get("occurrence_id"):
                occurrences.add(str(value["occurrence_id"]))
        investigation = len(occurrences) >= 3
        investigation_event = None
        if investigation:
            investigation_event = self.submit_event(
                event_type="investigation.requested",
                observed_revision=_hash({"kind": kind, "query": query}),
                debounce_seconds=0.0,
                payload={
                    "kind": kind,
                    "query_hash": _hash(query) if query else None,
                    "occurrences_7d": len(occurrences),
                },
            )
        return {
            "ok": True,
            "feedback_id": feedback_id,
            "kind": kind,
            "occurrences_7d": len(occurrences),
            "investigation_required": investigation,
            "investigation_event": investigation_event,
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

    def enrichment_request(self, candidate_id: str) -> dict[str, Any]:
        row = self.candidate(candidate_id)
        if row is None:
            return {"ok": False, "code": "candidate_not_found"}
        revisions = row.get("revisions") if isinstance(row.get("revisions"), Mapping) else {}
        request = {
            "schema_version": 1,
            "request_id": f"enrichment-{_hash({'candidate_id': candidate_id, 'revisions': revisions})[:24]}",
            "candidate_id": candidate_id,
            "status": row.get("status"),
            "base_revisions": revisions,
            "allowed_artifacts": ["skill/SKILL.md", "skill/*.md"],
            "max_bytes": MAX_ENRICHMENT_BYTES,
            "policy": "external-harness-review-required",
        }
        return {"ok": True, "request": request}

    def submit_enrichment(
        self,
        candidate_id: str,
        *,
        skill_root: Path | str,
        tool: str,
        version: str,
        provenance: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Import a constrained external skill result into a candidate only."""

        row = self.candidate(candidate_id)
        if row is None:
            return {"ok": False, "code": "candidate_not_found"}
        if row.get("status") not in {"draft", "review_required"}:
            return {"ok": False, "code": "candidate_not_enrichable", "status": row.get("status")}
        if not tool.strip() or not version.strip():
            return {"ok": False, "code": "enrichment_metadata_required"}
        candidate_path = self._candidate_path(candidate_id)
        before = compute_revisions(candidate_path)
        source = Path(skill_root).expanduser().resolve()
        if source == candidate_path or candidate_path in source.parents:
            return {"ok": False, "code": "enrichment_source_inside_candidate"}
        if (source / "skill").is_dir() and (source / "skill" / "SKILL.md").is_file():
            source = source / "skill"
        if not source.is_dir() or source.is_symlink() or not (source / "SKILL.md").is_file():
            return {"ok": False, "code": "enrichment_skill_missing"}
        files: list[Path] = []
        total = 0
        for path in sorted(source.rglob("*")):
            if path.is_dir():
                continue
            if path.is_symlink() or path.suffix.casefold() != ".md":
                return {"ok": False, "code": "enrichment_artifact_not_allowed"}
            try:
                path.relative_to(source)
                size = path.stat().st_size
            except OSError:
                return {"ok": False, "code": "enrichment_artifact_unreadable"}
            total += size
            if total > MAX_ENRICHMENT_BYTES:
                return {"ok": False, "code": "enrichment_too_large"}
            files.append(path)
        if not files:
            return {"ok": False, "code": "enrichment_skill_missing"}
        stage = candidate_path / ".docops" / f"enrichment-{uuid.uuid4().hex}"
        stage.mkdir(parents=True, exist_ok=True)
        backup_skill: Path | None = None
        try:
            for path in files:
                relative = path.relative_to(source)
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
            active_skill = candidate_path / "skill"
            backup_skill = candidate_path / ".docops" / f"skill-backup-{uuid.uuid4().hex}"
            if active_skill.exists():
                os.replace(active_skill, backup_skill)
            os.replace(stage, active_skill)
            if backup_skill.exists():
                shutil.rmtree(backup_skill)
            receipt_provenance = {
                **dict(provenance or {}),
                "base_composition": before["composition"],
                "input_skill_hash": hashlib.sha256(
                    "".join(
                        f"{path.relative_to(source).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}\\n"
                        for path in files
                    ).encode("utf-8")
                ).hexdigest(),
            }
            receipt_path = record_skill_enrichment(
                candidate_path,
                tool=tool,
                version=version,
                provenance=receipt_provenance,
                artifacts=[f"skill/{path.relative_to(source).as_posix()}" for path in files],
            )
        except (OSError, ValueError, UnicodeError) as exc:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)
            if backup_skill is not None and backup_skill.exists() and not (candidate_path / "skill").exists():
                os.replace(backup_skill, candidate_path / "skill")
            return {"ok": False, "code": "enrichment_import_failed", "message": redact_text(exc)}
        revisions = compute_revisions(candidate_path)
        evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
        updated_evidence = {
            **dict(evidence),
            "enrichment": {
                "receipt": ".docops/skill-enrichment.json",
                "tool": redact_text(tool),
                "version": redact_text(version),
                "base_composition": before["composition"],
                "output_skill_hash": skill_fingerprint(candidate_path),
                "receipt_path": str(receipt_path.name),
            },
        }
        self.update_candidate(candidate_id, status="review_required", revisions=revisions, evidence=updated_evidence)
        return {
            "ok": True,
            "candidate_id": candidate_id,
            "status": "review_required",
            "base_composition": before["composition"],
            "skill_revision": revisions["skill_revision"],
            "receipt": ".docops/skill-enrichment.json",
        }

    def evaluate_candidate(self, candidate_id: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
        """Persist an external evaluation receipt tied to the candidate hash."""

        row = self.candidate(candidate_id)
        if row is None:
            return {"ok": False, "code": "candidate_not_found"}
        if row.get("status") not in {"draft", "review_required"}:
            return {"ok": False, "code": "candidate_not_evaluable", "status": row.get("status")}
        candidate_path = self._candidate_path(candidate_id)
        composition = compute_revisions(candidate_path)["composition"]
        declared = evidence.get("composition") or evidence.get("evaluated_composition")
        if declared is not None and str(declared) != composition:
            return {"ok": False, "code": "evaluation_stale"}
        metrics = evidence.get("metrics")
        if not isinstance(metrics, Mapping) or not metrics:
            return {"ok": False, "code": "evaluation_metrics_required"}
        safe_metrics: dict[str, float] = {}
        for key, raw in metrics.items():
            try:
                value = float(raw)
            except (TypeError, ValueError, OverflowError):
                return {"ok": False, "code": "evaluation_metric_invalid", "metric": str(key)}
            if key.endswith("rate") or key in {
                "recall",
                "precision",
                "faithfulness",
                "abstention_rate",
                "recall_at_5",
                "mrr_at_5",
            }:
                if not 0 <= value <= 1:
                    return {"ok": False, "code": "evaluation_metric_out_of_range", "metric": str(key)}
            elif value < 0:
                return {"ok": False, "code": "evaluation_metric_out_of_range", "metric": str(key)}
            safe_metrics[str(key)] = value
        envelope = {
            "schema_version": 1,
            "ok": evidence.get("ok") is not False,
            "metrics": safe_metrics,
            "composition": composition,
            "metadata": redact_report(dict(evidence.get("metadata") or {})),
            "source": "external-harness",
        }
        evaluation_path = candidate_path / ".docops" / "evaluation.json"
        write_json_atomic(evaluation_path, envelope)
        manifest_path = candidate_path / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            manifest = None
        if isinstance(manifest, dict):
            manifest["readiness"] = assess_readiness(candidate_path)
            manifest["metrics"] = {
                **(manifest.get("metrics") if isinstance(manifest.get("metrics"), dict) else {}),
                "evaluation": envelope,
            }
            manifest["revisions"] = compute_revisions(candidate_path)
            write_json_atomic(manifest_path, manifest)
        revisions = compute_revisions(candidate_path)
        current_evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
        self.update_candidate(
            candidate_id,
            status="review_required",
            revisions=revisions,
            evidence={**dict(current_evidence), "evaluation": envelope},
        )
        return {
            "ok": True,
            "candidate_id": candidate_id,
            "composition": composition,
            "metrics": safe_metrics,
            "evaluation": ".docops/evaluation.json",
        }

    def approve_candidate(self, candidate_id: str, *, actor: str, role: str, policy_revision: str) -> dict[str, Any]:
        row = self.candidate(candidate_id)
        if row is None:
            return {"ok": False, "code": "candidate_not_found"}
        if row.get("status") not in {"draft", "review_required"}:
            return {"ok": False, "code": "candidate_not_reviewable", "status": row.get("status")}
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
        revoked = self._revoked_proposals_for_candidate(candidate_id)
        if revoked:
            return {"ok": False, "code": "revoked_dependency", "proposal_ids": revoked}
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
        if row.get("base_fingerprint") not in {None, "", "absent"} and (self.package_root / "manifest.json").is_file():
            active_fingerprint = compute_revisions(self.package_root)["composition"]
            if active_fingerprint != row["base_fingerprint"]:
                return {"ok": False, "code": "stale_base"}
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

    def _revoked_proposals_for_candidate(self, candidate_id: str) -> list[str]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT evidence_json FROM candidates WHERE candidate_id=?", (candidate_id,)
            ).fetchone()
            revoked = {
                str(value)
                for value in connection.execute("SELECT proposal_id FROM proposals WHERE status='revoked'").fetchall()
            }
        if row is None:
            return []
        try:
            evidence = json.loads(row["evidence_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            evidence = {}
        return sorted(revoked.intersection(_proposal_ids_from_evidence(evidence)))

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
        revoked = self._revoked_proposals_for_package(archive)
        if revoked:
            return {"ok": False, "code": "release_revoked", "proposal_ids": revoked}
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

    def _revoked_proposals_for_package(self, package_root: Path) -> list[str]:
        manifest_path = package_root / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []
        proposal_ids = _proposal_ids_from_evidence(manifest)
        if not proposal_ids:
            return []
        with self._connect() as connection:
            revoked = {
                str(row["proposal_id"])
                for row in connection.execute("SELECT proposal_id FROM proposals WHERE status='revoked'").fetchall()
            }
        return sorted(revoked.intersection(proposal_ids))

    def _candidate_path_for_new(self, candidate_id: str) -> Path:
        path = self.runtime_root / "candidates" / candidate_id / "package"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def _status_value(value: str) -> str:
    return value if value in {"draft", "review_required", "approved", "published", "failed", "blocked"} else "blocked"


def _proposal_ids_from_evidence(value: Any) -> set[str]:
    """Find proposal references in redacted candidate/manifest evidence."""

    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"proposal_id", "proposal_ids"}:
                if isinstance(item, str):
                    found.add(item)
                elif isinstance(item, (list, tuple, set)):
                    found.update(str(entry) for entry in item)
            found.update(_proposal_ids_from_evidence(item))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            found.update(_proposal_ids_from_evidence(item))
    return {item for item in found if item.startswith("proposal-")}


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
    materialized_learning = store.materialize_admitted_learning(candidate_path)
    if materialized_learning and bool(values.get("index_rag", False)):
        rag_result = RagSynchronizer(runtime_root=operation_options.runtime_root).sync(candidate_path)
        if not rag_result.ok:
            return {
                "ok": False,
                "code": "learning_reindex_failed",
                "candidate_id": candidate_id,
                "materialized_learning": materialized_learning,
                "error": rag_result.error,
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
        actual_id,
        status="review_required",
        revisions=revisions,
        evidence={"operation": result.to_dict(), "materialized_learning": materialized_learning},
    )
    return {
        "ok": True,
        "candidate_id": actual_id,
        "base_revisions": base_revisions,
        "revisions": revisions,
        "materialized_learning": materialized_learning,
    }


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
        if job.get("job_type") == "investigation.requested":
            result = {"ok": True, "investigation": payload, "action": "review_and_create_golden_candidate"}
            store.complete_job(job["job_id"], job["lease_id"], result)
            return {"ok": True, "worked": True, "job_id": job["job_id"], "result": result}
        if job.get("job_type") in {"skill.enrichment.requested", "source.revoked", "source.conflict"}:
            # No model or publisher lives in DOCOPS. These jobs produce a
            # reviewable hand-off (or an invalidation action) and stop before
            # touching the active package.
            action = (
                "prepare_external_enrichment_request"
                if job.get("job_type") == "skill.enrichment.requested"
                else "review_source_invalidation"
            )
            result = {"ok": True, "request": payload, "action": action}
            store.complete_job(job["job_id"], job["lease_id"], result)
            return {"ok": True, "worked": True, "job_id": job["job_id"], "result": result}
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


def work_loop(
    package_root: Path | str,
    *,
    runtime_root: Path | str | None = None,
    interval_seconds: float = 60.0,
    max_jobs: int | None = None,
) -> dict[str, Any]:
    """Run the durable worker in the foreground until stopped or bounded."""

    if interval_seconds <= 0 or (max_jobs is not None and max_jobs < 1):
        return {"ok": False, "code": "worker_loop_invalid"}
    processed: list[dict[str, Any]] = []
    while max_jobs is None or len(processed) < max_jobs:
        result = work_once(package_root, runtime_root=runtime_root)
        if result.get("worked"):
            processed.append(result)
        elif max_jobs is not None:
            break
        if max_jobs is None or len(processed) < max_jobs:
            time.sleep(interval_seconds)
    return {"ok": True, "worked": bool(processed), "processed": processed}
