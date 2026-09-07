"""Prepare an unpublished integration-candidate decision report.

This command composes the existing candidate, contract and release-gate seams.
It never merges, pushes, publishes or changes the active corpus. Promotion is a
separate human decision and is always reported as blocked until an external
authorization record exists.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.candidate_identity import (  # noqa: E402
    candidate_digest,
    git_commit,
    git_files,
    inspect_identity,
    worktree_status,
)

SCHEMA_VERSION = 1
FORBIDDEN_EXACT_FILES = {".rag_state.json"}
FORBIDDEN_DIRECTORY_PARTS = {
    ".venv",
    ".venv-posix",
    ".venv-rag",
    ".venv-windows",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
    "models_cache",
}

FEATURE_TRACE: tuple[dict[str, Any], ...] = (
    {
        "id": "modular-core",
        "selected": True,
        "origin": "working-tree",
        "origin_ref": "local integration worktree",
        "evidence": ["docops/operations.py", "docops/coordination.py", "docops/reader_sessions.py"],
        "decision": "preserve modular domain modules as the canonical lifecycle implementation",
    },
    {
        "id": "agent-distribution",
        "selected": True,
        "origin": "origin/feat/continuous-knowledge",
        "origin_ref": "origin/feat/continuous-knowledge",
        "evidence": ["skills/docops-agent/SKILL.md", "docops/agent_skill.py", "scripts/install_agents_bootstrap.py"],
        "decision": "selectively port and package the agent-first skill and discovery seam",
    },
    {
        "id": "harness-and-router",
        "selected": True,
        "origin": "origin/feat/continuous-knowledge",
        "origin_ref": "origin/feat/continuous-knowledge",
        "evidence": ["docops/harness.py", "docops/templates/router.md", "docops/runtime.py"],
        "decision": "keep one generation-aware harness and router with documented aliases",
    },
    {
        "id": "mcp-read-only",
        "selected": True,
        "origin": "both-candidates",
        "origin_ref": "origin/feat/continuous-knowledge + working-tree",
        "evidence": ["skills/vendor/knowledge-rag/mcp_server/server.py", "docops/retrieval.py"],
        "decision": "enforce read-only sessions and isolate persistent reader state",
    },
    {
        "id": "continuous-knowledge-governance",
        "selected": True,
        "origin": "working-tree",
        "origin_ref": "local integration worktree",
        "evidence": ["docops/candidates.py", "docops/learning.py", "docops/feedback.py", "docops/authorization.py"],
        "decision": "retain review-first candidates, consent, revocation and independent evidence",
    },
    {
        "id": "release-gates",
        "selected": True,
        "origin": "consolidation",
        "origin_ref": "T12/T13",
        "evidence": ["scripts/run_release_gates.py", "scripts/verify_clean_clone.py", "scripts/verify_wheel.py"],
        "decision": "make clean-clone, wheel, platform and real MCP checks sequential and reproducible",
    },
)


def _git(root: Path, arguments: Iterable[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode:
        return None
    value = completed.stdout.strip()
    return value or None


def _safe_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _last_json_payload(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict):
        return payload
    for line in reversed(text.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _run_json_check(root: Path, python: Path, script: str, *arguments: str) -> dict[str, Any]:
    command = [str(python), str(root / "scripts" / script), *arguments, "--json"]
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() not in {"pythonpath", "pythonhome", "pythonioencoding", "pythonutf8"}
    }
    environment["PYTHONNOUSERSITE"] = "1"
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "returncode": None, "error": str(exc), "script": script}
    payload = _last_json_payload(completed.stdout)
    findings: list[Any] = []
    if isinstance(payload, dict):
        for key in ("findings", "errors", "unresolved"):
            value = payload.get(key)
            if isinstance(value, list):
                findings.extend(value)
    return {
        "ok": completed.returncode == 0 and (payload.get("ok") is True if payload else False),
        "returncode": completed.returncode,
        "script": script,
        "finding_count": len(findings),
    }


def _check_versioned_state(files: list[str]) -> dict[str, Any]:
    forbidden: list[str] = []
    for value in files:
        path = Path(value)
        normalized = path.as_posix()
        synthetic_document = normalized == "documents/README.md" or normalized.startswith(
            ("documents/examples/", "documents/fixtures/")
        )
        reviewed_vendor_data = normalized.startswith("skills/vendor/knowledge-rag/mcp_server/data/")
        forbidden_directory = any(part in FORBIDDEN_DIRECTORY_PARTS for part in path.parts)
        private_documents = "documents" in path.parts and not synthetic_document
        runtime_data = "data" in path.parts and not reviewed_vendor_data
        if path.name in FORBIDDEN_EXACT_FILES or forbidden_directory or private_documents or runtime_data:
            forbidden.append(path.as_posix())
    return {
        "ok": not forbidden,
        "candidate_file_count": len(files),
        "forbidden_paths": sorted(forbidden),
        "allowlist": ["synthetic documents/fixtures and documents/examples", "reviewed vendor configuration data"],
    }


def _source_comparison(root: Path, baseline_ref: str, remote_ref: str, head: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, ref in (("baseline", baseline_ref), ("remote_candidate", remote_ref)):
        commit = _git(root, ["rev-parse", "--verify", f"{ref}^{{commit}}"])
        if not commit:
            result[label] = {"ref": ref, "available": False, "commit": None, "commit_delta": []}
            continue
        # The three-dot form compares from the merge base and is empty when
        # HEAD is still at origin/main.  For a candidate report we need the
        # direct commit-to-commit delta, plus the tracked and untracked files
        # currently present in the working tree.
        commit_delta = _git(root, ["diff", "--name-status", commit, "HEAD"]) or ""
        tracked_delta = _git(root, ["diff", "--name-status", ref]) or ""
        staged_delta = _git(root, ["diff", "--cached", "--name-status", ref]) or ""
        untracked = _git(root, ["ls-files", "--others", "--exclude-standard"]) or ""
        working_delta = list(tracked_delta.splitlines())
        working_delta.extend(staged_delta.splitlines())
        working_delta.extend(f"??\t{line}" for line in untracked.splitlines())
        result[label] = {
            "ref": ref,
            "available": True,
            "commit": commit,
            "head": head,
            "commit_delta": commit_delta.splitlines(),
            "working_tree_delta": sorted(set(working_delta)),
        }
    return result


def _gate_report(path: Path | None, root: Path, current_commit: str | None) -> dict[str, Any]:
    if path is None:
        return {"ok": False, "status": "missing", "path": None, "errors": ["T12 gate report was not supplied"]}
    if not path.is_file() or path.is_symlink():
        return {
            "ok": False,
            "status": "unreadable",
            "path": _safe_path(path, root),
            "errors": ["T12 gate report is not a regular file"],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "invalid", "path": _safe_path(path, root), "errors": [str(exc)]}
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "status": "invalid",
            "path": _safe_path(path, root),
            "errors": ["gate report is not an object"],
        }
    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("gate report schema_version must be 1")
    if payload.get("profile") != "full":
        errors.append("T13 requires the full T12 profile")
    if payload.get("ok") is not True:
        errors.append("T12 report is not green")
    stages = payload.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("T12 report has no stages")
    else:
        for stage in stages:
            if not isinstance(stage, dict):
                errors.append("T12 report contains an invalid stage")
                continue
            if stage.get("required", True) is True and stage.get("status") != "passed":
                errors.append(f"required stage is not passed: {stage.get('name', '<unknown>')}")
            if stage.get("status") == "not-run":
                errors.append(f"stage was not run: {stage.get('name', '<unknown>')}")
    reported_commit = payload.get("source", {}).get("commit") if isinstance(payload.get("source"), dict) else None
    if reported_commit and current_commit and reported_commit != current_commit:
        errors.append("T12 gate report is bound to a different source commit")
    return {
        "ok": not errors,
        "status": "green" if not errors else "blocked",
        "path": _safe_path(path, root),
        "profile": payload.get("profile"),
        "reported_commit": reported_commit,
        "current_commit": current_commit,
        "stage_count": len(stages) if isinstance(stages, list) else 0,
        "errors": errors,
    }


def _bundle_report(root: Path, output: Path | None, python: Path) -> tuple[dict[str, Any], list[str]]:
    if output is None:
        return {"requested": False, "ok": True, "status": "not-requested"}, []
    command = [
        str(python),
        str(root / "scripts" / "prepare_candidate.py"),
        "--root",
        str(root),
        "--output",
        str(output),
        "--python",
        str(python),
        "--profile",
        "core",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"requested": True, "ok": False, "status": "failed", "error": str(exc)}, [
            "candidate bundle command could not run"
        ]
    payload = _last_json_payload(completed.stdout) or {}
    ok = completed.returncode == 0 and payload.get("ok") is True and (output / "candidate-manifest.json").is_file()
    errors = [] if ok else ["candidate bundle preparation failed"]
    return {
        "requested": True,
        "ok": ok,
        "status": "ready" if ok else "failed",
        "path": _safe_path(output, root),
        "version": payload.get("version"),
        "source_commit": payload.get("source_commit"),
        "errors": errors,
    }, errors


def _markdown(report: dict[str, Any]) -> str:
    candidate = report["candidate"]
    lines = [
        "# Integration candidate decision",
        "",
        f"- Technical readiness: **{'GREEN' if report['technical_ready'] else 'BLOCKED'}**",
        f"- Branch: `{candidate.get('branch') or '(detached)'}`",
        f"- Source commit: `{candidate.get('source_commit') or 'unavailable'}`",
        f"- Candidate files: `{candidate.get('file_count', 0)}`",
        "",
        "## Decision",
        "",
        "Promotion to `main` is **BLOCKED**. This report records no human authorization and performs no merge, push, release or publication.",
        "",
        "## Feature trace",
        "",
        "| Capability | Origin | Decision |",
        "|---|---|---|",
    ]
    for feature in report["feature_trace"]:
        lines.append(f"| `{feature['id']}` | `{feature['origin_ref']}` | {feature['decision']} |")
    lines.extend(["", "## Risks", ""])
    for risk in report["risks"]:
        lines.append(f"- `{risk['id']}` ({risk['severity']}, owner `{risk['owner']}`): {risk['decision']}")
    lines.extend(["", "## Gate summary", ""])
    for key, value in report["checks"].items():
        lines.append(f"- `{key}`: **{'pass' if value.get('ok') else 'block'}**")
    lines.extend(
        [
            "",
            "Rollback: delete the unpublished candidate bundle/report directory; no active generation was changed.",
            "",
        ]
    )
    return "\n".join(lines)


def build_report(
    *,
    root: Path,
    output: Path,
    gates_report: Path | None,
    baseline_ref: str,
    remote_ref: str,
    python: Path,
    bundle_output: Path | None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    output = output.expanduser().resolve()
    if output == root:
        raise RuntimeError("integration report output cannot be the repository root")
    if output.is_relative_to(root) and (root / ".git").exists():
        relative = output.relative_to(root).as_posix()
        ignored = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--quiet", "--no-index", "--", relative],
            check=False,
            capture_output=True,
        )
        if ignored.returncode != 0:
            raise RuntimeError("integration report output inside the repository must be ignored")
    files = git_files(root) or []
    digest = candidate_digest(root, files) if files else None
    current_commit = git_commit(root)
    identity = inspect_identity(root, files, digest or "", verify_remote=False) if files else {}
    source_state = _check_versioned_state(files)
    contract_check = _run_json_check(root, python, "check_contracts.py")
    documentation_check = _run_json_check(root, python, "check_documentation.py", "--root", str(root))
    schema_check = _run_json_check(root, python, "sync_schemas.py", "--check")
    lifecycle_path = root / "docops" / "lifecycle.py"
    lifecycle_text = lifecycle_path.read_text(encoding="utf-8", errors="replace") if lifecycle_path.is_file() else ""
    competing_lifecycle = (
        ["docops/lifecycle.py"] if lifecycle_path.is_file() and "class LifecycleFacade" not in lifecycle_text else []
    )
    architecture = {
        "ok": bool(lifecycle_text) and not competing_lifecycle and contract_check["ok"] and schema_check["ok"],
        "canonical_facade": "docops.LifecycleFacade",
        "canonical_cli": "docops lifecycle",
        "forbidden_competing_files": competing_lifecycle,
        "schema_distribution": schema_check,
    }
    compatibility = {
        "ok": contract_check["ok"] and (root / "docs" / "CONTRACT-COMPATIBILITY.md").is_file(),
        "contract_check": contract_check,
        "migration_map": "docs/CONTRACT-COMPATIBILITY.md",
        "aliases": ["docops lifecycle", "docops run", "docops validate", "docops evaluate"],
        "evidence": ["scripts/check_contracts.py", "docs/CONTRACT-COMPATIBILITY.md"],
    }
    gates = _gate_report(gates_report, root, current_commit)
    bundle, bundle_errors = _bundle_report(root, bundle_output, python)
    errors = list(gates.get("errors", [])) + bundle_errors
    checks = {
        "architecture": architecture,
        "compatibility": compatibility,
        "documentation": documentation_check,
        "schema_distribution": schema_check,
        "versioned_state": source_state,
        "t12_full_gates": gates,
        "candidate_bundle": bundle,
    }
    technical_ready = all(value.get("ok") is True for value in checks.values())
    worktree = worktree_status(root)
    risks = [
        {
            "id": "human-approval-missing",
            "owner": "release-maintainer",
            "severity": "high",
            "decision": "block-promotion until an external human authorization record names this candidate",
        },
        {
            "id": "working-tree-state",
            "owner": "integration-maintainer",
            "severity": "high" if worktree else "medium",
            "decision": "preserve current local work and require a clean reviewed commit before promotion",
        },
        {
            "id": "ci-identity",
            "owner": "release-maintainer",
            "severity": "medium",
            "decision": "require CI evidence bound to the candidate commit and digest during the human release step",
        },
        {
            "id": "private-corpus-or-runtime",
            "owner": "repository-maintainer",
            "severity": "critical",
            "decision": "exclude and block any candidate containing corpus, cache or runtime paths",
        },
    ]
    promotion_blockers = [
        risk["id"] for risk in risks if risk["id"] in {"human-approval-missing", "working-tree-state"}
    ]
    promotion_blockers.extend(errors)
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "docops-integration-candidate-report",
        "ok": technical_ready,
        "technical_ready": technical_ready,
        "candidate": {
            "branch": _git(root, ["branch", "--show-current"]),
            "source_commit": current_commit,
            "source_state": identity.get("state"),
            "candidate_digest": digest,
            "file_count": len(files),
            "worktree_entries": len(worktree or []),
            "identity": identity,
        },
        "source_comparison": _source_comparison(root, baseline_ref, remote_ref, current_commit),
        "feature_trace": [dict(feature) for feature in FEATURE_TRACE],
        "compatibility": compatibility,
        "versioned_state": source_state,
        "checks": checks,
        "risks": risks,
        "promotion_blockers": promotion_blockers,
        "promotion": {
            "performed": False,
            "status": "blocked",
            "target": "main",
            "requires_human_approval": True,
            "authorization_record": None,
        },
        "policy": {
            "merge": "not performed",
            "push": "not performed",
            "release": "not performed",
            "publication": "not performed",
            "active_corpus_or_rag_mutation": "not performed",
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "integration-candidate-report.json", report)
    (output / "integration-candidate-report.md").write_text(_markdown(report), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--gates-report", type=Path)
    parser.add_argument("--baseline-ref", default="origin/main")
    parser.add_argument("--remote-ref", default="origin/feat/continuous-knowledge")
    parser.add_argument("--bundle-output", type=Path)
    parser.add_argument("--no-bundle", action="store_true", help="report only; do not build a candidate bundle")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_report(
            root=args.root,
            output=args.output,
            gates_report=args.gates_report,
            baseline_ref=args.baseline_ref,
            remote_ref=args.remote_ref,
            python=args.python,
            bundle_output=None if args.no_bundle else args.bundle_output,
        )
    except (OSError, UnicodeError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "errors": [{"code": "candidate_report_failed", "message": str(exc)}],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
