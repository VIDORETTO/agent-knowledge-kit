"""Safe, non-active storage for reviewable package candidates."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .contracts import validate_artifact
from .manifest import utc_now
from .observability import redact_report
from .package_validator import validate_package
from .readiness import assess_readiness, record_skill_enrichment
from .revisions import package_revisions, tree_hash
from .storage import write_json_atomic

CANDIDATE_SCHEMA_VERSION = 1
_CANDIDATE_ID = re.compile(r"^candidate-[0-9a-f]{32}$")


class CandidateError(ValueError):
    """Raised when candidate storage is missing, unsafe or malformed."""


class EnrichmentError(CandidateError):
    """Raised when an external enrichment hand-off cannot be accepted."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def candidate_root(output: Path | str) -> Path:
    """Return the private sibling directory that stores candidates for output."""

    output_path = Path(output)
    if not output_path.name or output_path.name in {".", ".."}:
        raise CandidateError("output directory must have a stable name for candidate storage")
    return output_path.parent / f".{output_path.name}.candidates"


def candidate_locator(output: Path | str, candidate_id: str) -> str:
    """Return a path relative to the output parent, without exposing its prefix."""

    _validate_candidate_id(candidate_id)
    return f".{Path(output).name}.candidates/{candidate_id}"


def _validate_candidate_id(candidate_id: str) -> None:
    if not isinstance(candidate_id, str) or _CANDIDATE_ID.fullmatch(candidate_id) is None:
        raise CandidateError("candidate id must be a generated candidate identifier")


def _ensure_candidate_root(output: Path | str) -> Path:
    root = candidate_root(output)
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise CandidateError("candidate storage root must be a regular directory")
    root.mkdir(parents=True, exist_ok=True)
    return root


def new_candidate_id() -> str:
    return f"candidate-{uuid.uuid4().hex}"


def finalize_candidate(
    output: Path | str,
    stage: Path,
    *,
    base_manifest: Mapping[str, Any] | None,
    plan_hash: str,
    manifest: Mapping[str, Any],
) -> tuple[str, Path, dict[str, Any]]:
    """Attach an exact base/hash receipt to a validated stage and move it aside."""

    if stage.is_symlink() or not stage.is_dir():
        raise CandidateError("candidate stage must be a regular directory")
    metadata_dir = stage / ".docops"
    if metadata_dir.is_symlink() or not metadata_dir.is_dir():
        raise CandidateError("candidate stage metadata must be a regular directory")

    root = _ensure_candidate_root(output)
    candidate_id = new_candidate_id()
    target = root / candidate_id
    if target.exists() or target.is_symlink():
        raise CandidateError("generated candidate identifier already exists")

    base_revisions = base_manifest.get("revisions", {}) if isinstance(base_manifest, Mapping) else {}
    candidate_revisions = manifest.get("revisions", {})
    if not isinstance(base_revisions, Mapping):
        base_revisions = {}
    if not isinstance(candidate_revisions, Mapping):
        raise CandidateError("candidate manifest has no revision evidence")
    required_revisions = (
        "corpus_revision",
        "index_revision",
        "skill_revision",
        "router_revision",
        "policy_revision",
        "golden_revision",
        "composition_hash",
        "release_id",
    )
    if any(not isinstance(candidate_revisions.get(key), str) for key in required_revisions):
        raise CandidateError("candidate manifest has incomplete revision evidence")

    receipt = {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "status": "review_required",
        "created_at": utc_now(),
        "plan_hash": str(plan_hash),
        "base_release_id": base_revisions.get("release_id"),
        "base_composition_hash": base_revisions.get("composition_hash"),
        "revisions": {key: candidate_revisions[key] for key in required_revisions},
        "locator": candidate_locator(output, candidate_id),
    }
    write_json_atomic(metadata_dir / "candidate.json", receipt)
    os.replace(stage, target)
    return candidate_id, target, receipt


