"""Validate that published support and workflow gates agree."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "SUPPORT-MATRIX.json"
_ACTION = re.compile(r"^\s*-?\s*uses:\s+[^\s]+@([^\s#]+)", re.MULTILINE)


def _load_matrix(path: Path = MATRIX_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("support matrix must be an object")
    return value


def _workflow_text(workflows_dir: Path = ROOT / ".github" / "workflows") -> str:
    paths = sorted([*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")])
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def _workflow_jobs(workflows: str) -> set[str]:
    return set(re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", workflows, re.MULTILINE))


def audit(*, matrix_path: Path = MATRIX_PATH, workflows_dir: Path = ROOT / ".github" / "workflows") -> dict[str, Any]:
    matrix = _load_matrix(matrix_path)
    findings: list[dict[str, str]] = []
    python = matrix.get("python") if isinstance(matrix.get("python"), dict) else {}
    supported = python.get("supported") if isinstance(python.get("supported"), list) else []
    tolerated = python.get("tolerated") if isinstance(python.get("tolerated"), list) else []
    if not supported or python.get("minimum") != supported[0]:
        findings.append(
            {"code": "invalid_python_matrix", "message": "minimum Python must be the first supported version"}
        )
    try:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    except OSError as exc:
        findings.append({"code": "pyproject_unreadable", "message": str(exc)})
        pyproject = ""
    minimum = str(python.get("minimum", ""))
    if f'requires-python = ">={minimum}"' not in pyproject:
        findings.append({"code": "python_floor_drift", "message": "pyproject minimum differs from support matrix"})
    workflows = _workflow_text(workflows_dir)
    for version in supported:
        if f'"{version}"' not in workflows:
            findings.append(
                {"code": "python_version_missing", "message": f"supported Python {version} is absent from CI"}
            )
    for version in tolerated:
        if f'"{version}"' in workflows:
            findings.append(
                {
                    "code": "tolerated_version_in_matrix",
                    "message": f"tolerated Python {version} must not be advertised as supported CI",
                }
            )
    for action_revision in _ACTION.findall(workflows):
        if not re.fullmatch(r"[0-9a-f]{40}", action_revision):
            findings.append(
                {"code": "mutable_action", "message": "workflow actions must use full immutable commit SHAs"}
            )
    expected_commands = {
        "pytest": "python -m pytest",
        "ruff": "python -m ruff check",
        "format": "python -m ruff format --check",
        "doctor": "python -m docops doctor",
        "release-audit": "scripts/audit_release.py",
        "clean-clone": "scripts/verify_clean_clone.py",
        "contract-conformance": "scripts/check_contracts.py",
        "run-indexed": "--index-rag",
        "evaluate-mcp": "--adapter mcp",
        "reindex-concurrency": "scripts/test_reindex_concurrency.py",
        "wheel-create-validate-evaluate": "scripts/verify_wheel.py",
        "supply-chain": "scripts/generate_supply_chain.py",
        "supply-chain-verify": "scripts/verify_supply_chain.py",
        "candidate-audit": "scripts/audit_release.py --candidate",
        "candidate-bundle": "scripts/prepare_candidate.py",
        "candidate-verify": "scripts/verify_candidate.py",
    }
    for gate, marker in expected_commands.items():
        if marker not in workflows:
            findings.append({"code": "gate_missing", "message": f"workflow does not execute {gate}: {marker}"})
    if "scripts/check_support_matrix.py" not in workflows:
        findings.append({"code": "matrix_gate_missing", "message": "CI must validate the normative support matrix"})
    try:
        release_doc = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
    except OSError as exc:
        findings.append({"code": "release_runbook_unreadable", "message": str(exc)})
        release_doc = ""
    profiles = matrix.get("profiles") if isinstance(matrix.get("profiles"), dict) else {}
    gate_names = matrix.get("gates") if isinstance(matrix.get("gates"), dict) else {}
    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            findings.append({"code": "invalid_profile", "message": f"profile must be an object: {profile_name}"})
            continue
        profile_gates = profile.get("gates") if isinstance(profile.get("gates"), list) else []
        for gate in profile_gates:
            if gate not in gate_names:
                findings.append(
                    {
                        "code": "profile_gate_missing",
                        "message": f"profile {profile_name} references unknown gate: {gate}",
                    }
                )
    wrappers = matrix.get("wrappers") if isinstance(matrix.get("wrappers"), dict) else {}
    for wrapper_group, paths in wrappers.items():
        if not isinstance(paths, list):
            findings.append(
                {"code": "invalid_wrapper_group", "message": f"wrapper group must be a list: {wrapper_group}"}
            )
            continue
        for relative in paths:
            if not isinstance(relative, str) or not (ROOT / relative).is_file():
                findings.append({"code": "wrapper_missing", "message": f"declared wrapper is missing: {relative}"})
            elif relative not in workflows:
                findings.append(
                    {
                        "code": "wrapper_unexercised",
                        "message": f"workflow does not exercise declared wrapper: {relative}",
                    }
                )
    skips = matrix.get("skips") if isinstance(matrix.get("skips"), list) else []
    for skip in skips:
        if (
            not isinstance(skip, dict)
            or not isinstance(skip.get("condition"), str)
            or not isinstance(skip.get("observable"), str)
        ):
            findings.append(
                {"code": "invalid_skip_policy", "message": "each skip policy needs condition and observable"}
            )
    jobs = _workflow_jobs(workflows)
    claims = matrix.get("claims") if isinstance(matrix.get("claims"), list) else []
    for claim in claims:
        if not isinstance(claim, dict):
            findings.append({"code": "invalid_claim", "message": "support claims must be objects"})
            continue
        profile = claim.get("profile")
        job = claim.get("job")
        if not isinstance(profile, str) or profile not in profiles:
            findings.append(
                {"code": "unknown_profile", "message": f"support claim references unknown profile: {profile}"}
            )
        elif isinstance(profiles.get(profile), dict):
            for gate_name in profiles[profile].get("gates", []):
                for requirement in gate_names.get(gate_name, []) if isinstance(gate_names.get(gate_name), list) else []:
                    marker = expected_commands.get(requirement)
                    if marker and marker not in workflows:
                        findings.append(
                            {
                                "code": "profile_gate_unexecuted",
                                "message": f"profile {profile} requires {requirement}: {marker}",
                            }
                        )
        if not isinstance(job, str) or job not in jobs:
            findings.append({"code": "claim_job_missing", "message": f"support claim has no workflow job: {job}"})
        platforms = claim.get("platforms", claim.get("platform"))
        if isinstance(platforms, str):
            platforms = [platforms]
        if not isinstance(platforms, list) or not platforms:
            findings.append(
                {"code": "invalid_claim_platform", "message": "support claim must name at least one platform"}
            )
        else:
            for platform in platforms:
                if not isinstance(platform, str) or platform not in workflows:
                    findings.append(
                        {
                            "code": "claim_platform_missing",
                            "message": f"support claim platform is absent from workflows: {platform}",
                        }
                    )
    order = matrix.get("order")
    if isinstance(order, list):
        if len(order) != len(set(order)):
            findings.append({"code": "duplicate_gate_order", "message": "support order must not repeat a stage"})
        known_stages = {
            "bootstrap",
            "doctor",
            "dependencies",
            "support-matrix",
            "contracts",
            "pytest",
            "ruff",
            "clean-clone",
            "wheel",
            "supply-chain",
            "supply-chain-verify",
            "rag",
            "candidate-audit",
            "candidate-bundle",
            "candidate-verify",
        }
        for stage in order:
            if stage not in known_stages:
                findings.append(
                    {"code": "unknown_gate_order", "message": f"support order contains an unknown stage: {stage}"}
                )
            marker = expected_commands.get(stage) if isinstance(stage, str) else None
            if marker and marker not in release_doc:
                findings.append(
                    {"code": "runbook_gate_missing", "message": f"release runbook does not execute {stage}: {marker}"}
                )
    return {"schema_version": 1, "ok": not findings, "matrix": matrix, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    parser.add_argument("--workflows", type=Path, default=ROOT / ".github" / "workflows")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = audit(matrix_path=args.matrix.expanduser().resolve(), workflows_dir=args.workflows.expanduser().resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
