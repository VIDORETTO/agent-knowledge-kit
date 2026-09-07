"""Canonical lifecycle facade over the modular DOCOPS seams.

The package generation remains the only active content store.  This module is
intentionally a thin application boundary: it owns the public lifecycle
vocabulary and the versioned runtime marker, while domain work continues to
live in :mod:`docops.operations`, :mod:`docops.source_policy` and the other
focused modules.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Mapping

from .contracts import validate_artifact
from .manifest import utc_now
from .observability import redact_report, redact_text
from .package_validator import validate_package
from .storage import write_json_atomic

LIFECYCLE_SCHEMA_VERSION = 1
RUNTIME_LAYOUT_VERSION = 1
RUNTIME_FILENAME = "runtime.json"

_LIFECYCLE_STATES = {
    "source": ("absent", "registered", "admitted", "observed", "withdrawn", "revoked"),
    "revision": ("absent", "observed", "candidate", "applied", "invalidated"),
    "signal": ("absent", "received", "coalesced", "processed", "blocked"),
    "candidate": ("absent", "draft", "review_required", "approved", "published", "rejected", "blocked", "revoked"),
    "evaluation": ("absent", "pending", "valid", "invalid", "stale"),
    "approval": ("absent", "pending", "approved", "invalidated"),
    "publication": ("absent", "staging", "published", "rolled_back", "blocked"),
    "reader": ("absent", "active", "expired", "revoked", "invalidated"),
}

_TRANSITIONS = {
    "source": {
        "absent": {"registered"},
        "registered": {"admitted", "withdrawn", "revoked"},
        "admitted": {"observed", "withdrawn", "revoked"},
        "observed": {"observed", "withdrawn", "revoked"},
        "withdrawn": {"withdrawn", "registered"},
        "revoked": {"revoked", "registered"},
    },
    "revision": {
        "absent": {"observed"},
        "observed": {"observed", "candidate", "invalidated"},
        "candidate": {"candidate", "applied", "invalidated"},
        "applied": {"applied", "candidate", "invalidated"},
        "invalidated": {"invalidated", "observed", "candidate"},
    },
    "signal": {
        "absent": {"received"},
        "received": {"received", "coalesced", "blocked"},
        "coalesced": {"coalesced", "processed", "blocked"},
        "processed": {"processed", "received"},
        "blocked": {"blocked", "received"},
    },
    "candidate": {
        "absent": {"draft"},
        "draft": {"draft", "review_required", "rejected", "blocked", "revoked"},
        "review_required": {"review_required", "approved", "rejected", "blocked", "revoked"},
        "approved": {"approved", "published", "blocked", "revoked"},
        "published": {"published", "revoked"},
        "rejected": {"rejected", "draft"},
        "blocked": {"blocked", "draft", "review_required"},
        "revoked": {"revoked"},
    },
    "evaluation": {
        "absent": {"pending"},
        "pending": {"pending", "valid", "invalid"},
        "valid": {"valid", "stale", "invalid"},
        "invalid": {"invalid", "pending"},
        "stale": {"stale", "pending"},
    },
    "approval": {
        "absent": {"pending"},
        "pending": {"pending", "approved", "invalidated"},
        "approved": {"approved", "invalidated"},
        "invalidated": {"invalidated", "pending"},
    },
    "publication": {
        "absent": {"staging"},
        "staging": {"staging", "published", "blocked"},
        "published": {"published", "rolled_back", "blocked"},
        "rolled_back": {"rolled_back", "staging", "published"},
        "blocked": {"blocked", "staging"},
    },
    "reader": {
        "absent": {"active"},
        "active": {"active", "expired", "revoked", "invalidated"},
        "expired": {"expired", "active"},
        "revoked": {"revoked"},
        "invalidated": {"invalidated", "active"},
    },
}


class LifecycleError(ValueError):
    """Closed, public error from the canonical lifecycle boundary."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class LifecycleStateMachine:
    """Validate transitions without exposing storage or implementation details."""

    states: ClassVar[Mapping[str, tuple[str, ...]]] = _LIFECYCLE_STATES

    def transition(self, entity: str, current: str, target: str) -> str:
        allowed_states = self.states.get(entity)
        if allowed_states is None or current not in allowed_states or target not in allowed_states:
            raise LifecycleError("lifecycle_state_invalid", "unknown lifecycle entity or state")
        if target not in _TRANSITIONS[entity].get(current, set()):
            raise LifecycleError("lifecycle_transition_invalid", "lifecycle transition is not allowed")
        return target

    def can_transition(self, entity: str, current: str, target: str) -> bool:
        try:
            self.transition(entity, current, target)
        except LifecycleError:
            return False
        return True


