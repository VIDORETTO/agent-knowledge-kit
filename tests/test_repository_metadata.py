from __future__ import annotations

import json
import tomllib
from pathlib import Path

import docops


def test_repository_metadata_is_consistent_and_utf8_clean() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    metadata = json.loads(Path("docs/REPOSITORY-METADATA.json").read_text(encoding="utf-8"))
    readme = Path("README.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert metadata["name"] == pyproject["name"]
    assert metadata["description"] == pyproject["description"]
    assert metadata["version"] == pyproject["version"] == docops.__version__
    assert f"Versão {docops.__version__} e verificação" in readme
    assert f"## {docops.__version__} — 2026-09-04" in changelog
    assert "Ã" not in readme
