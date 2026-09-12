"""Explicit Farol 2.0 release and RAGFlow cutover gates."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

EDITORIAL_TERMS = re.compile(r"mercado[ -]?livre|mercadolivre|\b(?:course|page|offer)\b", re.IGNORECASE)
LEGACY_TERMS = re.compile(r"knowledge-rag|chromadb|\bchroma\b", re.IGNORECASE)
_SURFACE_ALLOWLIST = {"docops/release_v2.py", "docops/migration.py", "specs/farol-2/"}


@dataclass(frozen=True)
class SurfaceAudit:
    surface: str
    ok: bool
    findings: list[dict[str, Any]]
    scanned_files: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "kind": "farol_v2_surface_audit",
            "surface": self.surface,
            "ok": self.ok,
            "scanned_files": self.scanned_files,
            "findings": self.findings,
        }


def audit_release_surface(
    root: Path | str,
    *,
    surface: str = "editorial",
    wheel: Path | str | None = None,
    allow_paths: set[str] | None = None,
) -> SurfaceAudit:
    """Find forbidden 1.x surfaces without exposing source content."""

    if surface not in {"editorial", "legacy", "all"}:
        raise ValueError("surface must be editorial, legacy or all")
    patterns: list[tuple[str, re.Pattern[str]]] = []
    if surface in {"editorial", "all"}:
        patterns.append(("editorial", EDITORIAL_TERMS))
    if surface in {"legacy", "all"}:
        patterns.append(("legacy", LEGACY_TERMS))
    allowed = set(_SURFACE_ALLOWLIST) | set(allow_paths or set())
    findings: list[dict[str, Any]] = []
    scanned = 0
    if wheel is not None:
        wheel_path = Path(wheel).expanduser().resolve()
        with zipfile.ZipFile(wheel_path) as archive:
            for name in sorted(archive.namelist()):
                if name.endswith("/") or _is_allowlisted(name, allowed):
                    continue
                try:
                    text = archive.read(name).decode("utf-8")
                except (UnicodeDecodeError, KeyError):
                    continue
                scanned += 1
                findings.extend(_find_terms(name, text, patterns))
    else:
        root_path = Path(root).expanduser().resolve()
        paths = [
            path
            for path in sorted(root_path.rglob("*"))
            if path.is_file()
            and not path.is_symlink()
            and not any(part in {".git", ".venv", ".venv-rag", "__pycache__", ".pytest_cache"} for part in path.parts)
        ]
        for path in paths:
            relative = path.relative_to(root_path).as_posix()
            if _is_allowlisted(relative, allowed):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            scanned += 1
            findings.extend(_find_terms(relative, text, patterns))
    return SurfaceAudit(surface, not findings, findings, scanned)


def require_cutover_approved(decision: Mapping[str, Any] | "CutoverDecision") -> None:
    """Guard destructive contraction behind the exact current decision."""

    payload = decision.to_dict() if isinstance(decision, CutoverDecision) else dict(decision)
    if payload.get("status") != "cutover_approved" or payload.get("ok") is not True:
        raise RuntimeError("legacy contraction requires an approved Farol 2.0 cutover decision")


def _is_allowlisted(path: str, allowlist: set[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized == item or normalized.startswith(item) for item in allowlist)


def _find_terms(path: str, text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for category, pattern in patterns:
            matches = sorted({match.group(0).casefold() for match in pattern.finditer(line)})
            if matches:
                findings.append({"category": category, "path": path, "line": line_number, "terms": matches})
    return findings


@dataclass(frozen=True)
class CutoverDecision:
    status: str
    ok: bool
    legacy_preserved: bool
    gates: dict[str, Any]
    blockers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "kind": "cutover_decision",
            "status": self.status,
            "ok": self.ok,
            "legacy_preserved": self.legacy_preserved,
            "gates": self.gates,
            "blockers": self.blockers,
        }


def evaluate_cutover(metrics: Mapping[str, Any]) -> CutoverDecision:
    gates = {
        "recall_at_5": _at_least(metrics.get("recall_at_5"), 1.0),
        "mrr_at_5": _at_least(metrics.get("mrr_at_5"), 0.86),
        "citation_coverage": _at_least(metrics.get("citation_coverage"), 1.0),
        "lineage_coverage": _at_least(metrics.get("lineage_coverage"), 1.0),
        "lifecycle": metrics.get("lifecycle") is True,
        "recovery": metrics.get("recovery") is True,
        "rollback": metrics.get("rollback") is True,
        "ragflow": metrics.get("ragflow_status") == "passed",
    }
    blockers = [name for name, passed in gates.items() if not passed]
    if metrics.get("ragflow_status") in {"not_run", "blocked"}:
        status = "not_run"
    elif blockers:
        status = "cutover_rejected"
    else:
        status = "cutover_approved"
    return CutoverDecision(status, status == "cutover_approved", True, gates, blockers)


def _at_least(value: Any, threshold: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) >= threshold
