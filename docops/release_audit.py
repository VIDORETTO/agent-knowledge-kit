"""Release-candidate checks for prohibited artifacts and credential leaks."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SKIP_DIRS = {
    ".git",
    ".venv",
    ".venv-rag",
    "__pycache__",
    ".pytest_cache",
    "data",
    "models_cache",
    "artifacts",
    ".docops",
    "build",
    "dist",
}
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|secret|password|token)\s*[:=]\s*[\"']?(?!REPLACE|<set|\$\{)[A-Za-z0-9_./+=-]{20,}"),
)
_WIN_USERS = "Users"
_POSIX_USERS = "/" + _WIN_USERS + "/"
_POSIX_HOME = "/" + "home" + "/"
_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:[A-Za-z]:[\\/]+" + _WIN_USERS + r"[\\/]+[^\s`\"']+|" + _POSIX_USERS + r"[^\s`\"']+|" + _POSIX_HOME + r"[^\s`\"']+)"
)
_GENERIC_PATH_PARTS = {"seu_usuario", "your_user", "yourname", "user", "username", "you"}


@dataclass
class ReleaseAuditResult:
    ok: bool
    findings: list[dict[str, str]] = field(default_factory=list)
    scanned_files: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "ok": self.ok, "scanned_files": self.scanned_files, "findings": self.findings}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)


def _finding(findings: list[dict[str, str]], code: str, path: str, message: str) -> None:
    findings.append({"code": code, "path": path, "message": message})


def _contains_generic_path_part(value: str) -> bool:
    parts = [part.casefold() for part in re.split(r"[\\/]+", value) if part]
    return any(part in _GENERIC_PATH_PARTS for part in parts)


def _tracked_paths(root: Path) -> set[Path] | None:
    if not (root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    raw = completed.stdout.decode("utf-8", errors="replace")
    values = {root / item for item in raw.split("\0") if item}
    return values or None


def _allowed_document(relative: Path) -> bool:
    parts = relative.parts
    return len(parts) >= 2 and parts[0] == "documents" and parts[1] in {"README.md", "examples", "fixtures"}


def audit_release(root: Path | str, *, tracked_only: bool = False) -> ReleaseAuditResult:
    """Audit a clone without reading ignored runtime trees into the report."""

    project_root = Path(root).expanduser().resolve()
    findings: list[dict[str, str]] = []
    tracked = _tracked_paths(project_root) if tracked_only else None
    if tracked_only and tracked is None:
        _finding(findings, "git_index_unavailable", ".git", "tracked-only audit requires a readable Git index")
    if not tracked_only:
        for directory in sorted(_SKIP_DIRS - {".git", "__pycache__", ".pytest_cache"}):
            candidate = project_root / directory
            if candidate.is_dir():
                _finding(findings, "prohibited_artifact", directory, "runtime directory is not a release artifact")
    if tracked_only and tracked is not None:
        candidates = sorted(tracked or set())
    else:
        candidates = sorted(path for path in project_root.rglob("*") if path.is_file() or path.is_symlink())
    scanned = 0
    nested_git_reported = False
    for path in candidates:
        try:
            relative = path.relative_to(project_root)
        except ValueError:
            continue
        parts = relative.parts
        if path.is_symlink():
            _finding(findings, "symlink_artifact", relative.as_posix(), "symbolic links are not portable release artifacts")
            continue
        if ".git" in parts:
            if parts[0] != ".git" and not nested_git_reported:
                _finding(findings, "nested_git", relative.as_posix(), "nested Git metadata must not be shipped")
                nested_git_reported = True
            continue
        if any(part in _SKIP_DIRS for part in parts):
            continue
        if parts and parts[0] == "documents" and not _allowed_document(relative):
            _finding(findings, "prohibited_artifact", relative.as_posix(), "acquired corpus files are not release artifacts")
            continue
        if relative.as_posix() == "config/network.yaml":
            _finding(findings, "prohibited_artifact", relative.as_posix(), "private network configuration must not be released")
            continue
        scanned += 1
        try:
            if path.stat().st_size > 25 * 1024 * 1024:
                _finding(findings, "large_artifact", relative.as_posix(), "release file exceeds the 25 MiB source limit")
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                _finding(findings, "secret_like_value", relative.as_posix(), "credential-like value detected; remove it before release")
                break
        absolute_paths = [match.group(0) for match in _ABSOLUTE_PATH_PATTERN.finditer(text)]
        if any(not _contains_generic_path_part(match) for match in absolute_paths):
            _finding(findings, "author_path", relative.as_posix(), "release text contains an absolute user-machine path")
    for requirements_name in ("requirements.txt", "requirements-dev.txt", "requirements.lock"):
        requirements_path = project_root / requirements_name
        if not requirements_path.is_file() or (tracked_only and tracked is not None and requirements_path not in tracked):
            continue
        for line_number, line in enumerate(requirements_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            value = line.strip()
            if not value or value.startswith("#") or value.startswith("-"):
                continue
            if "==" not in value:
                _finding(findings, "unpinned_dependency", f"{requirements_name}:{line_number}", "release dependencies must use exact versions")
    return ReleaseAuditResult(not findings, findings, scanned)