@dataclass(frozen=True)
class RuntimeState:
    """Portable runtime identity kept outside the active generation."""

    schema_version: int
    layout_version: int
    package_id: str
    status: str
    migration: str
    created_at: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "layout_version": self.layout_version,
            "package_id": self.package_id,
            "status": self.status,
            "migration": self.migration,
            "storage": "external-runtime",
        }


def runtime_directory(package_root: Path | str, runtime_root: Path | str | None = None) -> Path:
    """Resolve a runtime directory that cannot be nested in the active package."""

    package = Path(package_root).expanduser().resolve()
    if package.is_symlink():
        raise LifecycleError("unsafe_package_path", "active package must not be a symbolic link")
    runtime = (
        Path(runtime_root).expanduser().resolve()
        if runtime_root is not None
        else package.parent / f".{package.name}.docops-runtime"
    )
    if runtime == package or package in runtime.parents:
        raise LifecycleError("runtime_inside_package", "lifecycle runtime must be outside the active package")
    if runtime.is_symlink():
        raise LifecycleError("unsafe_runtime_path", "lifecycle runtime must not be a symbolic link")
    if runtime.exists() and not runtime.is_dir():
        raise LifecycleError("runtime_not_directory", "lifecycle runtime must be a directory")
    runtime.mkdir(parents=True, exist_ok=True)
    return runtime


def _package_id(package: Path) -> str:
    return f"package-{hashlib.sha256(str(package).encode('utf-8')).hexdigest()[:16]}"


def _runtime_payload(package: Path) -> dict[str, Any]:
    return {
        "schema_version": LIFECYCLE_SCHEMA_VERSION,
        "layout_version": RUNTIME_LAYOUT_VERSION,
        "package_id": _package_id(package),
        "status": "initialized",
        "migration": "none",
        "created_at": utc_now(),
    }


