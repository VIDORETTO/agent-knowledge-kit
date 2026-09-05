"""Stable fingerprints for the independently versioned knowledge layers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def _hash_bytes(parts: Iterable[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest()


def _file_digest(path: Path) -> str:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return "absent"
    try:
        return _hash_bytes((path.name.encode("utf-8"), b"\0", path.read_bytes()))
    except OSError:
        return "unreadable"


def _tree_digest(root: Path) -> str:
    if not root.is_dir() or root.is_symlink():
        return "absent"
    parts: list[bytes] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        try:
            content = path.read_bytes()
        except OSError:
            content = b"<unreadable>"
        parts.extend((relative, b"\0", content, b"\0"))
    return _hash_bytes(parts)


def _combined_digest(root: Path, files: Iterable[str], directories: Iterable[str] = ()) -> str:
    parts: list[bytes] = []
    for relative in sorted(files):
        path = root / relative
        parts.extend((relative.encode("utf-8"), b"\0", _file_digest(path).encode("ascii"), b"\0"))
    for relative in sorted(directories):
        parts.extend((relative.encode("utf-8"), b"\0", _tree_digest(root / relative).encode("ascii"), b"\0"))
    return _hash_bytes(parts)


def compute_revisions(package_root: Path | str) -> dict[str, Any]:
    """Compute non-circular revisions from package content and configuration."""

    root = Path(package_root).resolve()
    corpus_revision = _combined_digest(
        root,
        ("rag/sources.json", ".docops/state.json"),
        ("rag/documents",),
    )
    index_revision = _combined_digest(root, ("rag/index.json", "config.yaml"))
    skill_revision = _tree_digest(root / "skill")
    router_revision = _tree_digest(root / "router")
    harness_revision = _file_digest(root / "harness.json")
    golden_revision = _file_digest(root / ".docops" / "evaluation.json")
    policy_revision = _file_digest(root / ".docops" / "policy.json")
    composition_payload = {
        "corpus_revision": corpus_revision,
        "index_revision": index_revision,
        "skill_revision": skill_revision,
        "router_revision": router_revision,
        "harness_revision": harness_revision,
        "golden_revision": golden_revision,
        "policy_revision": policy_revision,
    }
    composition = hashlib.sha256(
        json.dumps(composition_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        **composition_payload,
        "composition": composition,
        "release_id": f"release-{composition[:16]}",
    }
