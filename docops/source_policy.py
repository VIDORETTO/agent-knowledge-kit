"""Source registration and acquisition-snapshot policy.

The registry is deliberately small and file-backed.  A registration describes
what the operator intends to keep, while a snapshot describes what an
acquisition actually observed.  An incomplete observation can never withdraw
an active registration.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contracts import validate_artifact
from .manifest import utc_now
from .source_resolver import canonicalize_url
from .storage import write_json_atomic

REGISTRY_FILENAME = "source-registry.json"
REGISTRY_SCHEMA_VERSION = 1
_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_KINDS = {"local", "repository", "web"}
_VERSION_POLICIES = {"latest", "pinned"}
_COMPLETENESS = {"complete", "partial", "incomplete", "failed", "unknown"}


class SourcePolicyError(ValueError):
    """Raised when a source policy request cannot be accepted safely."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


def source_registry_path(package_root: Path | str) -> Path:
    """Return the registry path after checking the package metadata boundary."""

    root = Path(package_root)
    if root.is_symlink():
        raise SourcePolicyError("unsafe_package_path", "source registry package must not be a symbolic link")
    if root.exists() and not root.is_dir():
        raise SourcePolicyError("package_not_directory", "source registry package must be a directory")
    metadata = root / ".docops"
    if metadata.is_symlink():
        raise SourcePolicyError(
            "unsafe_metadata_path", "source registry metadata directory must not be a symbolic link"
        )
    if metadata.exists() and not metadata.is_dir():
        raise SourcePolicyError("metadata_not_directory", "source registry metadata path must be a directory")
    metadata.mkdir(parents=True, exist_ok=True)
    path = metadata / REGISTRY_FILENAME
    if path.is_symlink():
        raise SourcePolicyError("unsafe_registry_path", "source registry file must not be a symbolic link")
    return path


def _registry_default() -> dict[str, Any]:
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "registry_revision": "",
        "registrations": [],
        "snapshots": [],
        "withdrawals": [],
    }


def _registry_revision(registry: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in registry.items() if key not in {"registry_revision", "updated_at"}}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_registration(registration: Mapping[str, Any]) -> None:
    result = validate_artifact("source-registration", registration)
    if not result.ok:
        raise SourcePolicyError(
            "source_registration_invalid",
            "source registration violates its public contract",
            details={"errors": result.errors},
        )


def _validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    result = validate_artifact("acquisition-snapshot", snapshot)
    if not result.ok:
        raise SourcePolicyError(
            "acquisition_snapshot_invalid",
            "acquisition snapshot violates its public contract",
            details={"errors": result.errors},
        )


