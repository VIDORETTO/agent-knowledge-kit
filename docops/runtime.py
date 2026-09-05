"""Portable runtime discovery shared by the command wrappers."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Mapping

from . import __version__

RAG_PACKAGE = "knowledge-rag"
RAG_RUNTIME_VERSION = "4.8.5"


def platform_venv_name() -> str:
    """Return the isolated venv name for the current filesystem platform."""

    return ".venv-windows" if os.name == "nt" else ".venv-posix"


def _native_venv_relatives() -> tuple[Path, ...]:
    if os.name == "nt":
        return (Path("Scripts") / "python.exe", Path("Scripts") / "python")
    return (Path("bin") / "python", Path("bin") / "python3")


def venv_config_matches_host(directory: Path) -> bool:
    """Reject a venv configuration created by the other OS in a shared tree."""

    config = directory / "pyvenv.cfg"
    if not config.is_file():
        return True
    home = None
    try:
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip().lower() == "home":
                home = value.strip()
                break
    except OSError:
        return True
    if not home:
        return True
    if os.name == "nt":
        return bool(PureWindowsPath(home).drive)
    return PurePosixPath(home).is_absolute() and not PureWindowsPath(home).drive


def venv_directory(project_root: Path | str) -> Path:
    """Select a native venv without allowing WSL and Windows to overwrite one another."""

    root = Path(project_root).resolve()
    primary = root / ".venv"
    platform_specific = root / platform_venv_name()
    if platform_specific.exists() and venv_config_matches_host(platform_specific):
        return platform_specific
    if primary.exists() and not venv_config_matches_host(primary):
        return platform_specific
    return primary


@dataclass(frozen=True)
class Executable:
    path: Path
    source: str

    @property
    def exists(self) -> bool:
        return self.path.is_file()


def _venv_candidates(root: Path, venv_names: tuple[str, ...]) -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    relatives = _native_venv_relatives()
    for name in venv_names:
        source = "environment" if name == "__override__" else ("rag-venv" if name == ".venv-rag" else "project-venv")
        for relative in relatives:
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
    for path, source in _venv_candidates(root, (".venv-rag", platform_venv_name(), ".venv")):
        if path.is_file() and _supports_knowledge_rag(path):
            return Executable(path, source)
    for command in ("python3", "python"):
        found = shutil.which(command)
        if found and _supports_knowledge_rag(Path(found)):
            return Executable(Path(found).absolute(), "PATH")
    missing = root / (Path("Scripts") / "python.exe" if os.name == "nt" else Path("bin") / "python")
    return Executable(missing, "missing")


def _supports_knowledge_rag(python: Path) -> bool:
    """Check module discoverability without importing or starting the server."""

    try:
        completed = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('mcp_server.server') else 1)",
            ],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def selected_runtime_version(python: Path | str, *, environ: Mapping[str, str] | None = None) -> str | None:
    """Read backend version from the selected interpreter, never this launcher."""

    environment = dict(os.environ if environ is None else environ)
    code = (
        "import sys\n"
        "try:\n"
        " import mcp_server\n"
        " value = getattr(mcp_server, '__version__', None)\n"
        "except ModuleNotFoundError as error:\n"
        " if error.name != 'mcp_server':\n"
        "  raise\n"
        " value = None\n"
        "if not value:\n"
        " from importlib.metadata import PackageNotFoundError, version\n"
        " try:\n"
        "  value = version('knowledge-rag')\n"
        " except PackageNotFoundError:\n"
        "  value = None\n"
        "print(value or '', file=sys.__stdout__)"
    )
    try:
        completed = subprocess.run(
            [str(python), "-c", code],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError, TypeError):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip().splitlines()
    return value[-1].strip() if value and value[-1].strip() else None


def runtime_contract(
    project_root: Path | str,
    *,
    python: Path | str | None = None,
    python_source: str | None = None,
    environ: Mapping[str, str] | None = None,
    expected_version: str | None = None,
) -> dict[str, str | None]:
    """Describe the exact backend contract used by a subprocess."""

    root = Path(project_root).resolve()
    discovered = None if python else discover_rag_python(root, environ=environ)
    executable = Path(python).expanduser().absolute() if python else discovered.path.absolute()
    environment = runtime_environment(root, environ=environ)
    selected_version = None
    if expected_version is None and executable.is_file():
        selected_version = selected_runtime_version(executable, environ=environment)
    contract_version = expected_version or selected_version or _vendor_version(root) or RAG_RUNTIME_VERSION
    return {
        "backend": RAG_PACKAGE,
        "expected_version": contract_version,
        "selected_version": selected_version,
        "python_source": python_source or ("explicit" if python else discovered.source),
    }


def _vendor_version(root: Path) -> str | None:
    version_path = root / "skills" / "vendor" / "knowledge-rag" / "mcp_server" / "__init__.py"
    try:
        text = version_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"__version__\s*=\s*[\"']([^\"']+)", text)
    return match.group(1) if match else None


def runtime_environment(
    project_root: Path | str,
    *,
    environ: Mapping[str, str] | None = None,
    disable_watcher: bool = True,
    vendor_root: Path | str | None = None,
    read_only: bool | None = None,
) -> dict[str, str]:
    """Build a subprocess environment rooted at the current clone."""

    root = Path(project_root).resolve()
    environment = dict(os.environ if environ is None else environ)
    environment["KNOWLEDGE_RAG_DIR"] = str(root)
    environment["PYTHONUNBUFFERED"] = "1"
    reviewed_vendor = Path(vendor_root).resolve() if vendor_root else root / "skills" / "vendor" / "knowledge-rag"
    if (reviewed_vendor / "mcp_server").is_dir():
        inherited_pythonpath = environment.get("PYTHONPATH", "")
        paths = [str(reviewed_vendor)]
        if inherited_pythonpath:
            paths.append(inherited_pythonpath)
        environment["PYTHONPATH"] = os.pathsep.join(paths)
    if disable_watcher:
        environment["KNOWLEDGE_RAG_WATCHER_DISABLED"] = "1"
    else:
        environment.pop("KNOWLEDGE_RAG_WATCHER_DISABLED", None)
    if read_only is True:
        environment["KNOWLEDGE_RAG_READ_ONLY"] = "1"
    elif read_only is False:
        # Maintenance callers must be able to override a reader environment
        # inherited from a parent harness.  The vendor server reads this once
        # at process start, so an explicit zero is safer than deleting it.
        environment["KNOWLEDGE_RAG_READ_ONLY"] = "0"
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


def runtime_provenance(
    project_root: Path | str,
    *,
    python: Path | str | None = None,
    python_source: str | None = None,
    environ: Mapping[str, str] | None = None,
    expected_version: str | None = None,
) -> dict[str, str | None]:
    """Describe the backend selected for a subprocess, without launcher metadata."""

    root = Path(project_root).resolve()
    vendor_version = _vendor_version(root)
    discovered = None if python else discover_rag_python(root, environ=environ)
    executable = Path(python).expanduser().absolute() if python else discovered.path.absolute()
    environment = runtime_environment(root, environ=environ)
    selected_version = selected_runtime_version(executable, environ=environment) if executable.is_file() else None
    backend_version = expected_version or selected_version or vendor_version
    source = "reviewed-vendor" if vendor_version else "installed-package" if selected_version else "unavailable"
    return {
        "operator_version": __version__,
        "backend": "knowledge-rag",
        "backend_version": backend_version,
        "backend_source": source,
        "selected_runtime_version": selected_version,
        "expected_version": expected_version or selected_version or vendor_version or RAG_RUNTIME_VERSION,
        "python_source": python_source or ("explicit" if python else discovered.source),
    }
