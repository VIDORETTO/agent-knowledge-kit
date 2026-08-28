from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_doctor_command_emits_machine_readable_report(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (tmp_path / "requirements.lock").write_text("# fixture\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "docops", "doctor", "--root", str(tmp_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "DOCOPS_SKIP_RAG": "1"},
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["ok"] is True
    assert report["capabilities"]["harness"] == "external Agent Skills + MCP"


def test_resolve_and_run_commands_are_consumable_by_a_harness(tmp_path: Path) -> None:
    source = tmp_path / "docs"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nUse the guide.", encoding="utf-8")
    output = tmp_path / "package"

    resolved = subprocess.run(
        [sys.executable, "-m", "docops", "resolve", str(source), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert resolved.returncode == 0, resolved.stderr
    assert json.loads(resolved.stdout)["selected"]["kind"] == "local"

    executed = subprocess.run(
        [
            sys.executable,
            "-m",
            "docops",
            "run",
            str(source),
            "--output",
            str(output),
            "--slug",
            "fixture",
            "--license",
            "MIT",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert executed.returncode == 0, executed.stderr
    assert json.loads(executed.stdout)["ok"] is True


def test_config_audit_command_rejects_an_unauthenticated_http_profile(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("server:\n  transport: sse\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "docops", "config-audit", str(config), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "network_auth_required" in completed.stdout