def list_candidates(output: Path | str) -> list[dict[str, Any]]:
    """List candidate receipts and reject arbitrary filesystem entries visibly."""

    root = candidate_root(output)
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        return [
            {
                "schema_version": CANDIDATE_SCHEMA_VERSION,
                "status": "rejected",
                "code": "unsafe_candidate_path",
                "message": "candidate storage root must be a regular directory",
            }
        ]

    reports: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if _CANDIDATE_ID.fullmatch(entry.name) is None:
            reports.append(
                {
                    "schema_version": CANDIDATE_SCHEMA_VERSION,
                    "candidate_id": entry.name,
                    "status": "rejected",
                    "code": "unsafe_candidate_path",
                    "message": "candidate entry name is not generated by DOCOPS",
                }
            )
            continue
        if entry.is_symlink() or not entry.is_dir():
            reports.append(
                {
                    "schema_version": CANDIDATE_SCHEMA_VERSION,
                    "candidate_id": entry.name,
                    "status": "rejected",
                    "code": "unsafe_candidate_path",
                    "message": "candidate entry must be a regular directory",
                }
            )
            continue
        receipt_path = entry / ".docops" / "candidate.json"
        if receipt_path.is_symlink() or not receipt_path.is_file():
            reports.append(
                {
                    "schema_version": CANDIDATE_SCHEMA_VERSION,
                    "candidate_id": entry.name,
                    "status": "rejected",
                    "code": "candidate_receipt_missing",
                    "message": "candidate receipt is missing or unsafe",
                }
            )
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            receipt = None
        if not isinstance(receipt, dict) or receipt.get("candidate_id") != entry.name:
            reports.append(
                {
                    "schema_version": CANDIDATE_SCHEMA_VERSION,
                    "candidate_id": entry.name,
                    "status": "rejected",
                    "code": "candidate_receipt_invalid",
                    "message": "candidate receipt does not identify its directory",
                }
            )
            continue
        reports.append(dict(receipt))
    return reports


def candidate_path(output: Path | str, candidate_id: str) -> Path:
    """Resolve a generated candidate id inside its private storage root."""

    _validate_candidate_id(candidate_id)
    root = candidate_root(output)
    path = root / candidate_id
    if path.parent != root:
        raise CandidateError("candidate path escaped its storage root")
    return path


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ENRICHMENT_ROOTS = {"skill", "router"}
_SENSITIVE_KEYS = (
    "access_token",
    "api_key",
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "signature",
    "token",
)


def _enrichment_error(code: str, message: str) -> EnrichmentError:
    return EnrichmentError(code, message)


