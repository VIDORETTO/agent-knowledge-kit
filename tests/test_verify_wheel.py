from __future__ import annotations

import json
import subprocess

from scripts.verify_wheel import command_failure_details


def test_wheel_failure_diagnostics_preserve_structured_errors_from_large_reports() -> None:
    expected_error = {
        "code": "symlink_artifact",
        "message": "runtime cache entered the package",
    }
    completed = subprocess.CompletedProcess(
        ["python", "-m", "docops", "run"],
        1,
        stdout=json.dumps(
            {
                "errors": [expected_error],
                "manifest": {"large": "x" * 5000},
                "outcome": {"code": "validation_failed", "status": "failed"},
            }
        ),
        stderr="",
    )

    diagnostic = json.loads(command_failure_details(completed))

    assert diagnostic["errors"] == [expected_error]
    assert diagnostic["outcome"] == {"code": "validation_failed", "status": "failed"}
    assert "manifest" not in diagnostic
