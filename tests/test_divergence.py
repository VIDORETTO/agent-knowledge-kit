from __future__ import annotations

from pathlib import Path

from docops.divergence import inspect_package_divergence
from docops.pipeline import PipelineOptions, run_pipeline


def test_validator_reports_skill_source_version_drift_without_claiming_success(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\n", encoding="utf-8")
    package = tmp_path / "package"
    assert run_pipeline(source, options=PipelineOptions(output_dir=package, slug="guide", version="v1", license="MIT")).ok

    skill = package / "skill" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace("`v1`", "`v2`"), encoding="utf-8")

    report = inspect_package_divergence(package)

    assert not report.synchronized
    assert report.warnings[0]["code"] == "skill_rag_divergence"