def _read_regular_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _enrichment_error("enrichment_path_unsafe", f"{label} must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _enrichment_error("enrichment_receipt_invalid", f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise _enrichment_error("enrichment_receipt_invalid", f"{label} must be a JSON object")
    return value


def _raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _path_is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise _enrichment_error("enrichment_path_unsafe", "candidate must not be a symbolic link")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise _enrichment_error(
                "enrichment_path_unsafe",
                f"candidate contains a symbolic link at {path.relative_to(root).as_posix()}",
            )


def _safe_relative_artifact(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _enrichment_error("enrichment_scope_rejected", "artifact path must be a non-empty string")
    if "\\" in value:
        raise _enrichment_error("enrichment_scope_rejected", "artifact paths must use POSIX separators")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise _enrichment_error("enrichment_scope_rejected", "artifact path must remain relative")
    if not path.parts or path.parts[0] not in _ENRICHMENT_ROOTS or len(path.parts) < 2:
        raise _enrichment_error("enrichment_scope_rejected", "artifact path is outside the enrichment scope")
    return path.as_posix()


def _validate_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise _enrichment_error("enrichment_hash_mismatch", f"{label} must be a lowercase SHA-256 hash")
    return value


def _reject_sensitive_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if any(marker in normalized for marker in _SENSITIVE_KEYS):
                raise _enrichment_error(
                    "enrichment_private_data", f"receipt contains a credential-like field at {path}"
                )
            _reject_sensitive_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_sensitive_keys(item, f"{path}[{index}]")


def _entries_by_path(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, list) or not value:
        raise _enrichment_error("enrichment_receipt_invalid", f"{label} must be a non-empty list")
    result: dict[str, str] = {}
    for entry in value:
        if not isinstance(entry, Mapping):
            raise _enrichment_error("enrichment_receipt_invalid", f"{label} entries must be objects")
        path = str(entry.get("path", ""))
        if path in result:
            raise _enrichment_error("enrichment_receipt_invalid", f"{label} contains a duplicate path")
        result[path] = _validate_hash(entry.get("sha256"), f"{label}.{path}.sha256")
    return result


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink(missing_ok=True)


def _snapshot_files(paths: list[Path]) -> dict[Path, bytes | None]:
    snapshot: dict[Path, bytes | None] = {}
    for path in paths:
        if path.exists() and not path.is_symlink():
            snapshot[path] = path.read_bytes()
        else:
            snapshot[path] = None
    return snapshot


def _restore_files(snapshot: Mapping[Path, bytes | None]) -> None:
    for path, data in snapshot.items():
        if data is None:
            if path.exists() and not path.is_dir():
                path.unlink(missing_ok=True)
            continue
        _write_bytes_atomic(path, data)


def submit_enrichment(
    package_root: Path | str,
    candidate_id: str,
    source_dir: Path | str,
    receipt_path: Path | str,
) -> dict[str, Any]:
    """Verify and import an external enrichment result into one candidate only."""

    root = candidate_path(package_root, candidate_id)
    if root.is_symlink() or not root.is_dir():
        raise _enrichment_error("enrichment_path_unsafe", "candidate must be a regular directory")
    source_root = Path(source_dir)
    if source_root.is_symlink() or not source_root.is_dir():
        raise _enrichment_error("enrichment_path_unsafe", "external output root must be a regular directory")
    _reject_symlinks(root)
    _reject_symlinks(source_root)

    candidate_receipt_path = root / ".docops" / "candidate.json"
    candidate_receipt = _read_regular_json(candidate_receipt_path, "candidate receipt")
    request = _read_regular_json(root / ".docops" / "enrichment-request.json", "enrichment request")
    receipt = _read_regular_json(Path(receipt_path), "enrichment receipt")
    _reject_sensitive_keys(receipt)

    request_contract = validate_artifact("enrichment-request", request)
    if not request_contract.ok:
        raise _enrichment_error("enrichment_request_invalid", "enrichment request violates its contract")
    receipt_contract = validate_artifact("enrichment-receipt", receipt)
    if not receipt_contract.ok:
        raise _enrichment_error("enrichment_receipt_invalid", "enrichment receipt violates its contract")
    if request.get("candidate_id") != candidate_id or receipt.get("candidate_id") != candidate_id:
        raise _enrichment_error("enrichment_request_mismatch", "candidate id does not match the hand-off")
    if receipt.get("request_id") != request.get("request_id"):
        raise _enrichment_error("enrichment_request_mismatch", "receipt request id does not match the exported task")
    if candidate_receipt.get("base_release_id") != request.get("base_release_id") or receipt.get(
        "base_release_id"
    ) != request.get("base_release_id"):
        raise _enrichment_error("enrichment_base_mismatch", "base release does not match the candidate")
    if candidate_receipt.get("base_composition_hash") != request.get("base_composition_hash") or receipt.get(
        "base_composition_hash"
    ) != request.get("base_composition_hash"):
        raise _enrichment_error("enrichment_base_mismatch", "base composition does not match the candidate")

    revisions = package_revisions(
        root,
        golden_revision=str(candidate_receipt.get("revisions", {}).get("golden_revision", "unknown")),
    )
    snapshot = request.get("snapshot")
    snapshot_revisions = snapshot.get("candidate_revisions") if isinstance(snapshot, Mapping) else None
    input_hashes = snapshot.get("input_hashes") if isinstance(snapshot, Mapping) else None
    if not isinstance(snapshot_revisions, Mapping) or not isinstance(input_hashes, Mapping):
        raise _enrichment_error("enrichment_request_invalid", "enrichment request snapshot is incomplete")
    if revisions.get("composition_hash") != snapshot_revisions.get("composition_hash"):
        raise _enrichment_error("enrichment_request_stale", "candidate changed after the task was exported")
    if receipt.get("candidate_composition_hash") != revisions.get("composition_hash"):
        raise _enrichment_error("enrichment_base_mismatch", "receipt input composition does not match the candidate")
    current_inputs = {
        "skill": tree_hash(root / "skill"),
        "router": tree_hash(root / "router"),
    }
    if dict(input_hashes) != current_inputs:
        raise _enrichment_error("enrichment_request_stale", "candidate input hashes changed after export")
    if receipt.get("inputs") is None:
        raise _enrichment_error("enrichment_receipt_invalid", "receipt has no input hashes")
    if _entries_by_path(receipt.get("inputs"), "inputs") != current_inputs:
        raise _enrichment_error("enrichment_input_mismatch", "receipt input hashes do not match the task")
    if receipt.get("validation", {}).get("ok") is not True:
        raise _enrichment_error("enrichment_validation_failed", "external receipt did not validate the output")

    output_hashes = _entries_by_path(receipt.get("outputs"), "outputs")
    normalized_outputs: dict[str, str] = {}
    prepared: list[tuple[str, bytes]] = []
    total_bytes = 0
    for raw_path, expected_hash in output_hashes.items():
        relative = _safe_relative_artifact(raw_path)
        if relative in normalized_outputs:
            raise _enrichment_error("enrichment_receipt_invalid", "receipt contains duplicate output paths")
        source_path = source_root / Path(*PurePosixPath(relative).parts)
        if not _path_is_within(source_root, source_path) or source_path.is_symlink() or not source_path.is_file():
            raise _enrichment_error("enrichment_path_unsafe", f"external output is missing or unsafe: {relative}")
        data = source_path.read_bytes()
        actual_hash = _raw_sha256(source_path)
        if actual_hash != expected_hash:
            raise _enrichment_error("enrichment_hash_mismatch", f"output hash does not match: {relative}")
        normalized_outputs[relative] = expected_hash
        prepared.append((relative, data))
        total_bytes += len(data)

    if "skill/SKILL.md" not in normalized_outputs:
        raise _enrichment_error("enrichment_scope_rejected", "conceptual enrichment must include skill/SKILL.md")
    budget = request.get("budget")
    if isinstance(budget, Mapping):
        max_files = budget.get("max_files")
        max_bytes = budget.get("max_bytes")
        if isinstance(max_files, int) and len(prepared) > max_files:
            raise _enrichment_error("enrichment_budget_exceeded", "external output contains too many files")
        if isinstance(max_bytes, int) and total_bytes > max_bytes:
            raise _enrichment_error("enrichment_budget_exceeded", "external output exceeds the byte budget")

    tool = receipt.get("tool")
    if (
        not isinstance(tool, Mapping)
        or not str(tool.get("name", "")).strip()
        or not str(tool.get("version", "")).strip()
    ):
        raise _enrichment_error("enrichment_receipt_invalid", "receipt tool name and version are required")

    with tempfile.TemporaryDirectory(prefix=f".{candidate_id}.enrichment-", dir=root.parent) as temporary:
        sandbox = Path(temporary) / candidate_id
        shutil.copytree(root, sandbox, symlinks=False)
        for relative, data in prepared:
            _write_bytes_atomic(sandbox / Path(*PurePosixPath(relative).parts), data)
        sandbox_manifest_path = sandbox / "manifest.json"
        sandbox_manifest = _read_regular_json(sandbox_manifest_path, "candidate manifest")
        declared_revisions = sandbox_manifest.get("revisions")
        golden_revision = (
            declared_revisions.get("golden_revision")
            if isinstance(declared_revisions, Mapping) and isinstance(declared_revisions.get("golden_revision"), str)
            else None
        )
        sandbox_manifest["revisions"] = package_revisions(sandbox, golden_revision=golden_revision)
        sandbox_manifest["readiness"] = assess_readiness(sandbox)
        write_json_atomic(sandbox_manifest_path, sandbox_manifest)
        validation_before = validate_package(sandbox)
        if not validation_before.ok:
            codes = sorted(
                {
                    str(error.get("code", "validation_error"))
                    for error in validation_before.errors
                    if isinstance(error, Mapping)
                }
            )
            suffix = f": {', '.join(codes)}" if codes else ""
            raise _enrichment_error(
                "enrichment_validation_failed",
                f"candidate validation rejected external output{suffix}",
            )
        record_skill_enrichment(
            sandbox,
            tool=str(tool["name"]),
            version=str(tool["version"]),
            validated=True,
            provenance=redact_report(dict(receipt.get("provenance", {}))),
            artifacts=sorted(normalized_outputs),
        )
        validation_after = validate_package(sandbox)
        if not validation_after.ok:
            codes = sorted(
                {
                    str(error.get("code", "validation_error"))
                    for error in validation_after.errors
                    if isinstance(error, Mapping)
                }
            )
            suffix = f": {', '.join(codes)}" if codes else ""
            raise _enrichment_error(
                "enrichment_validation_failed",
                f"enrichment evidence invalidated candidate validation{suffix}",
            )

        resulting_manifest = _read_regular_json(sandbox / "manifest.json", "enriched candidate manifest")
        resulting_revisions = resulting_manifest.get("revisions")
        if not isinstance(resulting_revisions, Mapping):
            raise _enrichment_error("enrichment_validation_failed", "enriched candidate has no revision evidence")
        internal_receipt = {
            "schema_version": 1,
            "request_id": request["request_id"],
            "candidate_id": candidate_id,
            "base_release_id": request["base_release_id"],
            "base_composition_hash": request["base_composition_hash"],
            "candidate_composition_hash": revisions["composition_hash"],
            "tool": {"name": str(tool["name"]), "version": str(tool["version"])},
            "inputs": [{"path": path, "sha256": value} for path, value in sorted(current_inputs.items())],
            "outputs": [{"path": path, "sha256": value} for path, value in sorted(normalized_outputs.items())],
            "validation": {"ok": True, "package": "passed"},
            "provenance": redact_report(dict(receipt.get("provenance", {}))),
        }
        write_json_atomic(sandbox / ".docops" / "enrichment-receipt.json", internal_receipt)
        updated_candidate_receipt = dict(candidate_receipt)
        updated_candidate_receipt.update(
            {
                "status": "review_required",
                "enrichment_status": "received",
                "enrichment_request_id": request["request_id"],
                "enrichment_receipt": ".docops/enrichment-receipt.json",
                "revisions": dict(resulting_revisions),
            }
        )

        commit_paths = [root / Path(*PurePosixPath(relative).parts) for relative in sorted(normalized_outputs)] + [
            root / "manifest.json",
            root / ".docops" / "skill-enrichment.json",
            root / ".docops" / "enrichment-receipt.json",
            candidate_receipt_path,
        ]
        snapshot_files = _snapshot_files(commit_paths)
        try:
            for relative in sorted(normalized_outputs):
                destination = root / Path(*PurePosixPath(relative).parts)
                if not _path_is_within(root, destination):
                    raise _enrichment_error("enrichment_scope_rejected", "destination escaped candidate")
                _write_bytes_atomic(destination, (sandbox / Path(*PurePosixPath(relative).parts)).read_bytes())
            for relative in (
                "manifest.json",
                ".docops/skill-enrichment.json",
                ".docops/enrichment-receipt.json",
            ):
                _write_bytes_atomic(root / Path(*PurePosixPath(relative).parts), (sandbox / relative).read_bytes())
            write_json_atomic(candidate_receipt_path, updated_candidate_receipt)
        except Exception:
            _restore_files(snapshot_files)
            raise

    return {
        "schema_version": 1,
        "ok": True,
        "status": "candidate_received",
        "code": "enrichment_received",
        "candidate_id": candidate_id,
        "request_id": request["request_id"],
        "candidate_locator": candidate_locator(package_root, candidate_id),
        "published": False,
        "artifacts": sorted(normalized_outputs),
        "revisions": dict(resulting_revisions),
    }
