"""Deterministic content identities used by editorial evidence and releases."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

REVISION_SCHEMA_VERSION = 1
_VOLATILE_KEYS = {
    "attempt_id",
    "completed_at",
    "created_at",
    "duration_ms",
    "finished_at",
    "recorded_at",
    "started_at",
    "timestamp",
    "updated_at",
}


def canonical_json(value: Any) -> str:
    """Serialize a JSON value independently of key or whitespace ordering."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    """Hash a JSON-compatible value using the documented canonical encoding."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_hash(path: Path | str) -> str:
    """Hash file bytes or a link target without following a link silently."""

    candidate = Path(path)
    digest = hashlib.sha256()
    try:
        if candidate.is_symlink():
            digest.update(b"symlink:")
            digest.update(os.readlink(candidate).encode("utf-8", errors="replace"))
        elif candidate.is_file():
            digest.update(b"file:")
            digest.update(candidate.read_bytes())
        else:
            digest.update(b"missing")
    except OSError:
        digest.update(b"unreadable")
    return digest.hexdigest()


def tree_hash(root: Path | str) -> str:
    """Hash a tree by relative POSIX path and content, including additions/removals."""

    candidate = Path(root)
    entries: list[tuple[str, str]] = []
    if candidate.is_symlink():
        entries.append(("<root>", file_hash(candidate)))
    elif candidate.is_dir():
        try:
            for path in sorted(candidate.rglob("*")):
                if path.is_dir() and not path.is_symlink():
                    continue
                entries.append((path.relative_to(candidate).as_posix(), file_hash(path)))
        except OSError:
            entries.append(("<unreadable>", "unreadable"))
    else:
        entries.append(("<missing>", "missing"))
    return content_hash(entries)


def _without_volatile(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _without_volatile(item)
            for key, item in value.items()
            if str(key).casefold() not in _VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_without_volatile(item) for item in value]
    if isinstance(value, tuple):
        return [_without_volatile(item) for item in value]
    return value


def _json_file_projection(path: Path) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"file_hash": file_hash(path)}
    return _without_volatile(value)


def _golden_hash(golden: Mapping[str, Any] | None, override: str | None) -> str:
    if override:
        return override
    if golden is None:
        return "unknown"
    return content_hash(_without_volatile(golden))


def package_revisions(
    package_root: Path | str,
    *,
    golden: Mapping[str, Any] | None = None,
    golden_revision: str | None = None,
) -> dict[str, str | int]:
    """Return hashes for every composition layer without timestamps or IDs."""

    root = Path(package_root)
    corpus_payload = {
        "documents": tree_hash(root / "rag" / "documents"),
        "sources": file_hash(root / "rag" / "sources.json"),
    }
    index_payload = {
        "index": _json_file_projection(root / "rag" / "index.json"),
        "data": tree_hash(root / "rag" / "data") if (root / "rag" / "data").exists() else "absent",
    }
    revisions: dict[str, str | int] = {
        "schema_version": REVISION_SCHEMA_VERSION,
        "corpus_revision": content_hash(corpus_payload),
        "index_revision": content_hash(index_payload),
        "skill_revision": tree_hash(root / "skill"),
        "router_revision": tree_hash(root / "router"),
        "policy_revision": file_hash(root / ".docops" / "policy.json")
        if (root / ".docops" / "policy.json").exists()
        else "default-policy-v1",
        "golden_revision": _golden_hash(golden, golden_revision),
    }
    composition = {key: value for key, value in revisions.items() if key != "schema_version"}
    revisions["composition_hash"] = content_hash(composition)
    revisions["release_id"] = f"release-{str(revisions['composition_hash'])[:24]}"
    return revisions


def evidence_matches_package(package_root: Path | str, evidence: Mapping[str, Any]) -> tuple[bool, str]:
    """Compare persisted revision evidence with the current package bytes."""

    recorded = evidence.get("revisions")
    if not isinstance(recorded, Mapping):
        return False, "incomplete"
    required = {
        "corpus_revision",
        "index_revision",
        "skill_revision",
        "router_revision",
        "policy_revision",
        "golden_revision",
        "composition_hash",
        "release_id",
    }
    if any(not isinstance(recorded.get(key), str) or not recorded.get(key) for key in required):
        return False, "incomplete"
    current = package_revisions(package_root, golden_revision=str(recorded["golden_revision"]))
    if any(current.get(key) != recorded.get(key) for key in required):
        return False, "invalidated"
    return True, "valid"
