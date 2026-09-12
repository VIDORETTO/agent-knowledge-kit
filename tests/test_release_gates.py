# seam-scope: compatibility-infrastructure (release gate runner CLI)
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.run_release_gates import _absolute_path_preserving_symlink, build_gate_plan


def test_release_gate_plan_is_sequential_and_declares_isolated_outputs(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_release_gates.py",
            "--root",
            str(tmp_path),
            "--profile",
            "core",
            "--plan",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    stages = report["stages"]
    assert report["ok"] is True
    assert report["execution"] == "plan"
    assert [stage["order"] for stage in stages] == list(range(1, len(stages) + 1))
    assert len({stage["name"] for stage in stages}) == len(stages)
    assert all(stage["isolation"] == "unique-temporary-workspace" for stage in stages)
    assert all(stage["artifacts"] for stage in stages)


def test_release_gate_report_preserves_versions_denominators_and_skip_reason(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_release_gates.py",
            "--root",
            str(tmp_path),
            "--profile",
            "core",
            "--plan",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    report = json.loads(completed.stdout)
    assert report["versions"]["python"]
    assert "denominators" in report
    assert report["skip_policy"]["observable"]
    assert report["artifacts_root"]


def test_full_rag_stage_uses_the_selected_interpreter_when_runtime_root_is_temporary(tmp_path: Path) -> None:
    python = Path(sys.executable).resolve()
    stages = build_gate_plan(tmp_path, python, tmp_path / "artifacts", "full")
    rag_stage = next(stage for stage in stages if stage.name == "rag-mcp")

    assert rag_stage.environment["DOCOPS_RAG_PYTHON"] == str(python)
    assert str(tmp_path / "skills" / "vendor" / "knowledge-rag") in rag_stage.environment["PYTHONPATH"]


def test_ragflow_profile_repeats_core_and_adds_fail_closed_contract_stage(tmp_path: Path) -> None:
    stages = build_gate_plan(tmp_path, Path(sys.executable).resolve(), tmp_path / "artifacts", "ragflow")

    assert len(stages) == 23
    assert stages[-1].name == "ragflow-contract"
    assert stages[-1].commands[0][-1] == "--json"
    assert stages[-1].artifacts[-1].endswith("ragflow-report.json")


def test_selected_interpreter_path_preserves_virtualenv_symlink(tmp_path: Path) -> None:
    selected = tmp_path / "bin" / "python"
    selected.parent.mkdir()
    selected.symlink_to(sys.executable)

    assert _absolute_path_preserving_symlink(selected) == selected
