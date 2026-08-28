"""Portable runtime discovery shared by the command wrappers."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Executable:
    path: Path
    source: str

    @property
    def exists(self) -> bool:
        return self.path.is_file()


def _venv_candidates(root: Path, venv_names: tuple[str, ...]) -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    for name in venv_names:
        source = "environment" if name == "__override__" else ("rag-venv" if name == ".venv-rag" else "project-venv")
        for relative in (
            Path("bin") / "python",
            Path("bin") / "python3",
            Path("Scripts") / "python.exe",
            Path("Scripts") / "python",
        ):
            candidates.append((root / name / relative, source))
    return candidates


def discover_rag_python(project_root: Path | str, *, environ: Mapping[str, str] | None = None) -> Executable:
    """Find the interpreter hosting knowledge-rag on any supported OS."""

    root = Path(project_root).resolve()
    env = os.environ if environ is None else environ
    override = env.get("DOCOPS_RAG_PYTHON", "").strip()
    if override:
        path = Path(override).expanduser()
        return Executable(path if path.is_absolute() else root / path, "environment")
    for path, source in _venv_candidates(root, (".venv-rag", ".venv")):
        if path.is_file():
            return Executable(path, source)
    for command in ("python3", "python"):
        found = shutil.which(command)
        if found:
            return Executable(Path(found).resolve(), "PATH")
    return Executable(Path(sys.executable).resolve(), "runtime")


def runtime_environment(
    project_root: Path | str,
    *,
    environ: Mapping[str, str] | None = None,
    disable_watcher: bool = True,
) -> dict[str, str]:
    """Build a subprocess environment rooted at the current clone."""

    root = Path(project_root).resolve()
    environment = dict(os.environ if environ is None else environ)
    environment["KNOWLEDGE_RAG_DIR"] = str(root)
    environment["PYTHONUNBUFFERED"] = "1"
    if disable_watcher:
        environment["KNOWLEDGE_RAG_WATCHER_DISABLED"] = "1"
    else:
        environment.pop("KNOWLEDGE_RAG_WATCHER_DISABLED", None)
    # A user-level mirror can redirect model downloads and make otherwise
    # reproducible bootstrap fail. The caller can opt back in explicitly.
    environment.pop("HF_ENDPOINT", None)
    return environment


def config_path(project_root: Path | str, *, environ: Mapping[str, str] | None = None) -> Path:
    root = Path(project_root).resolve()
    env = os.environ if environ is None else environ
    configured = env.get("DOCOPS_CONFIG", "").strip()
    path = Path(configured).expanduser() if configured else Path("config.yaml")
    return (path if path.is_absolute() else root / path).resolve()
