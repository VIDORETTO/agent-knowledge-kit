"""Environment diagnostics for a clean clone.

The doctor intentionally reports capabilities instead of trying to install
anything. Installation belongs to the bootstrap command and to the user's
chosen harness; this module stays deterministic and has no model integration.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .config_audit import audit_config_file


@dataclass(frozen=True)
class PythonDiscovery:
    """A Python executable candidate and how it was found."""

    path: Path
    source: str

    @property
    def exists(self) -> bool:
        return self.path.is_file()


@dataclass
class DoctorReport:
    """Machine-readable result of the portable environment checks."""

    project_root: Path
    ok: bool
    checks: dict[str, dict[str, object]]
    capabilities: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "project_root": str(self.project_root),
            "ok": self.ok,
            "checks": self.checks,
            "capabilities": self.capabilities,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)


def _candidate_paths(project_root: Path) -> list[tuple[Path, str]]:
    """Return venv layouts in a platform-neutral order.

    A clean clone can be prepared on one operating system and inspected on
    another, so both POSIX and Windows layouts are considered regardless of
    the current host.
    """

    candidates: list[tuple[Path, str]] = []
    for venv_name in (".venv", ".venv-rag"):
        for relative in (
            Path("bin") / "python",
            Path("bin") / "python3",
            Path("Scripts") / "python.exe",
            Path("Scripts") / "python",
        ):
            source = "project-venv" if venv_name == ".venv" else "rag-venv"
            candidates.append((project_root / venv_name / relative, source))
    return candidates


def discover_python(
    project_root: Path | str,
    *,
    environ: Mapping[str, str] | None = None,
) -> PythonDiscovery:
    """Find the Python executable without assuming a Windows-only path.

    ``DOCOPS_PYTHON`` is an explicit override and is returned even if it does
    not exist, allowing the doctor to explain the broken configuration.
    """

    root = Path(project_root).resolve()
    env = os.environ if environ is None else environ
    override = env.get("DOCOPS_PYTHON", "").strip()
    if override:
        path = Path(override).expanduser()
        return PythonDiscovery(path if path.is_absolute() else root / path, "environment")

    for candidate, source in _candidate_paths(root):
        if candidate.is_file():
            return PythonDiscovery(candidate, source)

    for command in ("python3", "python"):
        found = shutil.which(command)
        if found:
            return PythonDiscovery(Path(found).resolve(), "PATH")

    return PythonDiscovery(Path(sys.executable).resolve(), "runtime")


def _file_check(path: Path, description: str) -> dict[str, object]:
    exists = path.is_file()
    result: dict[str, object] = {"ok": exists, "path": str(path), "description": description}
    if not exists:
        result["hint"] = f"Create {path.name} in the project root."
    return result


def run_doctor(
    project_root: Path | str,
    *,
    environ: Mapping[str, str] | None = None,
) -> DoctorReport:
    """Inspect the clone and return a JSON-serializable report."""

    root = Path(project_root).resolve()
    env = os.environ if environ is None else environ
    python = discover_python(root, environ=env)
    checks: dict[str, dict[str, object]] = {
        "python": {
            "ok": python.exists,
            "path": str(python.path),
            "source": python.source,
            "version": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
        "project_metadata": _file_check(root / "pyproject.toml", "project metadata"),
        "dependency_lock": _file_check(root / "requirements.lock", "locked dependencies"),
        "operator_skill": _file_check(root / "skills" / "doc-to-rag-operator" / "SKILL.md", "operator Agent Skill"),
    }
    config_path = root / "config.yaml"
    if config_path.is_file():
        config_result = audit_config_file(config_path)
        checks["config"] = {"ok": config_result.ok, "transport": config_result.transport, "errors": config_result.errors}

    skip_rag = env.get("DOCOPS_SKIP_RAG", "").lower() in {"1", "true", "yes"}
    if skip_rag:
        capabilities = {
            "rag": "skipped",
            "network": "not-probed",
            "harness": "external Agent Skills + MCP",
            "operator_skill": "skills/doc-to-rag-operator/SKILL.md",
            "mcp_transport": "stdio by default; HTTP/SSE requires audited bearer auth",
        }
        checks["rag"] = {"ok": True, "status": "skipped", "reason": "DOCOPS_SKIP_RAG"}
    else:
        rag_required = env.get("DOCOPS_REQUIRE_RAG", "").lower() in {"1", "true", "yes"}
        rag_python = next(
            (candidate for candidate, source in _candidate_paths(root) if candidate.is_file() and source == "rag-venv"),
            None,
        )
        rag_ok = rag_python is not None
        checks["rag"] = {
            "ok": rag_ok or not rag_required,
            "status": "available" if rag_ok else "missing",
            "required": rag_required,
            "python": str(rag_python) if rag_python else None,
            "hint": "Run bootstrap with --rag to install knowledge-rag." if not rag_ok else None,
        }
        capabilities = {
            "rag": "available" if rag_ok else "missing",
            "network": "not-probed",
            "harness": "external Agent Skills + MCP",
            "operator_skill": "skills/doc-to-rag-operator/SKILL.md",
            "mcp_transport": "stdio by default; HTTP/SSE requires audited bearer auth",
        }

    required_names = ["python", "project_metadata", "dependency_lock"]
    if checks["rag"].get("required") is True:
        required_names.append("rag")
    required_ok = all(checks[name].get("ok", False) is True for name in required_names)
    return DoctorReport(root, required_ok, checks, capabilities)
