"""Repository acquisition and documentation-tree detection."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .source_resolver import SourceCandidate, SourceResolution
from .web_acquirer import NetworkPolicy, NetworkPolicyError


class RepositoryAcquisitionError(RuntimeError):
    """Raised for a repository that cannot be safely inspected or cloned."""


_DOC_SUFFIXES = {
    ".md", ".markdown", ".rst", ".adoc", ".txt", ".html", ".htm", ".pdf", ".docx",
    ".json", ".yaml", ".yml", ".xml", ".csv", ".py", ".c", ".h", ".cpp", ".js",
    ".jsx", ".ts", ".tsx", ".ipynb", ".xlsx", ".pptx",
}
_IGNORED_DIRS = {".git", ".hg", ".svn", "node_modules", "dist", "build", "__pycache__", "img", "images", "assets"}


@dataclass
class RepositoryAcquisitionResult:
    ok: bool
    root: Path | None = None
    docs_path: Path | None = None
    docs_relative: str | None = None
    files: list[str] = field(default_factory=list)
    commit: str | None = None
    version: str | None = None
    license: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    temporary: bool = False

    def cleanup(self) -> None:
        """Remove a clone created in the private temporary workspace."""

        if not self.temporary or self.root is None:
            return
        root = self.root
        self.temporary = False
        try:
            shutil.rmtree(root)
        except OSError as exc:
            self.warnings.append(f"temporary repository cleanup failed: {exc}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "root": str(self.root) if self.root else None,
            "docs_path": str(self.docs_path) if self.docs_path else None,
            "docs_relative": self.docs_relative,
            "files": self.files,
            "commit": self.commit,
            "version": self.version,
            "license": self.license,
            "source": self.source,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class RepositoryAcquirer:
    """Clone or inspect a repository and locate its documentation tree."""

    def __init__(
        self,
        *,
        clone_root: Path | str | None = None,
        git_timeout: float = 120.0,
        allow_private_network: bool = False,
    ) -> None:
        self.clone_root = Path(clone_root).resolve() if clone_root else None
        self.git_timeout = git_timeout
        self.network_policy = NetworkPolicy(allow_private=allow_private_network)

    def acquire(
        self,
        source: SourceResolution | SourceCandidate | Path | str,
        *,
        version: str | None = None,
        scope: str | None = None,
        language: str | None = None,
        destination: Path | str | None = None,
    ) -> RepositoryAcquisitionResult:
        candidate = self._candidate(source, version=version, scope=scope, language=language)
        if not candidate:
            return RepositoryAcquisitionResult(False, errors=[{"code": "not_repository", "message": "source is not a repository"}])

        requested_version = version or candidate.version
        try:
            root, cloned = self._obtain_root(candidate, destination=destination, version=requested_version)
        except NetworkPolicyError as exc:
            return RepositoryAcquisitionResult(False, errors=[{"code": exc.code, "message": str(exc)}], source=candidate.to_dict())
        except (OSError, RepositoryAcquisitionError, subprocess.SubprocessError) as exc:
            return RepositoryAcquisitionResult(False, errors=[{"code": "repository_unavailable", "message": str(exc)}], source=candidate.to_dict())
        temporary = cloned and destination is None and self.clone_root is None

        if not (root / ".git").is_dir() or (root / ".git").is_symlink():
            return RepositoryAcquisitionResult(
                False,
                root=root,
                errors=[{"code": "not_repository", "message": f"no .git directory at {root}"}],
                source=candidate.to_dict(),
                temporary=temporary,
            )
        commit = self._git_output(root, "rev-parse", "HEAD")
        try:
            docs_path = self._find_docs(root, candidate.scope, candidate.language)
        except (OSError, RepositoryAcquisitionError) as exc:
            return RepositoryAcquisitionResult(
                False,
                root=root,
                commit=commit,
                version=requested_version or "local",
                license=self._license(root),
                source=candidate.to_dict(),
                errors=[{"code": "docs_tree_not_found", "message": str(exc)}],
                temporary=temporary,
            )
        if docs_path is None:
            return RepositoryAcquisitionResult(
                False,
                root=root,
                commit=commit,
                version=requested_version or "local",
                license=self._license(root),
                source=candidate.to_dict(),
                errors=[{"code": "docs_tree_not_found", "message": "could not detect a supported documentation directory"}],
                temporary=temporary,
            )

        files = self._scan_files(root, docs_path)
        warnings: list[str] = []
        if cloned:
            warnings.append("repository was cloned into a temporary/private workspace")
        actual_version = requested_version or self._git_output(root, "describe", "--tags", "--exact-match") or "local"
        return RepositoryAcquisitionResult(
            True,
            root=root,
            docs_path=docs_path,
            docs_relative=docs_path.relative_to(root).as_posix(),
            files=files,
            commit=commit,
            version=actual_version,
            license=self._license(root),
            source=candidate.to_dict(),
            warnings=warnings,
            temporary=temporary,
        )

    @staticmethod
    def _candidate(
        source: SourceResolution | SourceCandidate | Path | str,
        *,
        version: str | None,
        scope: str | None,
        language: str | None,
    ) -> SourceCandidate | None:
        if isinstance(source, SourceResolution):
            candidate = source.selected
        elif isinstance(source, SourceCandidate):
            candidate = source
        else:
            path = Path(source).expanduser()
            if path.exists():
                return SourceCandidate(
                    kind="repository",
                    slug=path.name,
                    canonical=path.resolve().as_uri(),
                    repo_url=None,
                    version=version,
                    scope=scope,
                    language=language,
                    official=None,
                    confidence=1.0,
                    evidence=("existing local repository path",),
                    aliases=(path.name,),
                )
            parsed = urlsplit(str(source))
            if parsed.scheme == "file":
                raw_path = unquote(parsed.path)
                if os.name == "nt" and re.match(r"^/[A-Za-z]:/", raw_path):
                    raw_path = raw_path[1:]
                if parsed.netloc and parsed.netloc.casefold() != "localhost":
                    raw_path = f"//{parsed.netloc}{raw_path}"
                path = Path(raw_path)
                if path.exists():
                    return RepositoryAcquirer._candidate(path, version=version, scope=scope, language=language)
            return None
        if candidate is None or candidate.kind != "repository":
            return None
        return SourceCandidate(
            kind=candidate.kind,
            slug=candidate.slug,
            canonical=candidate.canonical,
            url=candidate.url,
            repo_url=candidate.repo_url,
            docs_url=candidate.docs_url,
            version=version or candidate.version,
            scope=scope or candidate.scope,
            language=language or candidate.language,
            license=candidate.license,
            official=candidate.official,
            confidence=candidate.confidence,
            evidence=candidate.evidence,
            aliases=candidate.aliases,
        )

    def _obtain_root(self, candidate: SourceCandidate, *, destination: Path | str | None, version: str | None) -> tuple[Path, bool]:
        if candidate.canonical.startswith("file://"):
            parsed = urlsplit(candidate.canonical)
            raw_path = unquote(parsed.path)
            # ``Path('/C:/repo')`` is not the same as ``Path('C:/repo')`` on
            # Windows. Handle both Windows file URIs and POSIX file URIs.
            if os.name == "nt" and re.match(r"^/[A-Za-z]:/", raw_path):
                raw_path = raw_path[1:]
            if parsed.netloc and parsed.netloc.casefold() != "localhost":
                raw_path = f"//{parsed.netloc}{raw_path}"
            path = Path(raw_path).resolve()
            return path, False
        if candidate.repo_url and urlsplit(candidate.repo_url).scheme in {"http", "https"}:
            self.network_policy.validate(candidate.repo_url)
            target = Path(destination).resolve() if destination else (
                self.clone_root / candidate.slug if self.clone_root else Path(tempfile.mkdtemp(prefix=f"docops-{candidate.slug}-"))
            )
            if target.is_symlink():
                raise RepositoryAcquisitionError(f"clone destination must not be a symbolic link: {target}")
            if target.exists() and any(target.iterdir()):
                raise RepositoryAcquisitionError(f"clone destination is not empty: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            command = ["git", "clone", "--depth", "1"]
            if version:
                command.extend(["--branch", version])
            command.extend([candidate.repo_url, str(target)])
            try:
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=self.git_timeout)
            except (OSError, subprocess.SubprocessError):
                if destination is None and self.clone_root is None:
                    shutil.rmtree(target, ignore_errors=True)
                raise
            return target, True
        raise RepositoryAcquisitionError("repository candidate has no cloneable URL")

    @staticmethod
    def _find_docs(root: Path, scope: str | None, language: str | None = None) -> Path | None:
        if scope:
            raw_candidate = root / scope
            if raw_candidate.is_symlink():
                return None
            candidate = raw_candidate.resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError as exc:
                raise RepositoryAcquisitionError("documentation scope escapes repository") from exc
            if candidate.is_dir() and RepositoryAcquirer._scan_files(root, candidate):
                return candidate
            return None
        candidates = tuple(
            path
            for path in (
                f"docs/{language}/docs" if language else None,
                f"docs/{language}" if language else None,
                "docs/en/docs",
                "docs/en",
                "website/docs",
                "documentation",
                "docs",
                "doc",
                "content/docs",
            )
            if path
        )
        for relative in candidates:
            candidate = root / relative
            if not candidate.is_symlink() and candidate.is_dir() and RepositoryAcquirer._scan_files(root, candidate):
                return candidate
        return None

    @staticmethod
    def _scan_files(root: Path, docs_path: Path) -> list[str]:
        if docs_path.is_symlink():
            return []
        files: list[str] = []
        for path in sorted(docs_path.rglob("*")):
            if path.is_symlink() or not path.is_file() or path.suffix.casefold() not in _DOC_SUFFIXES:
                continue
            relative_parts = path.relative_to(root).parts
            if any(part in _IGNORED_DIRS for part in relative_parts):
                continue
            files.append(path.relative_to(root).as_posix())
        return files

    @staticmethod
    def _git_output(root: Path, *args: str) -> str | None:
        try:
            completed = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True, timeout=30)
        except (subprocess.SubprocessError, OSError):
            return None
        output = completed.stdout.strip()
        return output or None

    @staticmethod
    def _license(root: Path) -> dict[str, Any]:
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
            path = root / name
            if not path.is_symlink() and path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")[:1000]
                identifier = "MIT" if "mit license" in text.casefold() or "permission is hereby granted" in text.casefold() else "declared"
                return {"status": "declared", "file": name, "identifier": identifier}
        return {"status": "unknown", "file": None, "identifier": None}
