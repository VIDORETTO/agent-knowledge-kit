"""Run the DOCOPS release gates sequentially in isolated stage workspaces.

The runner is deliberately an orchestration seam, not a second implementation
of the gates.  Each stage delegates to an existing public CLI, checker or
pytest command, records the exact command and a redacted diagnostic, and stops
on the first required failure.  RAG stages are optional only when the caller
explicitly allows the documented skip.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import locale
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ISOLATION = "unique-temporary-workspace"
PYTEST_COUNT_RE = re.compile(r"(?P<count>\d+)\s+(?P<label>passed|failed|skipped|xfailed|xpassed|error|errors)")
PYTEST_DURATION_RE = re.compile(r"in\s+(?P<seconds>[0-9]+(?:\.[0-9]+)?)s")
RAG_UNAVAILABLE_REASON = "knowledge-rag unavailable in the selected interpreter"


@dataclass(frozen=True)
class GateStage:
    """A serial gate with one private workspace and one or more commands."""

    name: str
    commands: tuple[tuple[str, ...], ...]
    artifacts: tuple[str, ...]
    required: bool = True
    requires_rag: bool = False
    environment: dict[str, str] = field(default_factory=dict)


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _display(value: str | Path, root: Path, output: Path | None = None) -> str:
    text = str(value)
    for original, replacement in ((str(root), "<root>"), (str(output) if output else "", "<artifacts>")):
        if original:
            text = text.replace(original, replacement)
    return text


def _command_display(command: Iterable[str], root: Path, output: Path | None) -> list[str]:
    return [_display(value, root, output) for value in command]


def _safe_tail(value: str, root: Path, output: Path | None) -> str:
    # Logs are evidence, but they must not turn a gate report into a corpus or
    # machine-layout export.  The underlying gate remains responsible for its
    # own content redaction; this layer removes known local path identifiers.
    redacted = _display(value, root, output)
    return redacted[-4000:]


def _counts(text: str) -> dict[str, int | float]:
    result: dict[str, int | float] = {}
    for match in PYTEST_COUNT_RE.finditer(text):
        label = match.group("label")
        if label == "errors":
            label = "error"
        result[label] = int(match.group("count"))
    duration = PYTEST_DURATION_RE.search(text)
    if duration:
        result["duration_seconds"] = float(duration.group("seconds"))
    return result


def _platform_report(python: Path) -> dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_executable": str(python),
        "shells": {name: shutil.which(name) is not None for name in ("sh", "bash", "pwsh")},
        "symlink_capability": _probe_symlink_capability(),
    }


def _probe_symlink_capability() -> bool:
    try:
        with tempfile.TemporaryDirectory(prefix="docops-gate-symlink-") as temporary:
            root = Path(temporary)
            target = root / "target"
            link = root / "link"
            target.write_text("x", encoding="utf-8")
            link.symlink_to(target)
            return link.is_symlink() and link.read_text(encoding="utf-8") == "x"
    except (OSError, NotImplementedError):
        return False


def _version_report(python: Path) -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "python_executable": str(python),
        "runner": "run_release_gates/1",
    }


def _source_report(root: Path) -> dict[str, Any]:
    def git_value(*arguments: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode:
            return None
        value = completed.stdout.strip()
        return value or None

    status = git_value("status", "--porcelain=v1", "--untracked-files=all")
    return {
        "commit": git_value("rev-parse", "--verify", "HEAD"),
        "branch": git_value("branch", "--show-current"),
        "worktree_entries": len(status.splitlines()) if status else 0,
        "binding": "checkout identity captured before gate execution",
    }


def _script(root: Path, name: str) -> str:
    return str(root / "scripts" / name)


def _artifact_path(stage_root: Path, name: str) -> str:
    return str(stage_root / name)


def _stage(
    name: str,
    root: Path,
    python: Path,
    stage_root: Path,
    commands: Iterable[Iterable[str]],
    *,
    artifacts: Iterable[str] = (),
    required: bool = True,
    requires_rag: bool = False,
    environment: dict[str, str] | None = None,
) -> GateStage:
    command_values = tuple(tuple(str(item) for item in command) for command in commands)
    artifact_values = tuple(str(Path(stage_root) / item) for item in artifacts)
    if not artifact_values:
        artifact_values = (_artifact_path(stage_root, "stage-report.json"),)
    return GateStage(
        name=name,
        commands=command_values,
        artifacts=artifact_values,
        required=required,
        requires_rag=requires_rag,
        environment=dict(environment or {}),
    )


def build_gate_plan(root: Path, python: Path, output: Path, profile: str) -> list[GateStage]:
    """Build the public, ordered gate plan without executing any command."""

    stage_root = output / "stages"
    py = str(python)
    root = root.expanduser().resolve()
    # Keep child Python's stdout encoding aligned with the host locale.  Forcing
    # UTF-8 here breaks existing subprocess seams on Windows: their parent
    # decodes text with the locale encoding, while Python would emit UTF-8.
    # The runner itself decodes and writes evidence explicitly below.
    common_env = {"PYTHONNOUSERSITE": "1"}
    clean_clone_command = [
        py,
        _script(root, "verify_clean_clone.py"),
        "--source",
        str(root),
        "--python",
        py,
        "--bootstrap",
    ]
    if profile == "full":
        clean_clone_command.append("--rag")
    stages = [
        _stage(
            "platform-info",
            root,
            python,
            stage_root / "01-platform-info",
            ((py, "--version"),),
            artifacts=("platform.json",),
            environment=common_env,
        ),
        _stage(
            "supply-chain-no-pip",
            root,
            python,
            stage_root / "02-supply-chain-no-pip",
            (
                (
                    py,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_candidate_identity.py::test_candidate_falls_back_when_bootstrap_no_install_leaves_a_venv_without_pip",
                ),
            ),
            artifacts=("pytest.log",),
            environment=common_env,
        ),
        _stage(
            "doctor",
            root,
            python,
            stage_root / "03-doctor",
            ((py, "-m", "docops", "doctor", "--root", str(root), "--json"),),
            artifacts=("doctor.json",),
            environment={**common_env, "DOCOPS_SKIP_RAG": "1"},
        ),
        _stage(
            "support-matrix",
            root,
            python,
            stage_root / "04-support-matrix",
            ((py, _script(root, "check_support_matrix.py"), "--json"),),
            artifacts=("support-matrix.json",),
            environment=common_env,
        ),
        _stage(
            "contracts",
            root,
            python,
            stage_root / "05-contracts",
            ((py, _script(root, "check_contracts.py"), "--json"),),
            artifacts=("contracts.json",),
            environment=common_env,
        ),
        _stage(
            "documentation",
            root,
            python,
            stage_root / "06-documentation",
            ((py, _script(root, "check_documentation.py"), "--root", str(root), "--json"),),
            artifacts=("documentation.json",),
            environment=common_env,
        ),
        _stage(
            "master-evolution-fixture",
            root,
            python,
            stage_root / "07-master-evolution-fixture",
            (
                (
                    py,
                    _script(root, "run_master_evolution_fixture.py"),
                ),
            ),
            artifacts=("master-evolution.json",),
            environment=common_env,
        ),
        _stage(
            "public-seams",
            root,
            python,
            stage_root / "08-public-seams",
            ((py, _script(root, "check_public_seams.py"), "--tests", str(root / "tests"), "--json"),),
            artifacts=("public-seams.json",),
            environment=common_env,
        ),
        _stage(
            "security",
            root,
            python,
            stage_root / "09-security",
            (
                (
                    py,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_rag_security_contract.py",
                    "tests/test_supply_chain.py",
                    "tests/test_learning.py",
                    "tests/test_usage_feedback.py",
                ),
            ),
            artifacts=("pytest.log",),
            environment=common_env,
        ),
        _stage(
            "dependency-audit",
            root,
            python,
            stage_root / "10-dependency-audit",
            (
                (
                    py,
                    _script(root, "audit_dependencies.py"),
                    "--requirements",
                    str(root / "requirements.lock"),
                    "--local",
                    "--strict",
                    "--evidence-dir",
                    str(stage_root / "10-dependency-audit" / "evidence"),
                ),
            ),
            artifacts=("evidence", "evidence/summary.json"),
            environment=common_env,
        ),
        _stage(
            "pip-check",
            root,
            python,
            stage_root / "11-pip-check",
            ((py, "-m", "pip", "check"),),
            artifacts=("pip-check.log",),
            environment=common_env,
        ),
        _stage(
            "workflow-yaml",
            root,
            python,
            stage_root / "12-workflow-yaml",
            (
                (
                    py,
                    _script(root, "validate_workflows.py"),
                    "--workflows",
                    str(root / ".github" / "workflows"),
                    "--json",
                ),
            ),
            artifacts=("workflows.json",),
            environment=common_env,
        ),
        _stage(
            "pytest",
            root,
            python,
            stage_root / "13-pytest",
            ((py, "-m", "pytest", "-q"),),
            artifacts=("pytest.log",),
            environment=common_env,
        ),
        _stage(
            "ruff",
            root,
            python,
            stage_root / "14-ruff",
            ((py, "-m", "ruff", "check", "docops", "tests", "scripts"),),
            artifacts=("ruff.log",),
            environment=common_env,
        ),
        _stage(
            "format",
            root,
            python,
            stage_root / "15-format",
            ((py, "-m", "ruff", "format", "--check", "docops", "tests", "scripts"),),
            artifacts=("format.log",),
            environment=common_env,
        ),
        _stage(
            "compileall",
            root,
            python,
            stage_root / "16-compileall",
            ((py, "-m", "compileall", "-q", "docops", "tests", "scripts"),),
            artifacts=("compileall.log",),
            environment=common_env,
        ),
        _stage(
            "diff-check",
            root,
            python,
            stage_root / "17-diff-check",
            (("git", "-C", str(root), "diff", "--check"),),
            artifacts=("diff-check.log",),
            environment=common_env,
        ),
        _stage(
            "clean-clone",
            root,
            python,
            stage_root / "18-clean-clone",
            (tuple(clean_clone_command),),
            artifacts=("clean-clone.json",),
            environment=common_env,
        ),
        _stage(
            "wheel-core",
            root,
            python,
            stage_root / "19-wheel-core",
            ((py, _script(root, "verify_wheel.py"), "--core"),),
            artifacts=("wheel-core.json",),
            environment=common_env,
        ),
        _stage(
            "crash-matrix",
            root,
            python,
            stage_root / "20-crash-matrix",
            (
                (
                    py,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_history_rollback.py",
                    "tests/test_promotion_recovery.py",
                    "tests/test_worker.py",
                ),
            ),
            artifacts=("pytest.log",),
            environment=common_env,
        ),
        _stage(
            "revocation",
            root,
            python,
            stage_root / "21-revocation",
            (
                (
                    py,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_reader_sessions.py",
                    "tests/test_learning.py",
                    "tests/test_candidate_publication.py",
                ),
            ),
            artifacts=("pytest.log",),
            environment=common_env,
        ),
    ]
    if profile == "full":
        rag_environment = {
            **common_env,
            "DOCOPS_RAG_PYTHON": str(python),
            "PYTHONPATH": os.pathsep.join((str(root / "skills" / "vendor" / "knowledge-rag"), str(root))),
        }
        stages.extend(
            [
                _stage(
                    "wheel-rag",
                    root,
                    python,
                    stage_root / "22-wheel-rag",
                    ((py, _script(root, "verify_wheel.py"), "--require-rag"),),
                    artifacts=("wheel-rag.json",),
                    requires_rag=True,
                    environment=common_env,
                ),
                _stage(
                    "rag-mcp",
                    root,
                    python,
                    stage_root / "23-rag-mcp",
                    _rag_commands(root, python, stage_root / "23-rag-mcp"),
                    artifacts=("stage-report.json", "package/manifest.json", "package/rag/index.json"),
                    requires_rag=True,
                    environment=rag_environment,
                ),
            ]
        )
    return stages


def _rag_commands(root: Path, python: Path, stage_root: Path) -> tuple[tuple[str, ...], ...]:
    py = str(python)
    source = stage_root / "source"
    package = stage_root / "package"
    cases = stage_root / "cases.json"
    return (
        (
            py,
            "-m",
            "docops",
            "run",
            str(source),
            "--output",
            str(package),
            "--slug",
            "release-gate",
            "--license",
            "MIT",
            "--runtime-root",
            str(stage_root),
            "--index-rag",
        ),
        (py, "-m", "docops", "validate", str(package), "--json"),
        (
            py,
            "-m",
            "docops",
            "evaluate",
            "--package",
            str(package),
            "--cases",
            str(cases),
            "--adapter",
            "mcp",
            "--runtime-root",
            str(stage_root),
            "--json",
        ),
        (py, _script(root, "mcp_smoke.py"), "background tasks"),
        (
            py,
            _script(root, "test_reindex_concurrency.py"),
            "--package",
            str(package),
            "--readers",
            "4",
            "--min-searches",
            "40",
            "--seconds",
            "10",
        ),
    )


def _prepare_rag_fixture(stage_root: Path) -> None:
    source = stage_root / "source"
    source.mkdir(parents=True, exist_ok=True)
    (source / "guide.md").write_text("# Guide\nAuthentication retries are bounded and observable.\n", encoding="utf-8")
    (stage_root / "cases.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "reviewed": True,
                "cases": [
                    {
                        "query": "authentication retries",
                        "expected_filepath": "guide.md",
                        "reviewed": True,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _rag_available(python: Path, root: Path) -> tuple[bool, str]:
    environment = {**os.environ, "PYTHONNOUSERSITE": "1", "PYTHONPATH": str(root)}
    try:
        completed = subprocess.run(
            [str(python), "-c", "import mcp_server.server"],
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    return completed.returncode == 0, (completed.stderr or completed.stdout or "").strip()[-500:]


def _initial_report(root: Path, python: Path, output: Path, profile: str, execution: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": execution == "plan",
        "execution": execution,
        "profile": profile,
        "root": _display(root, root, output),
        "artifacts_root": _display(output, root, output),
        "platform": _platform_report(python),
        "versions": _version_report(python),
        "source": _source_report(root),
        "denominators": {"stages": 0, "passed": 0, "failed": 0, "skipped": 0, "not_run": 0},
        "skip_policy": {
            "allowed": profile != "full",
            "observable": "status=skipped with an explicit reason and required=false",
            "rag_reason": RAG_UNAVAILABLE_REASON,
        },
        "isolation": {
            "mode": "serial",
            "workspace_policy": ISOLATION,
            "build_directories_shared": False,
        },
        "stages": [],
    }


def _plan_payload(stages: list[GateStage], root: Path, output: Path) -> list[dict[str, Any]]:
    planned: list[dict[str, Any]] = []
    for order, stage in enumerate(stages, start=1):
        planned.append(
            {
                "order": order,
                "name": stage.name,
                "status": "planned",
                "required": stage.required,
                "requires_rag": stage.requires_rag,
                "isolation": ISOLATION,
                "workspace": _display(Path(stage.artifacts[0]).parent, root, output),
                "commands": [_command_display(command, root, output) for command in stage.commands],
                "artifacts": [_display(path, root, output) for path in stage.artifacts],
            }
        )
    return planned


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _stage_record(
    stage: GateStage,
    order: int,
    *,
    root: Path,
    output: Path,
    status: str,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "order": order,
        "name": stage.name,
        "status": status,
        "required": stage.required,
        "requires_rag": stage.requires_rag,
        "isolation": ISOLATION,
        "workspace": _display(Path(stage.artifacts[0]).parent, root, output),
        "commands": [_command_display(command, root, output) for command in stage.commands],
        "artifacts": [_display(path, root, output) for path in stage.artifacts],
        "reason": reason,
    }


def _last_json_line(text: str) -> str | None:
    """Return the last complete JSON line from a command capture, if any."""

    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return candidate
    return None


def _materialize_declared_artifacts(stage: GateStage, command_results: list[dict[str, Any]]) -> None:
    """Ensure every declared capture artifact is a real, bounded file or directory."""

    stdout = str(command_results[-1].get("stdout_tail", "")) if command_results else ""
    stderr = str(command_results[-1].get("stderr_tail", "")) if command_results else ""
    for raw_path in stage.artifacts:
        path = Path(raw_path)
        if path.exists():
            continue
        if path.name == "stage-report.json":
            continue
        try:
            if path.suffix.casefold() == ".json":
                payload = _last_json_line(stdout)
                if payload is None:
                    payload = json.dumps(
                        {
                            "schema_version": 1,
                            "stage": stage.name,
                            "stdout_tail": stdout,
                            "stderr_tail": stderr,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(payload.rstrip() + "\n", encoding="utf-8")
            elif path.suffix:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(stdout + ("\n" + stderr if stderr else ""), encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)
        except OSError:
            # The command result and stage report remain authoritative when an
            # optional capture path cannot be materialized by the host.
            continue


def _run_stage(
    stage: GateStage,
    order: int,
    *,
    root: Path,
    output: Path,
    python: Path,
    timeout: int,
) -> dict[str, Any]:
    stage_dir = Path(stage.artifacts[0]).parent
    stage_dir.mkdir(parents=True, exist_ok=True)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() not in {"pythonpath", "pythonhome", "pythonioencoding", "pythonutf8"}
    }
    environment["PYTHONPATH"] = os.pathsep.join(
        str(value) for value in (root, os.environ.get("PYTHONPATH", "")) if value
    )
    environment.update(stage.environment)
    started = time.monotonic()
    started_at = _utc_now()
    record = _stage_record(stage, order, root=root, output=output, status="running")
    command_results: list[dict[str, Any]] = []
    success = True
    for command_index, command in enumerate(stage.commands, start=1):
        try:
            completed = subprocess.run(
                list(command),
                cwd=root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                timeout=timeout,
            )
            result = {
                "index": command_index,
                "command": _command_display(command, root, output),
                "returncode": completed.returncode,
                "stdout_tail": _safe_tail(completed.stdout, root, output),
                "stderr_tail": _safe_tail(completed.stderr, root, output),
                "denominators": _counts(completed.stdout + "\n" + completed.stderr),
            }
            command_results.append(result)
            (stage_dir / f"command-{command_index:02d}-stdout.log").write_text(result["stdout_tail"], encoding="utf-8")
            (stage_dir / f"command-{command_index:02d}-stderr.log").write_text(result["stderr_tail"], encoding="utf-8")
            if completed.returncode:
                success = False
                break
        except (OSError, subprocess.SubprocessError) as exc:
            success = False
            command_results.append(
                {
                    "index": command_index,
                    "command": _command_display(command, root, output),
                    "returncode": None,
                    "error": str(exc),
                    "denominators": {},
                }
            )
            break
    finished = time.monotonic()
    _materialize_declared_artifacts(stage, command_results)
    record.update(
        {
            "status": "passed" if success else "failed",
            "started_at": started_at,
            "duration_seconds": round(finished - started, 3),
            "returncode": 0
            if success
            else next((item.get("returncode") for item in command_results if item.get("returncode")), 1),
            "commands_run": command_results,
        }
    )
    # The stage report itself is an artifact and contains only redacted tails.
    _write_json(stage_dir / "stage-report.json", record)
    return record


def _update_denominators(report: dict[str, Any]) -> None:
    denominators = report["denominators"]
    stages = report["stages"]
    denominators["stages"] = len(stages)
    for stage in stages:
        status = stage.get("status")
        key = {"passed": "passed", "failed": "failed", "skipped": "skipped", "not-run": "not_run"}.get(status)
        if key:
            denominators[key] += 1
        for command in stage.get("commands_run", []):
            for label, count in command.get("denominators", {}).items():
                if label == "duration_seconds":
                    continue
                denominators[label] = denominators.get(label, 0) + count


def run_gate_pipeline(
    *,
    root: Path,
    python: Path,
    output: Path,
    profile: str,
    allow_rag_skip: bool = False,
    timeout: int = 1800,
) -> dict[str, Any]:
    stages = build_gate_plan(root, python, output, profile)
    report = _initial_report(root, python, output, profile, "run")
    report["skip_policy"]["allowed"] = bool(profile != "full" or allow_rag_skip)
    rag_available = True
    rag_diagnostic = "not-requested"
    if profile == "full":
        rag_available, rag_diagnostic = _rag_available(python, root)
        report["platform"]["rag_runtime"] = {"available": rag_available, "diagnostic": rag_diagnostic}
    blocked = False
    for order, stage in enumerate(stages, start=1):
        if blocked:
            record = _stage_record(
                stage,
                order,
                root=root,
                output=output,
                status="not-run",
                reason="blocked by an earlier required gate",
            )
        elif stage.requires_rag and not rag_available:
            if allow_rag_skip:
                record = _stage_record(
                    stage,
                    order,
                    root=root,
                    output=output,
                    status="skipped",
                    reason=RAG_UNAVAILABLE_REASON,
                )
            else:
                record = _stage_record(
                    stage,
                    order,
                    root=root,
                    output=output,
                    status="failed",
                    reason=f"{RAG_UNAVAILABLE_REASON}; rerun with an installed RAG runtime or explicit --allow-rag-skip",
                )
                blocked = True
        else:
            if stage.name == "rag-mcp":
                _prepare_rag_fixture(Path(stage.artifacts[0]).parent)
            record = _run_stage(stage, order, root=root, output=output, python=python, timeout=timeout)
            if record["status"] == "failed" and stage.required:
                blocked = True
        report["stages"].append(record)
        _update_denominators(report)
        _write_json(output / "release-gates.json", report)
    report["ok"] = not any(stage.get("status") == "failed" for stage in report["stages"])
    report["finished_at"] = _utc_now()
    _update_denominators(report)
    _write_json(output / "release-gates.json", report)
    return report


def _unique_output(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        output = requested.expanduser().resolve()
        if output.exists() and any(output.iterdir()):
            raise RuntimeError(f"gate output must be a new or empty directory: {output}")
        return output
    root = root.expanduser().resolve()
    # A clock-only name can collide when two shells start the gate at the same
    # instant.  The random suffix makes the default output safe even before a
    # second process reaches the non-empty-directory guard.
    return root / "artifacts" / f"release-gates-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(8)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--profile", choices=("core", "full"), default="full")
    parser.add_argument("--allow-rag-skip", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--plan", action="store_true", help="print the ordered plan without executing commands")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    python = args.python.expanduser().resolve()
    try:
        output = _unique_output(root, args.output)
        stages = build_gate_plan(root, python, output, args.profile)
        if args.plan:
            report = _initial_report(root, python, output, args.profile, "plan")
            report["stages"] = _plan_payload(stages, root, output)
            report["denominators"]["stages"] = len(stages)
        else:
            if not (root / "pyproject.toml").is_file():
                raise RuntimeError(f"repository metadata is missing: {root / 'pyproject.toml'}")
            output.mkdir(parents=True, exist_ok=True)
            report = run_gate_pipeline(
                root=root,
                python=python,
                output=output,
                profile=args.profile,
                allow_rag_skip=args.allow_rag_skip,
                timeout=max(1, args.timeout),
            )
    except (OSError, RuntimeError, ValueError) as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "execution": "plan" if args.plan else "run",
            "profile": args.profile,
            "error": {"code": "release_gate_runner_failed", "message": str(exc)},
        }
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
