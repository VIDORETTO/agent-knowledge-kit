from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.evaluate_golden import _public_evaluation


def test_golden_public_report_contains_metrics_but_no_queries_or_paths() -> None:
    canary = "customer-merger-confidential-roadmap"
    private_path = "C:/" + "Users/operator/private/corpus.md"
    backend = {
        "status": "success",
        "total_queries": 1,
        "mrr_at_5": 1.0,
        "recall_at_5": 1.0,
        "per_query": [{"query": canary, "expected": private_path, "top_result": private_path}],
    }

    report = _public_evaluation(backend, case_count=1)

    serialized = json.dumps(report)
    assert report == {
        "schema_version": 1,
        "ok": True,
        "case_count": 1,
        "metrics": {"mrr_at_5": 1.0, "recall_at_5": 1.0},
    }
    assert canary not in serialized
    assert private_path not in serialized


def test_golden_gate_fails_closed_when_required_corpus_is_missing(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "reviewed": True,
                "cases": [
                    {
                        "query": "missing corpus",
                        "expected_filepath": "documents/private-snapshot/not-present.md",
                        "reviewed": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "scripts/evaluate_golden.py", "--cases", str(cases)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False
    assert payload["code"] == "corpus_missing"


def test_golden_gate_rejects_expected_path_escape(tmp_path: Path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "reviewed": True,
                "cases": [{"query": "escape", "expected_filepath": "../outside.md", "reviewed": True}],
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "scripts/evaluate_golden.py", "--cases", str(cases)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False
    assert payload["code"] == "golden_paths_invalid"
