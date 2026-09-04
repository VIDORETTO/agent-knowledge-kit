"""Redacted, bounded operational diagnostics."""

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

_SECRET_VALUE = re.compile(
    r"(?i)(\b(?:access[_-]?token|api[_-]?key|authorization|bearer|client[_-]?secret|password|private[_-]?key|secret|signature|token)\b\s*[:=]\s*)([^\s,;&?#]+)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_WINDOWS_PATH = re.compile(r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:\\|[A-Z]:/)[^\s\"']+")
_POSIX_PATH = re.compile(r"(?<![\w])/(?:Users|home|private|tmp|var|workspace)/[^\s\"']+")
_MESSAGE_KEYS = {"message", "reason", "detail", "hint", "error"}
_PATH_KEYS = {"path", "source_path", "directory", "documents_dir", "data_dir", "models_cache_dir", "cwd"}
_SOURCE_KEYS = {"source", "url", "uri", "command"}
_QUERY_KEYS = {"query"}
_CONTENT_KEYS = {"content", "text", "raw", "stdout", "stderr"}
_CORPUS_KEYS = {"corpus", "document_text", "document_content"}


def redact_text(value: Any, *, limit: int = 240) -> str:
    """Return a bounded operational message without secrets or local paths."""

    text = str(value)

    def replace_secret(match: re.Match[str]) -> str:
        replacement = match.group(2)
        if replacement.casefold() in {"redacted", "<redacted>"}:
            return match.group(0)
        return match.group(1) + "<redacted>"

    text = _SECRET_VALUE.sub(replace_secret, text)
    text = _BEARER.sub("Bearer <redacted>", text)
    text = _WINDOWS_PATH.sub("<local-path>", text)
    text = _POSIX_PATH.sub("<local-path>", text)
    if len(text) > limit:
        text = text[: max(0, limit - 3)] + "..."
    return text


def redact_diagnostic(line: str) -> dict[str, Any]:
    """Classify one untrusted diagnostic line without retaining its contents."""

    value = redact_text(line, limit=4096)
    upper = value.upper()
    if "ERROR" in upper or "EXCEPTION" in upper or "FAIL" in upper:
        code = "stderr_error"
        severity = "error"
    elif "WARN" in upper:
        code = "stderr_warning"
        severity = "warning"
    elif "TIMEOUT" in upper:
        code = "stderr_timeout"
        severity = "warning"
    else:
        code = "stderr_event"
        severity = "info"
    category = "protocol" if any(word in upper for word in ("MCP", "JSON-RPC", "STDOUT", "STDERR")) else "backend"
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "length": min(len(value), 4096),
        "redacted": True,
    }


def exception_diagnostic(exc: BaseException, *, fallback_code: str = "operation_failed") -> dict[str, Any]:
    """Classify an operational exception without retaining its message."""

    declared_code = getattr(exc, "code", None)
    code = str(declared_code) if isinstance(declared_code, str) and declared_code else fallback_code
    if isinstance(exc, TimeoutError) and not declared_code:
        code = "operation_timeout"
    event: dict[str, Any] = {
        "code": code,
        "severity": "error",
        "category": "protocol" if code.startswith("mcp_") else "operation",
        "redacted": True,
    }
    exit_code = getattr(exc, "exit_code", None)
    if isinstance(exit_code, int) and not isinstance(exit_code, bool):
        event["process_exit_code"] = exit_code
    return event


def redact_report(value: Any) -> Any:
    """Redact operational text fields while preserving report structure."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in _CONTENT_KEYS and isinstance(item, str):
                result[str(key)] = "<redacted-content>"
            elif normalized_key in _CORPUS_KEYS and isinstance(item, str):
                result[str(key)] = "<redacted-corpus>"
            elif normalized_key in _QUERY_KEYS:
                result[str(key)] = None if item is None else "<redacted-query>"
            elif normalized_key in _MESSAGE_KEYS or normalized_key in _PATH_KEYS or normalized_key in _SOURCE_KEYS:
                result[str(key)] = None if item is None else redact_text(item)
            else:
                result[str(key)] = redact_report(item)
        return result
    if isinstance(value, list):
        return [redact_report(item) for item in value]
    if isinstance(value, tuple):
        return [redact_report(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


@dataclass
class DiagnosticRecorder:
    """Bounded event window for one subprocess operation."""

    limit: int = 20
    events: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.monotonic)

    def record(self, event: dict[str, Any]) -> None:
        if len(self.events) < max(1, self.limit):
            self.events.append(dict(event))

    def record_stderr(self, line: str) -> None:
        self.record(redact_diagnostic(line))

    def snapshot(self, *, status: str = "running", process_exit_code: int | None = None) -> dict[str, Any]:
        return {
            "status": status,
            "duration_ms": round((time.monotonic() - self.started_at) * 1000, 3),
            "process_exit_code": process_exit_code,
            "events": list(self.events),
            "event_count": len(self.events),
        }
