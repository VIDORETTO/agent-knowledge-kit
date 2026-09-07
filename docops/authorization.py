"""Persisted authorization records for sensitive worker effects."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import validate_artifact


class AuthorizationError(ValueError):
    """Raised when a persisted authorization cannot authorize an effect."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _parse_time(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise AuthorizationError("authorization_time_invalid", "authorization times must include a timezone")
    return parsed.astimezone(timezone.utc)


def read_rag_authorization(
    package_root: Path | str,
    *,
    package_id: str,
    target_revision: str,
    policy_revision: str,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Read and match the fixed persisted RAG authorization record."""

    root = Path(package_root)
    path = root / ".docops" / "rag-authorization.json"
    if path.is_symlink() or not path.is_file():
        raise AuthorizationError("rag_authorization_required", "RAG indexing requires persisted authorization")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuthorizationError("rag_authorization_invalid", "RAG authorization is unreadable") from exc
    if not isinstance(payload, dict):
        raise AuthorizationError("rag_authorization_invalid", "RAG authorization must be a JSON object")
    validation = validate_artifact("rag-authorization", payload)
    if not validation.ok:
        raise AuthorizationError("rag_authorization_invalid", "RAG authorization violates its contract")
    if payload["package_id"] != package_id:
        raise AuthorizationError("rag_authorization_scope_mismatch", "RAG authorization targets another package")
    if payload["target_revision"] != target_revision:
        raise AuthorizationError("rag_authorization_stale", "RAG authorization targets another revision")
    if payload["policy_revision"] != policy_revision:
        raise AuthorizationError("rag_authorization_stale", "RAG authorization targets another policy")
    current = (
        _parse_time(now)
        if isinstance(now, str)
        else (now.astimezone(timezone.utc) if isinstance(now, datetime) else datetime.now(timezone.utc))
    )
    expires_at = payload.get("expires_at")
    if expires_at is not None and _parse_time(str(expires_at)) <= current:
        raise AuthorizationError("rag_authorization_expired", "RAG authorization has expired")
    return payload


__all__ = ["AuthorizationError", "read_rag_authorization"]
