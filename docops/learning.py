"""Quarantine and review seam for conversation-derived learning proposals.

Conversation text is treated as a proposal, never as a source of truth.  The
module stores a minimized excerpt outside the active RAG tree, requires an
explicit reviewer for admission, and keeps revocation tombstones that block
historical rollback from resurrecting a derived document.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import validate_artifact
from .manifest import utc_now
from .storage import write_json_atomic, write_text_atomic

LEARNING_DIR = ".docops/learning"
PROPOSALS_DIR = "proposals"
REVIEWS_DIR = "reviews"
PRIVATE_DIR = "private"
TOMBSTONES_FILENAME = "tombstones.json"
INDEX_FILENAME = "index.json"

_SCHEMA_VERSION = 1
_PROPOSAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_MAX_EXCERPT = 4000
_MAX_CLAIM = 2000
_MAX_EVIDENCE = 8
_MAX_REFERENCE = 512
_MAX_QUOTE = 1200
_MAX_CONSENT_PURPOSE = 256
_MAX_CONSENT_HOLDER = 256
_FORBIDDEN_CAPTURE_FIELDS = {
    "messages",
    "transcript",
    "full_transcript",
    "conversation_log",
    "chat_history",
}
_CLAIM_KINDS = {
    "preference",
    "project_decision",
    "factual_correction",
    "observation_experiment",
    "hypothesis",
    "opinion",
    "agent_response",
    "question",
}
_SCOPES = {"private", "project", "shared"}
_EVIDENCE_KINDS = {
    "primary_source",
    "official_record",
    "reproducible_experiment",
    "decision_record",
    "user_confirmation",
    "user_statement",
    "agent_response",
    "conversation",
}
_RESPONSE_KINDS = {"agent_response", "assistant_response", "model_output"}
_RECURSIVE_SCHEMES = {"agent", "assistant", "model", "rag", "conversation"}


class LearningError(ValueError):
    """Raised when a proposal or review violates the learning policy."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


def _package_root(package_root: Path | str) -> Path:
    root = Path(package_root)
    if root.is_symlink():
        raise LearningError("unsafe_package_path", "learning package must not be a symbolic link")
    if root.exists() and not root.is_dir():
        raise LearningError("package_not_directory", "learning package must be a directory")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _learning_root(package_root: Path | str, *, create: bool = True) -> Path:
    root = _package_root(package_root) / LEARNING_DIR
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        raise LearningError("unsafe_learning_path", "learning state must be a regular directory")
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def _state_path(package_root: Path | str, relative: str, *, create_parent: bool = True) -> Path:
    root = _learning_root(package_root, create=create_parent)
    path = root / relative
    if path.exists() and path.is_symlink():
        raise LearningError("unsafe_learning_path", "learning state must not contain symbolic links")
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _proposal_path(package_root: Path | str, proposal_id: str) -> Path:
    return _state_path(package_root, f"{PROPOSALS_DIR}/{proposal_id}.json")


def _review_path(package_root: Path | str, review_id: str) -> Path:
    return _state_path(package_root, f"{REVIEWS_DIR}/{review_id}.json")


