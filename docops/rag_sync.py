"""Optional integration with the user's local knowledge-rag MCP server."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config_audit import audit_config_file
from .mcp_client import first_json_payload, start_mcp_server
from .runtime import discover_rag_python, runtime_environment
from .storage import write_text_atomic


def package_rag_config() -> dict[str, Any]:
    """Return a package-local, stdio-only knowledge-rag configuration."""

    return {
        "paths": {
            "documents_dir": "./rag/documents",
            "data_dir": "./rag/data",
            "models_cache_dir": "./rag/models_cache",
        },
        "documents": {
            "supported_formats": [".md", ".txt", ".json", ".yaml", ".yml", ".rst", ".adoc"],
            "exclude_patterns": ["data", "models_cache", ".venv", ".git"],
            "chunking": {"chunk_size": 1000, "chunk_overlap": 200},
        },
        "models": {"embedding": {"profile": "compact", "gpu": False}, "reranker": {"enabled": False}},
        "search": {"default_results": 5, "max_results": 100, "collection_name": "knowledge_base"},
        "category_mappings": {},
        "keyword_routes": {},
        "query_expansions": {},
        "server": {
            "transport": "stdio",
            "host": "127.0.0.1",
            "port": 8179,
            "auth": {"bearer_token": ""},
            "rate_limit": {"enabled": False, "requests_per_minute": 60, "burst": 10},
            "metrics": {"enabled": False, "port": 9179},
            "logging": {"format": "text", "level": "INFO"},
        },
    }


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text or any(character in text for character in ":#{}[]&,*!|>'\"%@`\n") or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text


def _render_yaml(value: Any, indent: int = 0) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_render_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_render_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
    return lines


@dataclass
class RagSyncResult:
    ok: bool
    stats: dict[str, Any] = field(default_factory=dict)
    reindex: dict[str, Any] = field(default_factory=dict)
    smoke: dict[str, Any] = field(default_factory=dict)
    error: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "stats": self.stats, "reindex": self.reindex, "smoke": self.smoke, "error": self.error}


class RagSynchronizer:
    """Run the real knowledge-rag MCP reindex only when explicitly requested."""

    def __init__(self, *, python: Path | str | None = None, runtime_root: Path | str | None = None, timeout_seconds: float = 1800.0) -> None:
        self.python = Path(python) if python else None
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else None
        self.timeout_seconds = timeout_seconds

    def sync(self, package_root: Path | str, *, full_rebuild: bool = False) -> RagSyncResult:
        root = Path(package_root).resolve()
        config_path = root / "config.yaml"
        if not config_path.exists():
            write_text_atomic(config_path, "\n".join(_render_yaml(package_rag_config())) + "\n")
        config_audit = audit_config_file(config_path)
        if not config_audit.ok:
            return RagSyncResult(False, error={"code": "unsafe_rag_config", "message": "; ".join(error["message"] for error in config_audit.errors)})
        executable = self.python or discover_rag_python(self.runtime_root or root).path
        if not executable.is_file():
            return RagSyncResult(False, error={"code": "rag_python_missing", "message": str(executable)})
        client = None
        try:
            client = start_mcp_server(executable, root, env=runtime_environment(root))
            arguments = {"full_rebuild": True} if full_rebuild else {"force": True}
            response = client.call("tools/call", name="reindex_documents", arguments=arguments, timeout=self.timeout_seconds)
            if response.get("error"):
                return RagSyncResult(False, error={"code": "rag_reindex_failed", "message": str(response["error"])})
            reindex = first_json_payload(response) or {}
            deadline = time.monotonic() + self.timeout_seconds
            while time.monotonic() < deadline:
                status_response = client.call("tools/call", name="get_reindex_status", arguments={}, timeout=120)
                status = first_json_payload(status_response) or {}
                state = status.get("reindex") if isinstance(status.get("reindex"), dict) else status
                if not state.get("active", False):
                    reindex = state
                    break
                time.sleep(1)
            else:
                return RagSyncResult(False, reindex=reindex, error={"code": "rag_timeout", "message": "reindex timeout"})
            stats_response = client.call("tools/call", name="get_index_stats", arguments={}, timeout=120)
            stats = first_json_payload(stats_response) or {}
            if isinstance(stats.get("stats"), dict):
                stats = stats["stats"]
            smoke_response = client.call(
                "tools/call",
                name="search_knowledge",
                arguments={"query": "documentation", "max_results": 1},
                timeout=120,
            )
            smoke = first_json_payload(smoke_response) or {}
            if smoke_response.get("error"):
                return RagSyncResult(
                    False,
                    stats=stats,
                    reindex=reindex,
                    smoke={"ok": False},
                    error={"code": "rag_smoke_failed", "message": str(smoke_response["error"])},
                )
            return RagSyncResult(
                True,
                stats=stats,
                reindex=reindex,
                smoke={"ok": True, "result_count": len(smoke.get("results") or [])},
            )
        except (OSError, RuntimeError, TimeoutError) as exc:
            return RagSyncResult(False, error={"code": "rag_integration_failed", "message": str(exc)})
        finally:
            if client is not None:
                client.close()
