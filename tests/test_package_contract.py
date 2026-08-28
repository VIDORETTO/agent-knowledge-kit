from __future__ import annotations

import json
from pathlib import Path

from docops.package_validator import validate_package


def test_validator_rejects_a_package_missing_one_product(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "run-1",
                "source": {"input": "fixture", "canonical": "file:///fixture", "version": "local"},
                "provenance": {"license": "MIT", "redistribution": "allowed"},
                "artifacts": {"skill": "skill", "router": "router", "rag": "rag"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_package(tmp_path)

    assert not result.ok
    assert "missing_skill" in {error["code"] for error in result.errors}


def test_validator_accepts_the_complete_fixture_package(tmp_path: Path) -> None:
    skill = tmp_path / "skill"
    router = tmp_path / "router"
    rag = tmp_path / "rag"
    (skill / "chapters").mkdir(parents=True)
    router.mkdir()
    (rag / "documents").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: fixture-skill\ndescription: Fixture knowledge skill.\n---\n# Fixture\n",
        encoding="utf-8",
    )
    (router / "SKILL.md").write_text(
        "---\nname: fixture-router\ndescription: Routes fixture questions.\n---\n"
        "Use fixture-skill for concepts and search_knowledge for facts. Cite source.\n",
        encoding="utf-8",
    )
    (rag / "documents" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (rag / "index.json").write_text(
        json.dumps({"status": "ready", "documents": 1, "chunks": 1}), encoding="utf-8"
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "run-1",
                "source": {"input": "fixture", "canonical": "file:///fixture", "version": "local"},
                "provenance": {"license": "MIT", "redistribution": "allowed"},
                "artifacts": {"skill": "skill", "router": "router", "rag": "rag"},
            }
        ),
        encoding="utf-8",
    )

    result = validate_package(tmp_path)

    assert result.ok, result.errors
