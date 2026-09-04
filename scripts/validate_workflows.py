"""Validate GitHub Actions YAML and require executable job steps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def validate_workflows(workflows_dir: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    paths = sorted([*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")])
    for path in paths:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            findings.append(
                {
                    "code": "workflow_yaml_invalid",
                    "file": path.name,
                    "message": "workflow is not valid UTF-8 YAML",
                }
            )
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), dict):
            findings.append(
                {"code": "workflow_jobs_missing", "file": path.name, "message": "workflow jobs must be a mapping"}
            )
            continue
        for name, job in payload["jobs"].items():
            if not isinstance(job, dict) or not isinstance(job.get("steps"), list) or not job["steps"]:
                findings.append(
                    {
                        "code": "job_steps_missing",
                        "file": path.name,
                        "message": f"workflow job has no executable steps: {name}",
                    }
                )
    return {
        "schema_version": 1,
        "ok": not findings and bool(paths),
        "workflow_count": len(paths),
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows", type=Path, default=Path(__file__).resolve().parents[1] / ".github/workflows")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = validate_workflows(args.workflows.expanduser().resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
