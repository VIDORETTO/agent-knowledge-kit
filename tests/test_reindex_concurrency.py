from __future__ import annotations

import os
from pathlib import Path

from scripts.test_reindex_concurrency import (
    _mcp_error,
    _runtime_environment_for_package,
    recoverable_residue_counts,
    safe_reindex_status,
    stress_gate_findings,
)


def _stable_state(*, staging: int = 0, backups: int = 0, attempts: int = 0) -> dict[str, object]:
    return {
        "managed": True,
        "recovery": {"status": "stable"},
        "residue_counts": {"staging": staging, "backups": backups, "attempts": attempts},
    }


def test_stress_gate_rejects_warnings_and_every_residue_type() -> None:
    findings = stress_gate_findings(
        errors=[],
        warnings=[{"code": "stderr_warning", "severity": "warning", "redacted": True}],
        searches=40,
        min_searches=40,
        reindex={"active": False, "status": "succeeded", "error_count": 0},
        final_state=_stable_state(staging=1, backups=2, attempts=3),
        final_index={"backend_total_documents": 2, "backend_total_chunks": 4},
    )

    assert {finding["code"] for finding in findings} == {"stress_warnings_present", "stress_residue_present"}
    assert all(finding["redacted"] is True for finding in findings)


def test_stress_gate_requires_a_successful_terminal_reindex() -> None:
    common = {
        "errors": [],
        "warnings": [],
        "searches": 40,
        "min_searches": 40,
        "final_state": _stable_state(),
        "final_index": {"backend_total_documents": 2, "backend_total_chunks": 4},
    }

    active = stress_gate_findings(reindex={"active": True, "status": "running", "error_count": 0}, **common)
    failed = stress_gate_findings(reindex={"active": False, "status": "failed", "error_count": 1}, **common)

    assert [finding["code"] for finding in active] == ["reindex_not_terminal"]
    assert [finding["code"] for finding in failed] == ["reindex_failed"]


def test_stress_gate_rejects_insufficient_load_and_inconsistent_final_state() -> None:
    findings = stress_gate_findings(
        errors=[],
        warnings=[],
        searches=39,
        min_searches=40,
        reindex={"active": False, "status": "succeeded", "error_count": 0},
        final_state={"managed": False, "recovery": {"status": "repair_required"}, "residue_counts": {}},
        final_index={"backend_total_documents": None, "backend_total_chunks": 0},
    )

    assert [finding["code"] for finding in findings] == [
        "stress_load_below_minimum",
        "stress_final_state_invalid",
        "stress_final_index_invalid",
    ]


def test_reindex_status_summary_distinguishes_running_success_and_failure_without_details() -> None:
    running = safe_reindex_status({"active": True, "operation": "smart_reindex"})
    succeeded = safe_reindex_status({"active": False, "last_result": {"errors": 0, "indexed": 2}})
    failed = safe_reindex_status(
        {"active": False, "last_error": "token=secret query=customer-merger-confidential-roadmap"}
    )

    assert running == {"active": True, "status": "running", "error_count": None}
    assert succeeded == {"active": False, "status": "succeeded", "error_count": 0}
    assert failed == {"active": False, "status": "failed", "error_count": None}
    assert "secret" not in str(failed)
    assert "customer-merger" not in str(failed)


def test_stress_mcp_errors_never_retain_backend_query_or_token_details() -> None:
    canary = "query=customer-merger-confidential-roadmap token=private-value"

    diagnostic = _mcp_error({"error": {"message": canary}})

    assert diagnostic == "mcp_protocol_error"
    assert canary not in diagnostic


def test_completed_attempt_history_is_not_reported_as_recoverable_residue() -> None:
    counts = recoverable_residue_counts(
        {
            "staging": [],
            "backups": [],
            "attempts": [
                {
                    "status": "retained",
                    "outcome": {"status": "succeeded", "code": "completed"},
                    "staging": {"present": False},
                }
            ],
        }
    )

    assert counts == {"staging": 0, "backups": 0, "recoverable_attempts": 0, "attempt_records": 1}


def test_attempt_with_staging_or_nonterminal_outcome_is_recoverable_residue() -> None:
    counts = recoverable_residue_counts(
        {
            "staging": [],
            "backups": [],
            "attempts": [
                {
                    "status": "retained",
                    "outcome": {"status": "succeeded", "code": "completed"},
                    "staging": {"present": True},
                },
                {
                    "status": "retained",
                    "outcome": {"status": "running"},
                    "staging": {"present": False},
                },
            ],
        }
    )

    assert counts == {"staging": 0, "backups": 0, "recoverable_attempts": 2, "attempt_records": 2}


def test_concurrency_runtime_uses_the_reviewed_vendor_tree(tmp_path: Path) -> None:
    environment = _runtime_environment_for_package(tmp_path)

    assert environment["PYTHONPATH"].split(os.pathsep)[0] == str(
        Path(__file__).parents[1].resolve() / "skills" / "vendor" / "knowledge-rag"
    )
