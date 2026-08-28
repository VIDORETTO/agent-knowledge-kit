"""Versioned execution manifests for the document operator."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .source_resolver import SourceResolution, canonicalize_url
from .storage import write_json_atomic

MANIFEST_SCHEMA_VERSION = 1
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "bearer",
    "client_secret",
    "password",
    "passwd",
    "private_key",
    "secret",
    "signature",
    "sig",
    "token",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _redact_query(query: str) -> str:
    pairs = parse_qsl(query, keep_blank_values=True)
    if not pairs:
        return query
    redacted = False
    safe_pairs: list[tuple[str, str]] = []
    for key, value in pairs:
        normalized = re.sub(r"[-\s]+", "_", key.casefold())
        if normalized in _SENSITIVE_QUERY_KEYS or normalized.endswith(("_token", "_secret")):
            safe_pairs.append((key, "REDACTED"))
            redacted = True
        else:
            safe_pairs.append((key, value))
    return urlencode(safe_pairs, doseq=True) if redacted else query


def redact_url(value: str) -> str:
    """Remove URL userinfo before it can enter a report or log."""

    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid-url>"
    safe_query = _redact_query(parsed.query)
    if parsed.scheme == "file":
        basename = Path(parsed.path.rstrip("/")).name or "source"
        return f"file://local/{basename}"
    if parsed.scheme not in {"http", "https"} or "@" not in parsed.netloc:
        if re.match(r"^[A-Za-z]:[\\/]", value) or os.path.isabs(value):
            return "<local-path>"
        try:
            return canonicalize_url(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, safe_query, "")))
        except ValueError:
            return "<invalid-url>"
    host = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, host, parsed.path or "/", safe_query, ""))


def _safe_local_reference(raw: Any, destination: Any) -> str | None:
    if not isinstance(raw, str) or not isinstance(destination, str) or not destination:
        return None
    parsed = urlsplit(raw)
    if parsed.scheme != "file" or parsed.netloc.casefold() == "local":
        return None
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    safe_destination = destination.replace("\\", "/")
    return f"file://local/{digest}/{safe_destination}"


def _safe_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    result = redact_metadata(dict(entry))
    for key in ("source", "canonical"):
        reference = _safe_local_reference(entry.get(key), entry.get("destination"))
        if reference:
            result[key] = reference
    return result


def redact_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Redact an entry while retaining a unique local-source identity."""

    return _safe_entry(entry)


def redact_metadata(value: Any) -> Any:
    """Recursively redact URL/path fields in nested reports."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"input", "source", "url", "canonical", "repo_url", "docs_url", "requested_url", "final_url"} and isinstance(item, str):
                result[str(key)] = redact_url(item)
            else:
                result[str(key)] = redact_metadata(item)
        return result
    if isinstance(value, list):
        return [redact_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [redact_metadata(item) for item in value]
    return value


def build_manifest(
    resolution: SourceResolution,
    *,
    entries: Iterable[Mapping[str, Any]],
    provenance: Mapping[str, Any],
    artifacts: Mapping[str, str],
    run_id: str | None = None,
    created_at: str | None = None,
    checkpoints: Mapping[str, Any] | None = None,
    metrics: Mapping[str, Any] | None = None,
    warnings: Iterable[str] = (),
    errors: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a machine-readable manifest without changing source files."""

    selected = resolution.selected
    source_canonical = selected.canonical if selected else resolution.input
    source = {
        "input": redact_url(resolution.input),
        "kind": resolution.kind,
        "canonical": redact_url(source_canonical),
        "version": selected.version if selected else None,
        "slug": selected.slug if selected else None,
        "scope": selected.scope if selected else None,
        "language": selected.language if selected else None,
        "license": selected.license if selected and selected.license else provenance.get("license"),
        "official": selected.official if selected else None,
        "requires_decision": resolution.requires_decision,
    }
    normalized_entries = [_safe_entry(entry) for entry in entries]
    accepted = sum(1 for entry in normalized_entries if entry.get("status") == "accepted")
    ignored = sum(1 for entry in normalized_entries if entry.get("status") == "ignored")
    entry_errors = sum(1 for entry in normalized_entries if entry.get("status") in {"error", "failed"})
    explicit_errors = [redact_metadata(dict(error)) for error in errors]
    all_errors = explicit_errors + [entry for entry in normalized_entries if entry.get("status") in {"error", "failed"}]
    status = "blocked" if resolution.requires_decision and not selected else ("partial" if all_errors else "succeeded")
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id or f"run-{uuid.uuid4().hex}",
        "created_at": created_at or utc_now(),
        "status": status,
        "source": source,
        "candidates": [_safe_entry(candidate.to_dict()) for candidate in resolution.candidates],
        "discovery": {
            "kind": resolution.kind,
            "candidate_count": len(resolution.candidates),
            "selected_confidence": selected.confidence if selected else None,
            "evidence": list(selected.evidence) if selected else [],
        },
        "provenance": redact_metadata(dict(provenance)),
        "entries": normalized_entries,
        "counts": {"accepted": accepted, "ignored": ignored, "errors": entry_errors + len(explicit_errors)},
        "artifacts": dict(artifacts),
        "checkpoints": redact_metadata(dict(checkpoints or {})),
        "metrics": redact_metadata(dict(metrics or {})),
        "warnings": list(warnings),
        "errors": all_errors,
    }


def write_manifest(path: Path | str, manifest: Mapping[str, Any]) -> None:
    """Persist a manifest atomically."""

    write_json_atomic(path, dict(manifest))


def read_manifest(path: Path | str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported or invalid manifest")
    return value
