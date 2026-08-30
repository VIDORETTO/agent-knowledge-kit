from __future__ import annotations

from pathlib import Path

from scripts.bootstrap import install_command


def test_bootstrap_installs_the_project_and_optional_profiles(tmp_path: Path) -> None:
    command = install_command(Path("python"), tmp_path, rag=True, formats=True, dev=True)

    assert command[:5] == ["python", "-m", "pip", "install", "--editable"]
    assert str(tmp_path) in command
    assert "--requirement" in command
    assert "pytest==8.4.1" in command
    assert command.count(str(tmp_path / "requirements.txt")) == 1