def _validate_id(value: str, *, field: str) -> str:
    normalized = value.strip()
    if not _PROPOSAL_ID.fullmatch(normalized):
        raise LearningError("invalid_identifier", f"{field} contains unsupported characters")
    return normalized


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LearningError("learning_state_unreadable", f"could not read learning state: {exc}") from exc
    if not isinstance(value, dict):
        raise LearningError("learning_state_invalid", "learning state must be a JSON object")
    return value


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _proposal_hash(proposal: Mapping[str, Any]) -> str:
    payload = {
        key: value for key, value in proposal.items() if key not in {"proposal_hash", "state", "review", "derived"}
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_proposal(proposal: Mapping[str, Any]) -> None:
    result = validate_artifact("learning-proposal", proposal)
    if not result.ok:
        raise LearningError(
            "learning_proposal_invalid",
            "learning proposal violates its public contract",
            details={"errors": result.errors},
        )
    expected = _proposal_hash(proposal)
    if proposal.get("proposal_hash") != expected:
        raise LearningError(
            "proposal_hash_mismatch",
            "learning proposal hash does not match its stable content",
            details={"expected": expected, "actual": proposal.get("proposal_hash")},
        )
    consent = proposal.get("consent")
    if not isinstance(consent, Mapping):
        raise LearningError("consent_invalid", "learning consent must be an object")
    _validate_consent_shape(consent)
    if consent.get("consent_hash") != _consent_hash(consent):
        raise LearningError("consent_hash_mismatch", "learning consent hash does not match its contents")


def _validate_review(review: Mapping[str, Any]) -> None:
    result = validate_artifact("learning-review", review)
    if not result.ok:
        raise LearningError(
            "learning_review_invalid",
            "learning review violates its public contract",
            details={"errors": result.errors},
        )


def _parse_time(value: Any, *, field: str) -> datetime:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise LearningError("consent_time_invalid", f"{field} must be RFC3339") from exc
    if parsed.tzinfo is None:
        raise LearningError("consent_time_invalid", f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _consent_hash(consent: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in consent.items() if key != "consent_hash"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_consent_shape(consent: Mapping[str, Any]) -> None:
    holder_id = str(consent.get("holder_id") or "").strip()
    if not holder_id or len(holder_id) > _MAX_CONSENT_HOLDER:
        raise LearningError("consent_holder_required", "consent holder_id is required")
    scope = str(consent.get("scope") or "").strip()
    if scope not in _SCOPES:
        raise LearningError("consent_scope_invalid", "consent scope must be private, project or shared")
    purpose = str(consent.get("purpose") or "").strip()
    if not purpose or len(purpose) > _MAX_CONSENT_PURPOSE:
        raise LearningError("consent_purpose_required", "consent purpose is required and must be bounded")
    granted_at = _parse_time(consent.get("granted_at"), field="consent.granted_at")
    expires_at = _parse_time(consent.get("expires_at"), field="consent.expires_at")
    if expires_at <= granted_at:
        raise LearningError("consent_window_invalid", "consent expires_at must be after granted_at")
    revoked_at = consent.get("revoked_at")
    if revoked_at is not None:
        _parse_time(revoked_at, field="consent.revoked_at")


def _normalize_consent(
    raw: Any,
    *,
    claim_scope: str,
    privacy: str,
    author_id: str | None,
    now: str | None,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise LearningError("consent_required", "conversation capture requires an explicit consent object")
    holder_id = str(raw.get("holder_id") or "").strip()
    if not holder_id or len(holder_id) > _MAX_CONSENT_HOLDER:
        raise LearningError("consent_holder_required", "consent holder_id is required")
    if author_id and holder_id != author_id:
        raise LearningError("consent_holder_mismatch", "consent holder must match the conversation author")
    scope = str(raw.get("scope") or "").strip()
    if scope not in _SCOPES:
        raise LearningError("consent_scope_invalid", "consent scope must be private, project or shared")
    if scope != claim_scope or scope != privacy:
        raise LearningError("consent_scope_mismatch", "consent scope must match claim and privacy scope")
    purpose = str(raw.get("purpose") or "").strip()
    if not purpose or len(purpose) > _MAX_CONSENT_PURPOSE:
        raise LearningError("consent_purpose_required", "consent purpose is required and must be bounded")
    granted_at = _parse_time(raw.get("granted_at"), field="consent.granted_at")
    expires_at = _parse_time(raw.get("expires_at"), field="consent.expires_at")
    current = _parse_time(now or utc_now(), field="now")
    if granted_at > current:
        raise LearningError("consent_not_yet_active", "consent granted_at cannot be in the future")
    if expires_at <= granted_at:
        raise LearningError("consent_window_invalid", "consent expires_at must be after granted_at")
    if expires_at <= current:
        raise LearningError("consent_expired", "consent expires_at must be in the future")
    revoked_at = raw.get("revoked_at")
    if revoked_at is not None:
        _parse_time(revoked_at, field="consent.revoked_at")
        raise LearningError("consent_revoked", "revoked consent cannot authorize capture")
    consent = {
        "holder_id": holder_id,
        "scope": scope,
        "purpose": purpose,
        "granted_at": _iso_time(granted_at),
        "expires_at": _iso_time(expires_at),
        "revoked_at": None,
    }
    consent["consent_hash"] = _consent_hash(consent)
    return consent


def _consent_is_active(consent: Mapping[str, Any], *, now: str | None) -> bool:
    try:
        _validate_consent_shape(consent)
        if consent.get("revoked_at") is not None:
            return False
        current = _parse_time(now or utc_now(), field="now")
        return (
            _parse_time(consent.get("granted_at"), field="consent.granted_at")
            <= current
            < _parse_time(consent.get("expires_at"), field="consent.expires_at")
        )
    except LearningError:
        return False


def _evidence_digest(kind: str, reference: str, quote: str | None) -> str:
    payload = {"kind": kind, "reference": reference, "quote": quote}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _normalize_verification(
    raw: Any,
    *,
    kind: str,
    reference: str,
    quote: str | None,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {
            "status": "unverified",
            "verifier": None,
            "provenance": None,
            "authority": None,
            "license": None,
            "supports_claim": False,
            "evidence_hash": None,
            "receipt_hash": None,
        }
    status = str(raw.get("status") or "").strip().casefold()
    if status != "verified":
        if status not in {"", "unverified"}:
            raise LearningError("evidence_verification_invalid", "evidence verification status is unsupported")
        return {
            "status": "unverified",
            "verifier": None,
            "provenance": None,
            "authority": None,
            "license": None,
            "supports_claim": False,
            "evidence_hash": None,
            "receipt_hash": None,
        }
    fields = {key: str(raw.get(key) or "").strip() for key in ("verifier", "provenance", "authority", "license")}
    if any(not value for value in fields.values()):
        raise LearningError(
            "evidence_verification_invalid",
            "verified evidence requires verifier, provenance, authority and license",
        )
    if fields["verifier"].casefold().split(":", 1)[0] in _RECURSIVE_SCHEMES:
        raise LearningError("evidence_verification_invalid", "agent or RAG output cannot verify evidence")
    if raw.get("supports_claim") is not True:
        raise LearningError("evidence_verification_invalid", "verified evidence must explicitly support the claim")
    evidence_hash = _evidence_digest(kind, reference, quote)
    if raw.get("evidence_hash") != evidence_hash:
        raise LearningError("evidence_verification_invalid", "evidence_hash does not match the cited material")
    receipt_payload = {"evidence_hash": evidence_hash, "verifier": fields["verifier"], "status": "verified"}
    expected_receipt = hashlib.sha256(_canonical_json(receipt_payload).encode("utf-8")).hexdigest()
    if raw.get("receipt_hash") != expected_receipt:
        raise LearningError("evidence_verification_invalid", "receipt_hash does not match the verifier envelope")
    return {
        "status": "verified",
        **fields,
        "supports_claim": True,
        "evidence_hash": evidence_hash,
        "receipt_hash": expected_receipt,
    }


def _normalize_evidence(raw: Any, *, field: str = "evidence") -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise LearningError("evidence_invalid", f"{field} must be a list")
    if len(raw) > _MAX_EVIDENCE:
        raise LearningError("evidence_too_large", f"{field} contains too many references")
    normalized: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise LearningError("evidence_invalid", f"{field} entries must be objects")
        kind = str(item.get("kind") or "").strip()
        reference = str(item.get("reference") or "").strip()
        if kind not in _EVIDENCE_KINDS:
            raise LearningError("evidence_kind_invalid", f"unsupported evidence kind {kind!r}")
        if not reference or len(reference) > _MAX_REFERENCE:
            raise LearningError("evidence_reference_invalid", "evidence reference must be short and non-empty")
        quote = item.get("quote")
        if quote is not None:
            quote = str(quote).strip()
            if len(quote) > _MAX_QUOTE:
                raise LearningError("evidence_quote_too_large", "evidence quote exceeds the minimization limit")
        verification = _normalize_verification(
            item.get("verification"),
            kind=kind,
            reference=reference,
            quote=quote,
        )
        normalized.append(
            {
                "kind": kind,
                "reference": reference,
                "quote": quote,
                "independent": item.get("independent") is True,
                "verification": verification,
            }
        )
    return normalized


def _recursive_evidence(item: Mapping[str, Any]) -> bool:
    reference = str(item.get("reference") or "").strip().casefold()
    scheme = reference.split(":", 1)[0]
    verification = item.get("verification") if isinstance(item.get("verification"), Mapping) else {}
    verifier = str(verification.get("verifier") or "").casefold()
    return scheme in _RECURSIVE_SCHEMES or verifier.split(":", 1)[0] in _RECURSIVE_SCHEMES


def _verified_evidence(item: Mapping[str, Any]) -> bool:
    verification = item.get("verification")
    return (
        isinstance(verification, Mapping)
        and verification.get("status") == "verified"
        and verification.get("supports_claim") is True
        and not _recursive_evidence(item)
    )


def _evidence_check(
    proposal: Mapping[str, Any],
    review_evidence: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    all_evidence = list(proposal.get("evidence") or []) + list(review_evidence or [])
    response_excluded = not any(
        str(item.get("kind") or "").casefold() in _RESPONSE_KINDS or _recursive_evidence(item)
        for item in all_evidence
        if isinstance(item, Mapping)
    )
    references = sorted(
        {
            str(item.get("reference")).strip()
            for item in all_evidence
            if isinstance(item, Mapping) and str(item.get("reference") or "").strip()
        }
    )
    claim = proposal.get("claim") if isinstance(proposal.get("claim"), Mapping) else {}
    kind = str(claim.get("kind") or "")
    independent_kinds = {
        "primary_source",
        "official_record",
        "reproducible_experiment",
        "decision_record",
        "user_confirmation",
        "user_statement",
    }
    independent = any(
        isinstance(item, Mapping)
        and item.get("independent") is True
        and str(item.get("kind") or "") in independent_kinds
        and _verified_evidence(item)
        for item in all_evidence
    )
    if kind == "preference":
        independent = any(
            isinstance(item, Mapping)
            and item.get("independent") is True
            and str(item.get("kind") or "") in {"user_confirmation", "user_statement"}
            and _verified_evidence(item)
            for item in all_evidence
        )
    return {
        "independent": independent,
        "response_excluded": response_excluded,
        "references": references,
    }


def _admission_reason(proposal: Mapping[str, Any], evidence_check: Mapping[str, Any]) -> str | None:
    claim = proposal.get("claim") if isinstance(proposal.get("claim"), Mapping) else {}
    kind = str(claim.get("kind") or "")
    scope = str(claim.get("scope") or "")
    privacy = str(proposal.get("privacy") or "")
    if not bool(evidence_check.get("response_excluded")):
        return "agent response is not independent evidence"
    if kind in {"hypothesis", "opinion", "question", "agent_response"}:
        return f"{kind} remains quarantined and cannot be admitted as knowledge"
    if kind == "preference":
        if scope != "private" or privacy != "private":
            return "personal preferences must remain private"
        if not evidence_check.get("independent"):
            return "personal preference requires explicit user confirmation"
        return None
    if kind == "project_decision":
        if scope not in {"project", "shared"}:
            return "project decisions require project or shared scope"
        if not evidence_check.get("independent"):
            return "project decision requires a decision record or confirmation"
        return None
    if kind == "factual_correction":
        if not evidence_check.get("independent"):
            return "factual correction requires an independent primary source or experiment"
        return None
    if kind == "observation_experiment":
        if not evidence_check.get("independent"):
            return "experimental observation requires reproducible evidence"
        return None
    return "claim kind is not admissible"


def _safe_relative_to_package(root: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/").lstrip("/")
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise LearningError("unsafe_derived_path", "derived path escapes the learning package") from exc
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _render_claim(proposal: Mapping[str, Any]) -> str:
    claim = proposal["claim"]
    lines = [
        f"# Verified learning proposal {proposal['proposal_id']}",
        "",
        str(claim["text"]).strip(),
        "",
        "## Provenance",
        "",
        f"- proposal: `{proposal['proposal_id']}`",
        f"- kind: `{claim['kind']}`",
        f"- scope: `{claim['scope']}`",
    ]
    evidence = proposal.get("evidence") or []
    if evidence:
        lines.extend(["", "## Evidence", ""])
        for item in evidence:
            lines.append(f"- `{item['kind']}`: `{item['reference']}`")
    return "\n".join(lines).rstrip() + "\n"


def _write_sources_metadata(package_root: Path, metadata: Mapping[str, Any]) -> None:
    path = package_root / "rag" / "sources.json"
    if path.exists() and path.is_symlink():
        raise LearningError("unsafe_rag_path", "RAG sources metadata must not be a symbolic link")
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LearningError("rag_sources_invalid", f"could not read RAG sources metadata: {exc}") from exc
    if not isinstance(payload, dict):
        raise LearningError("rag_sources_invalid", "RAG sources metadata must be an object")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        sources = []
    destination = str(metadata["destination"])
    sources = [item for item in sources if not isinstance(item, Mapping) or item.get("destination") != destination]
    sources.append(dict(metadata))
    payload["schema_version"] = 1
    payload["sources"] = sources
    write_json_atomic(path, payload)


def _remove_sources_metadata(package_root: Path, destination: str) -> None:
    path = package_root / "rag" / "sources.json"
    if not path.is_file() or path.is_symlink():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        return
    payload["sources"] = [
        item for item in payload["sources"] if not isinstance(item, Mapping) or item.get("destination") != destination
    ]
    write_json_atomic(path, payload)


def _load_tombstones(package_root: Path | str) -> list[dict[str, Any]]:
    path = _state_path(package_root, TOMBSTONES_FILENAME, create_parent=False)
    if not path.exists():
        return []
    payload = _read_json(path)
    value = payload.get("tombstones", [])
    if not isinstance(value, list):
        raise LearningError("tombstones_invalid", "learning tombstones must be a list")
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _write_index(package_root: Path | str) -> None:
    root = _learning_root(package_root)
    proposals: list[dict[str, Any]] = []
    for path in sorted((root / PROPOSALS_DIR).glob("*.json")) if (root / PROPOSALS_DIR).is_dir() else []:
        if path.is_symlink():
            continue
        try:
            value = _read_json(path)
        except LearningError:
            continue
        proposals.append(
            {
                "proposal_id": value.get("proposal_id"),
                "proposal_hash": value.get("proposal_hash"),
                "state": value.get("state"),
                "claim_kind": (value.get("claim") or {}).get("kind"),
                "privacy": value.get("privacy"),
                "submitted_at": value.get("submitted_at"),
            }
        )
    write_json_atomic(root / INDEX_FILENAME, {"schema_version": 1, "proposals": proposals})


def _load_proposal(package_root: Path | str, proposal_id: str) -> tuple[Path, dict[str, Any]]:
    normalized_id = _validate_id(proposal_id, field="proposal_id")
    path = _proposal_path(package_root, normalized_id)
    if not path.is_file() or path.is_symlink():
        raise LearningError("proposal_not_found", f"learning proposal {normalized_id!r} was not found")
    proposal = _read_json(path)
    _validate_proposal(proposal)
    return path, proposal


def submit_learning_proposal(
    package_root: Path | str,
    proposal: Mapping[str, Any] | Path | str,
    *,
    capture_opt_in: bool = False,
    now: str | None = None,
) -> dict[str, Any]:
    """Store a minimized conversation proposal in quarantine only."""

    root = _package_root(package_root)
    if isinstance(proposal, (Path, str)):
        try:
            raw = json.loads(Path(proposal).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LearningError("proposal_unreadable", f"could not read learning proposal: {exc}") from exc
    else:
        raw = dict(proposal)
    if not isinstance(raw, Mapping):
        raise LearningError("proposal_invalid", "learning proposal must be a JSON object")
    forbidden = sorted(_FORBIDDEN_CAPTURE_FIELDS.intersection(raw))
    if forbidden:
        raise LearningError(
            "capture_not_minimized",
            "submit only a minimized excerpt; full conversation fields are not accepted",
            details={"fields": forbidden},
        )
    explicit_opt_in = raw.get("capture_opt_in") is True or capture_opt_in is True
    if not explicit_opt_in:
        raise LearningError("capture_not_opted_in", "conversation capture requires explicit opt-in")

    excerpt = str(raw.get("excerpt") or "").strip()
    if not excerpt:
        raise LearningError("excerpt_required", "a minimized excerpt is required")
    if len(excerpt) > _MAX_EXCERPT:
        raise LearningError("excerpt_too_large", "conversation excerpt exceeds the minimization limit")
    claim_raw = raw.get("claim")
    if not isinstance(claim_raw, Mapping):
        raise LearningError("claim_invalid", "claim must be an object")
    claim_text = str(claim_raw.get("text") or "").strip()
    claim_kind = str(claim_raw.get("kind") or "").strip()
    claim_scope = str(claim_raw.get("scope") or "").strip()
    if not claim_text or len(claim_text) > _MAX_CLAIM:
        raise LearningError("claim_invalid", "claim text is empty or exceeds the minimization limit")
    if claim_kind not in _CLAIM_KINDS:
        raise LearningError("claim_kind_invalid", f"unsupported claim kind {claim_kind!r}")
    if claim_scope not in _SCOPES:
        raise LearningError("claim_scope_invalid", f"unsupported claim scope {claim_scope!r}")
    privacy = str(raw.get("privacy") or claim_scope).strip()
    if privacy not in _SCOPES:
        raise LearningError("privacy_invalid", f"unsupported privacy scope {privacy!r}")
    if claim_kind == "preference" and (claim_scope != "private" or privacy != "private"):
        raise LearningError("preference_scope_invalid", "personal preferences must be private")
    source_raw = raw.get("source") if isinstance(raw.get("source"), Mapping) else {}
    source_kind = str(source_raw.get("kind") or "conversation").strip()
    if source_kind not in {"conversation", "operator", "import"}:
        raise LearningError("source_kind_invalid", "source kind must be conversation, operator or import")
    source = {
        "kind": source_kind,
        "conversation_id": str(source_raw.get("conversation_id")).strip()
        if source_raw.get("conversation_id")
        else None,
        "author_id": str(source_raw.get("author_id")).strip() if source_raw.get("author_id") else None,
    }
    consent = _normalize_consent(
        raw.get("consent"),
        claim_scope=claim_scope,
        privacy=privacy,
        author_id=source["author_id"],
        now=now,
    )
    evidence = _normalize_evidence(raw.get("evidence"))
    proposal_id = _validate_id(
        str(raw.get("proposal_id") or f"proposal-{uuid.uuid4().hex}"),
        field="proposal_id",
    )
    proposal_value: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "proposal_id": proposal_id,
        "capture_opt_in": True,
        "excerpt": excerpt,
        "claim": {"text": claim_text, "kind": claim_kind, "scope": claim_scope},
        "evidence": evidence,
        "source": source,
        "consent": consent,
        "privacy": privacy,
        "state": "quarantined",
        "submitted_at": now or utc_now(),
        "proposal_hash": "",
        "approved": raw.get("approved") is True,
        "derived": [],
        "review": None,
    }
    proposal_value["proposal_hash"] = _proposal_hash(proposal_value)
    _validate_proposal(proposal_value)
    path = _proposal_path(root, proposal_id)
    if path.exists():
        raise LearningError("proposal_exists", f"learning proposal {proposal_id!r} already exists")
    write_json_atomic(path, proposal_value)
    _write_index(root)
    return {
        "schema_version": 1,
        "ok": True,
        "code": "learning_quarantined",
        "proposal_id": proposal_id,
        "proposal_hash": proposal_value["proposal_hash"],
        "state": "quarantined",
        "capture_opt_in": True,
        "searchable": False,
        "publication_allowed": False,
        "approval_field_ignored": proposal_value["approved"],
    }


def review_learning_proposal(
    package_root: Path | str,
    proposal_id: str,
    *,
    decision: str,
    actor: str,
    role: str = "human_approver",
    evidence: Sequence[Mapping[str, Any]] | None = None,
    now: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Review, admit, reject or revoke one proposal with explicit authority."""

    root = _package_root(package_root)
    path, proposal = _load_proposal(root, proposal_id)
    if role != "human_approver":
        raise LearningError("review_role_invalid", "learning admission requires a human_approver role")
    reviewer = actor.strip()
    if not reviewer:
        raise LearningError("review_actor_required", "review actor is required")
    author_id = str((proposal.get("source") or {}).get("author_id") or "").strip()
    if author_id and author_id == reviewer:
        raise LearningError("self_review_forbidden", "the proposal author cannot approve the same proposal")
    if decision not in {"admit", "reject", "revoke"}:
        raise LearningError("review_decision_invalid", "decision must be admit, reject or revoke")
    if decision == "revoke" and proposal.get("state") != "admitted":
        raise LearningError("proposal_not_admitted", "only an admitted proposal can be revoked")
    if decision in {"admit", "reject"} and proposal.get("state") != "quarantined":
        raise LearningError("proposal_not_quarantined", "only a quarantined proposal can be reviewed")
    if decision == "admit" and not _consent_is_active(proposal["consent"], now=now):
        raise LearningError("consent_inactive", "active consent is required before learning admission")

    reviewer_evidence = _normalize_evidence(evidence, field="review evidence")
    evidence_check = _evidence_check(proposal, reviewer_evidence)
    derived: list[dict[str, Any]] = []
    rollback_blocked = False
    final_state = decision
    if decision == "admit":
        admission_error = _admission_reason(proposal, evidence_check)
        if admission_error:
            raise LearningError("learning_admission_blocked", admission_error, details=evidence_check)
        claim = proposal["claim"]
        if claim["kind"] == "preference":
            private_path = _state_path(root, f"{PRIVATE_DIR}/{proposal['proposal_id']}.json")
            private_payload = {
                "schema_version": 1,
                "proposal_id": proposal["proposal_id"],
                "claim": dict(claim),
                "privacy": "private",
                "admitted_at": now or utc_now(),
            }
            write_json_atomic(private_path, private_payload)
            derived.append(
                {
                    "kind": "private_memory",
                    "path": private_path.relative_to(root).as_posix(),
                    "sha256": _sha256(private_path),
                    "active_rag": False,
                }
            )
        else:
            rag_root = root / "rag" / "documents"
            if rag_root.exists() and rag_root.is_symlink():
                raise LearningError("unsafe_rag_path", "RAG documents path must not be a symbolic link")
            rag_root.mkdir(parents=True, exist_ok=True)
            destination = rag_root / "learning" / f"{proposal['proposal_id']}.md"
            if destination.exists() and destination.is_symlink():
                raise LearningError("unsafe_derived_path", "learning document must not be a symbolic link")
            content = _render_claim(proposal)
            write_text_atomic(destination, content)
            relative_destination = destination.relative_to(root).as_posix()
            _write_sources_metadata(
                root,
                {
                    "schema_version": 1,
                    "source_id": f"conversation:{proposal['proposal_id']}",
                    "destination": relative_destination.removeprefix("rag/documents/"),
                    "title": f"Verified learning proposal {proposal['proposal_id']}",
                    "format": "conversation-proposal",
                    "privacy": proposal["privacy"],
                    "quality_status": "accepted",
                    "quality_reason": None,
                    "locators": [
                        {
                            "kind": "section",
                            "label": "Verified learning proposal",
                            "available": True,
                            "start_line": 1,
                            "end_line": 1,
                        }
                    ],
                },
            )
            derived.append(
                {
                    "kind": "active_rag_document",
                    "path": relative_destination,
                    "sha256": _sha256(destination),
                    "active_rag": True,
                    "reindex_required": True,
                }
            )
        final_state = "admitted"
    elif decision == "reject":
        final_state = "rejected"
    else:
        final_state = "revoked"
        consent = dict(proposal["consent"])
        consent["revoked_at"] = _iso_time(_parse_time(now or utc_now(), field="now"))
        consent["consent_hash"] = _consent_hash(consent)
        proposal["consent"] = consent
        tombstone_entries = _load_tombstones(root)
        for item in proposal.get("derived") or []:
            if not isinstance(item, Mapping) or not item.get("path"):
                continue
            relative = str(item["path"])
            target = _safe_relative_to_package(root, relative)
            if target.exists() or target.is_symlink():
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                else:
                    target.unlink(missing_ok=True)
            if relative.startswith("rag/documents/"):
                _remove_sources_metadata(root, relative.removeprefix("rag/documents/"))
            tombstone_entries.append(
                {
                    "schema_version": 1,
                    "proposal_id": proposal["proposal_id"],
                    "path": relative,
                    "sha256": item.get("sha256"),
                    "revoked_at": now or utc_now(),
                }
            )
        write_json_atomic(
            _state_path(root, TOMBSTONES_FILENAME),
            {"schema_version": 1, "tombstones": tombstone_entries},
        )
        rollback_blocked = True

    if decision == "revoke":
        proposal["proposal_hash"] = _proposal_hash(proposal)
    review: dict[str, Any] = {
        "schema_version": 1,
        "review_id": f"review-{uuid.uuid4().hex}",
        "proposal_id": proposal["proposal_id"],
        "proposal_hash": proposal["proposal_hash"],
        "decision": decision,
        "actor": reviewer,
        "role": role,
        "evidence_check": evidence_check,
        "publication_allowed": False,
        "derived": derived if decision == "admit" else list(proposal.get("derived") or []),
        "state": final_state,
        "reviewed_at": now or utc_now(),
        "reason": reason or "",
        "rollback_blocked": rollback_blocked,
    }
    _validate_review(review)
    proposal["state"] = final_state
    if decision == "admit":
        proposal["derived"] = derived
    proposal["review"] = {
        "review_id": review["review_id"],
        "decision": decision,
        "actor": reviewer,
        "reviewed_at": review["reviewed_at"],
    }
    _validate_proposal(proposal)
    write_json_atomic(path, proposal)
    write_json_atomic(_review_path(root, review["review_id"]), review)
    _write_index(root)
    return {
        "schema_version": 1,
        "ok": True,
        "code": {
            "admit": "learning_admitted",
            "reject": "learning_rejected",
            "revoke": "learning_revoked",
        }[decision],
        "proposal_id": proposal["proposal_id"],
        "proposal_hash": proposal["proposal_hash"],
        "review_id": review["review_id"],
        "state": final_state,
        "derived": derived if decision == "admit" else review["derived"],
        "publication_allowed": False,
        "searchable": bool(decision == "admit" and derived and derived[0].get("active_rag")),
        "reindex_required": bool(
            decision == "admit" and derived and derived[0].get("active_rag") and derived[0].get("reindex_required")
        ),
        "rollback_blocked": rollback_blocked,
        "evidence_check": evidence_check,
    }


def read_learning_proposal(package_root: Path | str, proposal_id: str) -> dict[str, Any]:
    """Read one proposal through the same validation boundary as mutations."""

    _, proposal = _load_proposal(package_root, proposal_id)
    return proposal


def admitted_learning_documents(package_root: Path | str) -> list[dict[str, Any]]:
    """Return active, non-private derived documents for a deterministic rebuild."""

    candidate_root = Path(package_root)
    if not candidate_root.exists():
        return []
    root = _package_root(candidate_root)
    proposal_dir = _learning_root(root) / PROPOSALS_DIR
    if not proposal_dir.is_dir():
        return []
    documents: list[dict[str, Any]] = []
    for path in sorted(proposal_dir.glob("*.json")):
        if path.is_symlink():
            continue
        try:
            proposal = _read_json(path)
            _validate_proposal(proposal)
        except LearningError:
            continue
        if proposal.get("state") != "admitted":
            continue
        for item in proposal.get("derived") or []:
            if not isinstance(item, Mapping) or item.get("kind") != "active_rag_document":
                continue
            relative = str(item.get("path") or "")
            if not relative.startswith("rag/documents/"):
                continue
            documents.append(
                {
                    "destination": relative.removeprefix("rag/documents/"),
                    "content": _render_claim(proposal),
                    "source": {
                        "schema_version": 1,
                        "source_id": f"conversation:{proposal['proposal_id']}",
                        "destination": relative.removeprefix("rag/documents/"),
                        "title": f"Verified learning proposal {proposal['proposal_id']}",
                        "format": "conversation-proposal",
                        "privacy": proposal["privacy"],
                        "quality_status": "accepted",
                        "quality_reason": None,
                        "locators": [
                            {
                                "kind": "section",
                                "label": "Verified learning proposal",
                                "available": True,
                                "start_line": 1,
                                "end_line": 1,
                            }
                        ],
                    },
                }
            )
    return documents


def copy_learning_state(source_root: Path | str, destination_root: Path | str) -> None:
    """Carry private learning state into a staged package without activation."""

    source = _package_root(source_root) / LEARNING_DIR
    if not source.is_dir() or source.is_symlink():
        return
    destination = _package_root(destination_root) / LEARNING_DIR
    if destination.exists() and destination.is_symlink():
        raise LearningError("unsafe_learning_path", "staged learning state must not be a symbolic link")
    shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=False)


def rollback_learning_guard(
    package_root: Path | str,
    historical_root: Path | str,
) -> dict[str, Any] | None:
    """Return a revocation conflict when rollback would restore a tombstoned file."""

    root = _package_root(package_root)
    historical = Path(historical_root).resolve()
    for tombstone in _load_tombstones(root):
        relative = str(tombstone.get("path") or "")
        if not relative:
            continue
        candidate = _safe_relative_to_package(historical, relative)
        if candidate.exists() or candidate.is_symlink():
            return {
                "proposal_id": tombstone.get("proposal_id"),
                "path": relative,
                "code": "revoked_learning_derivative",
            }
    return None


__all__ = [
    "LearningError",
    "admitted_learning_documents",
    "copy_learning_state",
    "read_learning_proposal",
    "review_learning_proposal",
    "rollback_learning_guard",
    "submit_learning_proposal",
]
