"""Portable hand-off metadata for external Agent Skills/MCP harnesses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import validate_artifact
from .storage import write_json_atomic


def build_harness_manifest(package_root: Path | str) -> dict[str, Any]:
    """Describe how a harness can load artifacts without author paths."""

    root = Path(package_root).resolve()
    payload = {
        "schema_version": 1,
        "package_root": ".",
        "skills": ["skill", "router"],
        "mcp": {
            "name": "knowledge-rag",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "mcp_server.server"],
            "cwd": ".",
            "env": {
                "KNOWLEDGE_RAG_DIR": ".",
                "KNOWLEDGE_RAG_WATCHER_DISABLED": "1",
                "KNOWLEDGE_RAG_READ_ONLY": "1",
            },
            "config": "config.yaml",
        },
        "notes": [
            "Resolve command=python through the clone's prepared environment on the target machine.",
            "Copy or mount skill/ and router/ into the harness skill directory; the package never selects a model.",
            f"Generated for package basename {root.name!r}; no absolute path is persisted.",
        ],
    }
    contract = validate_artifact("harness", payload)
    if not contract.ok:
        details = "; ".join(f"{error.get('path', '$')}: {error['message']}" for error in contract.errors)
        raise RuntimeError(f"generated harness contract is invalid: {details}")
    return payload


def write_harness_manifest(package_root: Path | str) -> Path:
    """Write the portable hand-off file and return its path."""

    root = Path(package_root).resolve()
    path = root / "harness.json"
    write_json_atomic(path, build_harness_manifest(root))
    return path


def read_harness_manifest(path: Path | str) -> dict[str, Any]:
    """Read and minimally validate a hand-off file."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    contract = validate_artifact("harness", value)
    if not contract.ok:
        details = "; ".join(f"{error.get('path', '$')}: {error['message']}" for error in contract.errors)
        raise ValueError(f"invalid harness contract: {details}")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("unsupported harness manifest")
    return value