def _read_runtime(path: Path, package: Path, *, create: bool) -> RuntimeState:
    if path.is_symlink():
        raise LifecycleError("unsafe_runtime_state", "runtime marker must not be a symbolic link")
    if not path.exists():
        legacy_names = ("lifecycle.sqlite3", "state.sqlite3", "lifecycle.db")
        if any((path.parent / name).exists() for name in legacy_names):
            raise LifecycleError(
                "runtime_migration_required",
                "legacy lifecycle state requires an explicit migration",
            )
        if not create:
            return RuntimeState(1, 1, _package_id(package), "absent", "none", "")
        payload = _runtime_payload(package)
        write_json_atomic(path, payload)
        return RuntimeState(**payload)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LifecycleError("runtime_invalid", "runtime marker is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise LifecycleError("runtime_invalid", "runtime marker must be a JSON object")
    if payload.get("schema_version") != LIFECYCLE_SCHEMA_VERSION:
        raise LifecycleError("runtime_schema_unsupported", "runtime schema version is unsupported")
    if payload.get("layout_version") != RUNTIME_LAYOUT_VERSION:
        raise LifecycleError("runtime_layout_unsupported", "runtime layout version is unsupported")
    if payload.get("package_id") != _package_id(package):
        raise LifecycleError("runtime_package_mismatch", "runtime marker belongs to another package")
    required = ("status", "migration", "created_at")
    if any(not isinstance(payload.get(key), str) for key in required):
        raise LifecycleError("runtime_invalid", "runtime marker is incomplete")
    return RuntimeState(
        schema_version=int(payload["schema_version"]),
        layout_version=int(payload["layout_version"]),
        package_id=str(payload["package_id"]),
        status=str(payload["status"]),
        migration=str(payload["migration"]),
        created_at=str(payload["created_at"]),
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _active_summary(package: Path) -> dict[str, str]:
    manifest = _read_json(package / "manifest.json")
    if manifest is None:
        return {"active": "absent", "source": "absent", "candidate": "absent", "publication": "absent"}
    validation = validate_package(package)
    entries = manifest.get("entries")
    accepted = isinstance(entries, list) and any(
        isinstance(entry, Mapping) and entry.get("status") == "accepted" for entry in entries
    )
    metadata = package / ".docops"
    candidate = "present" if (metadata / "candidate.json").is_file() else "absent"
    publication = "published" if (metadata / "publication.json").is_file() else "absent"
    return {
        "active": "valid" if validation.ok else "invalid",
        "source": "materialized" if accepted else "absent",
        "candidate": candidate,
        "publication": publication,
    }


class LifecycleFacade:
    """Single public application facade for the modular lifecycle."""

    def __init__(self, package_root: Path | str, *, runtime_root: Path | str | None = None) -> None:
        self.package_root = Path(package_root).expanduser().resolve()
        self.runtime_root = runtime_directory(self.package_root, runtime_root)
        self._machine = LifecycleStateMachine()

    def _runtime(self) -> RuntimeState:
        return _read_runtime(self.runtime_root / RUNTIME_FILENAME, self.package_root, create=True)

    def status(self) -> dict[str, Any]:
        """Return a redacted, versioned status projection."""

        try:
            runtime = _read_runtime(self.runtime_root / RUNTIME_FILENAME, self.package_root, create=True)
        except LifecycleError as exc:
            runtime = {
                "schema_version": LIFECYCLE_SCHEMA_VERSION,
                "layout_version": RUNTIME_LAYOUT_VERSION,
                "package_id": _package_id(self.package_root),
                "status": "blocked",
                "migration": "required" if exc.code == "runtime_migration_required" else "invalid",
                "storage": "external-runtime",
            }
            payload = {
                "schema_version": LIFECYCLE_SCHEMA_VERSION,
                "ok": False,
                "code": exc.code,
                "runtime": runtime,
                "lifecycle": {
                    "active": "unknown",
                    "source": "unknown",
                    "candidate": "unknown",
                    "publication": "unknown",
                },
                "compatibility": {"cli": "expand-contract", "json": "versioned", "artifacts": "contract-first"},
                "errors": [{"code": exc.code, "message": redact_text(str(exc))}],
            }
            return redact_report(payload)

        active = _active_summary(self.package_root)
        payload = {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            "ok": True,
            "code": "lifecycle_status",
            "runtime": runtime.to_public_dict(),
            "lifecycle": {
                **active,
                "state_machine": "canonical-v1",
                "readiness": "valid" if active["active"] == "valid" else "not_ready",
            },
            "compatibility": {
                "cli": "expand-contract",
                "json": "versioned",
                "artifacts": "contract-first",
                "legacy_states": "explicit-migration",
            },
            "errors": [],
        }
        contract = validate_artifact("lifecycle-status", payload)
        if not contract.ok:
            return {
                "schema_version": LIFECYCLE_SCHEMA_VERSION,
                "ok": False,
                "code": "lifecycle_status_contract_invalid",
                "runtime": runtime.to_public_dict(),
                "lifecycle": active,
                "compatibility": {"cli": "expand-contract", "json": "versioned", "artifacts": "contract-first"},
                "errors": redact_report(contract.errors),
            }
        return redact_report(payload)

    def plan(self, source: str | Path, *, options: Any = None) -> Any:
        """Build a plan through the existing public operation seam."""

        self._runtime()
        from .operations import OperationOptions, plan

        if options is None:
            options = OperationOptions(output_dir=self.package_root)
        return plan(source, options=options)

    def apply(self, operation: Any) -> Any:
        """Apply a previously built operation through the existing seam."""

        self._runtime()
        from .operations import apply

        return apply(operation)

    def preview(self, operation: Any) -> Any:
        """Return a no-effects preview through the existing seam."""

        self._runtime()
        from .operations import preview

        return preview(operation)

    def run(self, source: str | Path, *, options: Any = None) -> Any:
        """Plan and apply one operation without creating a second lifecycle."""

        return self.apply(self.plan(source, options=options))

    def inspect(self) -> dict[str, Any]:
        """Alias for the stable status projection."""

        return self.status()


CanonicalLifecycle = LifecycleFacade
Lifecycle = LifecycleFacade


def lifecycle_status(package_root: Path | str, *, runtime_root: Path | str | None = None) -> dict[str, Any]:
    """Return the canonical status without requiring callers to hold a facade."""

    return LifecycleFacade(package_root, runtime_root=runtime_root).status()


__all__ = [
    "CanonicalLifecycle",
    "Lifecycle",
    "LifecycleError",
    "LifecycleFacade",
    "LifecycleStateMachine",
    "RuntimeState",
    "lifecycle_status",
    "runtime_directory",
]
