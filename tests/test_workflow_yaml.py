from __future__ import annotations

from pathlib import Path

from scripts.validate_workflows import validate_workflows


def test_repository_workflows_are_valid_yaml_with_executable_jobs() -> None:
    report = validate_workflows(Path(".github/workflows"))

    assert report["ok"] is True
    assert report["workflow_count"] >= 3


def test_workflow_validator_rejects_invalid_yaml_and_missing_steps(tmp_path: Path) -> None:
    (tmp_path / "invalid.yml").write_text("jobs: [\n", encoding="utf-8")
    (tmp_path / "empty.yml").write_text("name: Empty\njobs:\n  noop:\n    runs-on: ubuntu-latest\n", encoding="utf-8")

    report = validate_workflows(tmp_path)

    assert report["ok"] is False
    assert {finding["code"] for finding in report["findings"]} == {"workflow_yaml_invalid", "job_steps_missing"}
