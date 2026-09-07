# seam-scope: compatibility-infrastructure (integration candidate report CLI)

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_integration_candidate_report_requires_green_gates_and_human_promotion(tmp_path: Path) -> None:
    gates = tmp_path / "t12.json"
    gates.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ok": True,
                "profile": "full",
                "stages": [{"name": "full", "status": "passed", "required": True}],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "report"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_integration_candidate.py",
            "--root",
            ".",
            "--output",
            str(output),
            "--gates-report",
            str(gates),
            "--no-bundle",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["technical_ready"] is True
    assert report["feature_trace"]
    assert report["compatibility"]["ok"] is True
    assert report["versioned_state"]["ok"] is True
    assert report["promotion"] == {
        "performed": False,
        "status": "blocked",
        "target": "main",
        "requires_human_approval": True,
        "authorization_record": None,
    }
    assert (output / "integration-candidate-report.json").is_file()
    assert (output / "integration-candidate-report.md").is_file()
