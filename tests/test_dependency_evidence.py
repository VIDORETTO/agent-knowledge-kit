from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_dependency_audit_preserves_raw_stdout_stderr_and_exit_code(tmp_path: Path) -> None:
    fake_root = tmp_path / "fake"
    package = fake_root / "pip_audit"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text(
        """
import json
import sys

print(json.dumps({
    "dependencies": [{
        "name": "chromadb",
        "version": "1.5.9",
        "vulns": [{"id": "CVE-2026-45829", "aliases": [], "fix_versions": []}],
    }],
    "fixes": [],
}))
print("RAW-STDERR-EVIDENCE", file=sys.stderr)
raise SystemExit(1)
""".lstrip(),
        encoding="utf-8",
    )
    requirements = tmp_path / "requirements.lock"
    requirements.write_text("chromadb==1.5.9\n", encoding="utf-8")
    evidence = tmp_path / "evidence"
    environment = {**os.environ, "PYTHONPATH": str(fake_root)}

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_dependencies.py",
            "--requirements",
            str(requirements),
            "--strict",
            "--evidence-dir",
            str(evidence),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    raw = report["audits"][0]["evidence"]
    assert (evidence / raw["stdout"]).read_text(encoding="utf-8").strip().startswith("{")
    assert (evidence / raw["stderr"]).read_text(encoding="utf-8").strip() == "RAW-STDERR-EVIDENCE"
    assert (evidence / raw["exit_code"]).read_text(encoding="ascii").strip() == "1"
    summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
    assert summary["raw_audit"]["ok"] is False
