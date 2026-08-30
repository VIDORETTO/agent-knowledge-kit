from __future__ import annotations

from pathlib import Path

from scripts.bootstrap import install_command, pip_upgrade_command


def test_bootstrap_installs_the_project_and_optional_profiles(tmp_path: Path) -> None:
    command = install_command(Path("python"), tmp_path, rag=True, formats=True, dev=True)

    assert command[:5] == ["python", "-m", "pip", "install", "--editable"]
    assert str(tmp_path) in command
    assert "--requirement" in command
    assert "pytest==9.1.1" in command
    assert "pip-audit==2.10.1" in command
    assert "setuptools==84.0.0" in command
    assert command.count(str(tmp_path / "requirements.txt")) == 1


def test_bootstrap_pins_a_known_safe_pip_before_installing_packages() -> None:
    command = pip_upgrade_command(Path("python"))

    assert command[-2:] == ["pip==26.2.1", "setuptools==84.0.0"]
