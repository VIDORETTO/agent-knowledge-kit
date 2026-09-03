import json
import shutil
import subprocess
import sys
from pathlib import Path


def test_support_checker_rejects_a_platform_claim_without_a_matching_workflow_job(tmp_path: Path) -> None:
    matrix = json.loads(Path("docs/SUPPORT-MATRIX.json").read_text(encoding="utf-8"))
    matrix["claims"] = [
        {"id": "uncovered-profile", "platform": "windows", "profile": "bootstrap", "job": "missing-profile-job"}
    ]
    matrix_path = tmp_path / "SUPPORT-MATRIX.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    for path in Path(".github/workflows").glob("*.yml"):
        shutil.copy2(path, workflows / path.name)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_support_matrix.py",
            "--matrix",
            str(matrix_path),
            "--workflows",
            str(workflows),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    report = json.loads(completed.stdout)
    assert any(finding["code"] == "claim_job_missing" for finding in report["findings"])