def _load_registry(package_root: Path | str) -> tuple[Path, dict[str, Any]]:
    path = source_registry_path(package_root)
    if not path.exists():
        return path, _registry_default()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourcePolicyError("source_registry_invalid", f"could not read source registry: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise SourcePolicyError("source_registry_invalid", "unsupported source registry schema")
    for key in ("registrations", "snapshots", "withdrawals"):
        if not isinstance(raw.get(key), list):
            raise SourcePolicyError("source_registry_invalid", f"source registry {key} must be a list")
    for registration in raw["registrations"]:
        if not isinstance(registration, Mapping):
            raise SourcePolicyError("source_registry_invalid", "source registry registrations must be objects")
        _validate_registration(registration)
    return path, dict(raw)


def _save_registry(path: Path, registry: dict[str, Any]) -> dict[str, Any]:
    registry["registry_revision"] = _registry_revision(registry)
    registry["updated_at"] = utc_now()
    write_json_atomic(path, registry)
    return registry


def _validate_source_id(source_id: str) -> str:
    value = source_id.strip()
    if not _SOURCE_ID.fullmatch(value):
        raise SourcePolicyError(
            "source_id_invalid",
            "source_id must contain only letters, numbers, dots, underscores, and hyphens",
        )
    return value


def _nonempty(value: str | None, name: str, default: str | None = None) -> str:
    normalized = (value if value is not None else default or "").strip()
    if not normalized:
        raise SourcePolicyError(f"{name}_required", f"{name} must not be empty")
    return normalized


def _registration_payload(
    *,
    source_id: str,
    canonical: str,
    kind: str,
    scope: str,
    version_policy: str,
    version: str | None,
    language: str | None,
    rights: str,
    privacy: str,
    authority: str,
    owner: str,
    registered_at: str | None = None,
) -> dict[str, Any]:
    if kind not in _KINDS:
        raise SourcePolicyError("source_kind_invalid", f"source kind must be one of {sorted(_KINDS)}")
    if version_policy not in _VERSION_POLICIES:
        raise SourcePolicyError(
            "version_policy_invalid",
            f"version policy must be one of {sorted(_VERSION_POLICIES)}",
        )
    if version_policy == "pinned" and not version:
        raise SourcePolicyError("pinned_version_required", "pinned sources require an explicit version")
    payload = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "source_id": _validate_source_id(source_id),
        "canonical": canonicalize_url(_nonempty(canonical, "canonical")),
        "kind": kind,
        "scope": _nonempty(scope, "scope", "/**"),
        "version_policy": version_policy,
        "version": version,
        "language": language.strip() if isinstance(language, str) and language.strip() else None,
        "rights": _nonempty(rights, "rights", "unknown"),
        "privacy": _nonempty(privacy, "privacy", "unknown"),
        "authority": _nonempty(authority, "authority", "operator"),
        "owner": _nonempty(owner, "owner", "local"),
        "status": "active",
        "registered_at": registered_at or utc_now(),
        "withdrawn_at": None,
        "last_observed_revision": None,
        "last_observed_version": None,
        "last_observed_at": None,
        "last_observed_entries": 0,
    }
    _validate_registration(payload)
    return payload


def register_source(
    package_root: Path | str,
    *,
    source_id: str,
    canonical: str,
    kind: str = "web",
    scope: str = "/**",
    version_policy: str = "latest",
    version: str | None = None,
    language: str | None = None,
    rights: str = "unknown",
    privacy: str = "unknown",
    authority: str = "operator",
    owner: str = "local",
    readmit: bool = False,
) -> dict[str, Any]:
    """Register/update one source, requiring explicit authorization to readmit."""

    path, registry = _load_registry(package_root)
    registration = _registration_payload(
        source_id=source_id,
        canonical=canonical,
        kind=kind,
        scope=scope,
        version_policy=version_policy,
        version=version,
        language=language,
        rights=rights,
        privacy=privacy,
        authority=authority,
        owner=owner,
    )
    registrations = list(registry["registrations"])
    existing_index = next(
        (index for index, item in enumerate(registrations) if item.get("source_id") == registration["source_id"]),
        None,
    )
    if existing_index is not None:
        existing = dict(registrations[existing_index])
        for field in ("canonical", "kind", "scope", "version_policy"):
            if existing.get(field) != registration[field]:
                raise SourcePolicyError(
                    "source_conflict",
                    f"source_id {registration['source_id']!r} is already bound to different {field}",
                )
        if existing.get("status") == "withdrawn" and not readmit:
            raise SourcePolicyError(
                "source_readmission_required",
                "a withdrawn source requires explicit readmission authorization",
            )
        if existing.get("status") == "withdrawn" and any(
            str(registration.get(field) or "").strip().casefold() in {"", "unknown", "unspecified"}
            for field in ("rights", "privacy", "authority", "owner")
        ):
            raise SourcePolicyError(
                "source_not_admitted",
                "readmission requires explicit rights, privacy, authority and owner",
            )
        registration["registered_at"] = existing.get("registered_at") or registration["registered_at"]
        registration["last_observed_revision"] = existing.get("last_observed_revision")
        registration["last_observed_version"] = existing.get("last_observed_version")
        registration["last_observed_at"] = existing.get("last_observed_at")
        registration["last_observed_entries"] = existing.get("last_observed_entries", 0)
        registration["status"] = "active"
        if existing.get("status") == "withdrawn" and readmit:
            registration["readmitted_at"] = utc_now()
            registration["readmission_reason"] = "explicit_operator_reauthorization"
        registrations[existing_index] = registration
    else:
        registrations.append(registration)
    registry["registrations"] = sorted(registrations, key=lambda item: str(item["source_id"]))
    saved = _save_registry(path, registry)
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "ok": True,
        "code": "source_registered",
        "source": registration,
        "registered_source_ids": [item["source_id"] for item in registry["registrations"]],
        "registry_revision": saved["registry_revision"],
    }


