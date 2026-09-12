# seam-scope: compatibility-infrastructure (release gate boundary fixtures)
from __future__ import annotations

from docops.release_v2 import evaluate_cutover


def test_cutover_gate_requires_all_measured_thresholds_and_recovery() -> None:
    decision = evaluate_cutover(
        {
            "recall_at_5": 1.0,
            "mrr_at_5": 0.86,
            "citation_coverage": 1.0,
            "lineage_coverage": 1.0,
            "lifecycle": True,
            "recovery": True,
            "rollback": True,
            "ragflow_status": "passed",
        }
    )
    assert decision.status == "cutover_approved"


def test_cutover_gate_does_not_turn_external_not_run_into_pass() -> None:
    decision = evaluate_cutover(
        {
            "recall_at_5": 1.0,
            "mrr_at_5": 0.9,
            "citation_coverage": 1.0,
            "lineage_coverage": 1.0,
            "lifecycle": True,
            "recovery": True,
            "rollback": True,
            "ragflow_status": "not_run",
        }
    )
    assert decision.status == "not_run"
    assert decision.ok is False


def test_cutover_gate_rejects_below_threshold_without_removing_legacy() -> None:
    decision = evaluate_cutover(
        {
            "recall_at_5": 0.99,
            "mrr_at_5": 0.9,
            "citation_coverage": 1.0,
            "lineage_coverage": 1.0,
            "lifecycle": True,
            "recovery": True,
            "rollback": True,
            "ragflow_status": "passed",
        }
    )
    assert decision.status == "cutover_rejected"
    assert decision.legacy_preserved is True
