from __future__ import annotations

from pathlib import Path

from docops.evaluator import evaluate_package, generate_golden_candidates
from docops.pipeline import PipelineOptions, run_pipeline


def _package(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Authentication\nToken validation and errors.", encoding="utf-8")
    output = tmp_path / "package"
    result = run_pipeline(str(source), options=PipelineOptions(output_dir=output, slug="fixture", license="MIT"))
    assert result.ok
    return output


def test_evaluator_requires_reviewed_cases_and_reports_recall_and_mrr(tmp_path: Path) -> None:
    package = _package(tmp_path)
    cases = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [{"query": "Authentication token validation", "expected_filepath": "guide.md", "kind": "factual"}],
    }

    result = evaluate_package(package, cases)

    assert result.ok
    assert result.metrics["recall_at_5"] == 1.0
    assert result.metrics["mrr_at_5"] == 1.0
    assert result.cases[0]["expected_found"] is True
    assert result.thresholds == {"recall_at_5": 0.85, "mrr_at_5": 0.7}


def test_unreviewed_golden_candidates_cannot_be_used_as_a_quality_gate(tmp_path: Path) -> None:
    package = _package(tmp_path)
    candidates = generate_golden_candidates(package)
    result = evaluate_package(package, {"schema_version": 1, "cases": candidates})

    assert not result.ok
    assert any(error["code"] == "golden_not_reviewed" for error in result.errors)