def _read_snapshot(snapshot: Mapping[str, Any] | Path | str, source_id: str | None) -> dict[str, Any]:
    if isinstance(snapshot, (Path, str)):
        try:
            raw = json.loads(Path(snapshot).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SourcePolicyError(
                "acquisition_snapshot_unreadable", f"could not read acquisition snapshot: {exc}"
            ) from exc
    else:
        raw = dict(snapshot)
    if not isinstance(raw, dict):
        raise SourcePolicyError("acquisition_snapshot_invalid", "acquisition snapshot must be an object")
    normalized = dict(raw)
    normalized.setdefault("schema_version", REGISTRY_SCHEMA_VERSION)
    if source_id and not normalized.get("source_id"):
        normalized["source_id"] = source_id
    normalized.setdefault("revision", normalized.get("observed_revision") or "unknown")
    normalized.setdefault("entries", [])
    normalized.setdefault("errors", [])
    normalized.setdefault("observation_time", utc_now())
    normalized.setdefault("completeness", "partial")
    _validate_snapshot(normalized)
    return normalized


def _snapshot_id(snapshot: Mapping[str, Any]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _policy_result(
    *,
    code: str,
    message: str,
    source_id: str,
    registry: Mapping[str, Any],
    preserved: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "ok": False,
        "code": code,
        "message": message,
        "source_id": source_id,
        "preserved": preserved,
        "registered_source_ids": [
            item["source_id"] for item in registry.get("registrations", []) if item.get("status") == "active"
        ],
        "registry_revision": registry.get("registry_revision", ""),
    }


def reconcile_source(
    package_root: Path | str,
    snapshot: Mapping[str, Any] | Path | str,
    *,
    source_id: str | None = None,
    withdraw: bool = False,
) -> dict[str, Any]:
    """Reconcile one acquisition snapshot without implicit withdrawal."""

    path, registry = _load_registry(package_root)
    normalized = _read_snapshot(snapshot, source_id)
    resolved_source_id = _validate_source_id(str(normalized["source_id"]))
    registrations = list(registry["registrations"])
    registration_index = next(
        (index for index, item in enumerate(registrations) if item.get("source_id") == resolved_source_id),
        None,
    )
    if registration_index is None:
        raise SourcePolicyError("source_not_registered", f"source_id {resolved_source_id!r} is not registered")
    registration = dict(registrations[registration_index])
    if registration["status"] == "withdrawn":
        raise SourcePolicyError("source_withdrawn", f"source_id {resolved_source_id!r} is already withdrawn")
    missing_policy = [
        field
        for field in ("rights", "privacy", "authority", "owner")
        if str(registration.get(field) or "").strip().casefold() in {"", "unknown", "unspecified"}
    ]
    if missing_policy:
        result = _policy_result(
            code="source_not_admitted",
            message="source reconciliation requires explicit rights, privacy, authority and owner",
            source_id=resolved_source_id,
            registry=registry,
        )
        result["missing_policy"] = missing_policy
        return result
    if normalized["scope"] != registration["scope"]:
        return _policy_result(
            code="scope_mismatch",
            message="acquisition snapshot scope does not match the registered scope",
            source_id=resolved_source_id,
            registry=registry,
        )

    observation = dict(normalized)
    observation["snapshot_id"] = _snapshot_id(normalized)
    observation["reconciled_at"] = utc_now()
    completeness = str(normalized["completeness"])
    if completeness != "complete":
        observation["decision"] = "preserved_incomplete"
        registry["snapshots"].append(observation)
        saved = _save_registry(path, registry)
        result = _policy_result(
            code="acquisition_incomplete",
            message="incomplete acquisition cannot remove or withdraw a registered source",
            source_id=resolved_source_id,
            registry=saved,
        )
        result["registry_revision"] = saved["registry_revision"]
        return result

    observed_version = normalized.get("version")
    if (
        registration["version_policy"] == "pinned"
        and observed_version is not None
        and observed_version != registration.get("version")
    ):
        observation["decision"] = "preserved_pinned"
        registry["snapshots"].append(observation)
        saved = _save_registry(path, registry)
        result = _policy_result(
            code="version_pinned",
            message="snapshot version differs from the registered pinned version",
            source_id=resolved_source_id,
            registry=saved,
        )
        result["registry_revision"] = saved["registry_revision"]
        return result

    entries = normalized["entries"]
    if not entries and not withdraw:
        observation["decision"] = "preserved_withdrawal_confirmation_required"
        registry["snapshots"].append(observation)
        saved = _save_registry(path, registry)
        result = _policy_result(
            code="withdrawal_confirmation_required",
            message="an empty complete snapshot requires explicit withdrawal authorization",
            source_id=resolved_source_id,
            registry=saved,
        )
        result["registry_revision"] = saved["registry_revision"]
        return result

    registration["last_observed_revision"] = normalized["revision"]
    registration["last_observed_version"] = observed_version
    registration["last_observed_at"] = normalized["observation_time"]
    registration["last_observed_entries"] = len(entries)
    if registration["version_policy"] == "latest" and observed_version:
        registration["version"] = observed_version
    if withdraw:
        registration["status"] = "withdrawn"
        registration["withdrawn_at"] = utc_now()
        observation["decision"] = "withdrawn_explicitly"
        registry["withdrawals"].append(
            {
                "schema_version": REGISTRY_SCHEMA_VERSION,
                "source_id": resolved_source_id,
                "revision": normalized["revision"],
                "scope": normalized["scope"],
                "withdrawn_at": registration["withdrawn_at"],
                "reason": "explicit_operator_request",
            }
        )
    else:
        observation["decision"] = "reconciled"
    registrations[registration_index] = registration
    registry["registrations"] = sorted(registrations, key=lambda item: str(item["source_id"]))
    registry["snapshots"].append(observation)
    saved = _save_registry(path, registry)
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "ok": True,
        "code": "source_withdrawn" if withdraw else "source_reconciled",
        "source_id": resolved_source_id,
        "preserved": not withdraw,
        "withdrawn": withdraw,
        "registered_source_ids": [
            item["source_id"] for item in saved["registrations"] if item.get("status") == "active"
        ],
        "registry_revision": saved["registry_revision"],
        "snapshot_id": observation["snapshot_id"],
    }


def read_source_registry(package_root: Path | str) -> dict[str, Any]:
    """Read the registry through the same validation boundary as mutations."""

    _, registry = _load_registry(package_root)
    registry.setdefault("registry_revision", _registry_revision(registry))
    return registry


def withdrawal_authorized(package_root: Path | str, canonical: str) -> bool:
    """Return whether an empty complete snapshot explicitly withdrew a source."""

    registry = read_source_registry(package_root)
    normalized = canonicalize_url(canonical)
    for registration in registry["registrations"]:
        if registration.get("canonical") == normalized and registration.get("status") == "withdrawn":
            return True
    return False


__all__ = [
    "REGISTRY_FILENAME",
    "SourcePolicyError",
    "read_source_registry",
    "reconcile_source",
    "register_source",
    "source_registry_path",
    "withdrawal_authorized",
]
