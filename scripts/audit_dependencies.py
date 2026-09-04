"""Run the dependency audit with a narrowly documented Chroma exception.

The project uses ChromaDB only through its local ``PersistentClient``. It does
not expose Chroma's HTTP API, enable ``trust_remote_code`` or accept a remote
model repository through the MCP surface. The four currently published
Chroma advisories therefore remain a tracked residual risk, not an ignored
unknown. Any other finding, including a future Chroma advisory, fails the
gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import site
import subprocess
import sys
from pathlib import Path
from typing import Any

CHROMA_RESIDUAL_CVES = frozenset(
    {
        "CVE-2026-45829",
        "CVE-2026-45830",
        "CVE-2026-45831",
        "CVE-2026-45833",
    }
)


def _audit_command(*, requirements: Path | None = None, local: bool = False) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "--format",
        "json",
        "--progress-spinner",
        "off",
    ]
    if requirements is not None:
        command.extend(["--requirement", str(requirements), "--strict"])
    if local:
        command.append("--skip-editable")
        for path in site.getsitepackages():
            command.extend(["--path", path])
    return command


def _run_audit(*, requirements: Path | None = None, local: bool = False) -> dict[str, Any]:
    completed = subprocess.run(
        _audit_command(requirements=requirements, local=local),
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"pip-audit did not return JSON\nstdout: {completed.stdout[-2000:]}\nstderr: {completed.stderr[-2000:]}"
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("dependencies"), list):
        raise RuntimeError("pip-audit returned an unexpected JSON shape")
    return {
        "source": "local" if local else "requirements",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        **payload,
    }


def _finding_key(dependency: dict[str, Any], vulnerability: dict[str, Any]) -> tuple[str, str]:
    identifiers = [str(vulnerability.get("id", ""))]
    identifiers.extend(str(alias) for alias in vulnerability.get("aliases", []))
    return str(dependency.get("name", "")).lower(), next((item for item in identifiers if item), "unknown")


def _classify(audits: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    residual: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for audit in audits:
        for dependency in audit["dependencies"]:
            for vulnerability in dependency.get("vulns", []):
                package_name, identifier = _finding_key(dependency, vulnerability)
                aliases = {identifier, *(str(alias) for alias in vulnerability.get("aliases", []))}
                key = (package_name, next(iter(sorted(aliases))))
                if key in seen:
                    continue
                seen.add(key)
                finding = {
                    "package": dependency.get("name"),
                    "version": dependency.get("version"),
                    "id": vulnerability.get("id"),
                    "aliases": vulnerability.get("aliases", []),
                    "fix_versions": vulnerability.get("fix_versions", []),
                    "description": vulnerability.get("description", ""),
                }
                if (
                    package_name == "chromadb"
                    and dependency.get("version") == "1.5.9"
                    and aliases & CHROMA_RESIDUAL_CVES
                ):
                    residual.append(finding)
                else:
                    unresolved.append(finding)
    return residual, unresolved


def _raw_findings(audits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve the auditor's findings before policy classification."""

    findings: list[dict[str, Any]] = []
    for audit in audits:
        for dependency in audit.get("dependencies", []):
            for vulnerability in dependency.get("vulns", []):
                if not isinstance(vulnerability, dict):
                    continue
                findings.append(
                    {
                        "source": audit.get("source"),
                        "package": dependency.get("name"),
                        "version": dependency.get("version"),
                        "id": vulnerability.get("id"),
                        "aliases": vulnerability.get("aliases", []),
                        "fix_versions": vulnerability.get("fix_versions", []),
                        "description": vulnerability.get("description", ""),
                    }
                )
    return findings


def _write_raw_evidence(directory: Path, audits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    directory.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    for audit in audits:
        source = str(audit["source"])
        stdout_name = f"{source}.stdout.json"
        stderr_name = f"{source}.stderr.log"
        exit_name = f"{source}.exit-code"
        stdout = str(audit.get("stdout", ""))
        stderr = str(audit.get("stderr", ""))
        (directory / stdout_name).write_text(stdout, encoding="utf-8")
        (directory / stderr_name).write_text(stderr, encoding="utf-8")
        (directory / exit_name).write_text(f"{audit['exit_code']}\n", encoding="ascii")
        summaries.append(
            {
                "source": source,
                "exit_code": audit["exit_code"],
                "evidence": {
                    "stdout": stdout_name,
                    "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
                    "stderr": stderr_name,
                    "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
                    "exit_code": exit_name,
                },
            }
        )
    return summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, required=True, help="requirements file to resolve and audit")
    parser.add_argument("--local", action="store_true", help="also audit the active interpreter environment")
    parser.add_argument("--strict", action="store_true", help="fail on any finding outside the documented residual set")
    parser.add_argument("--evidence-dir", type=Path, help="preserve raw stdout, stderr and exit codes")
    args = parser.parse_args(argv)

    requirements = args.requirements.expanduser().resolve()
    if not requirements.is_file():
        print(json.dumps({"ok": False, "error": f"requirements file not found: {requirements}"}, ensure_ascii=False))
        return 2

    audits = [_run_audit(requirements=requirements)]
    if args.local:
        audits.append(_run_audit(local=True))
    residual, unresolved = _classify(audits)
    raw_findings = _raw_findings(audits)
    collection_failed = any(audit["exit_code"] not in {0, 1} for audit in audits)
    audit_summaries = (
        _write_raw_evidence(args.evidence_dir.expanduser().resolve(), audits)
        if args.evidence_dir is not None
        else [{"source": audit["source"], "exit_code": audit["exit_code"]} for audit in audits]
    )
    result = {
        "ok": not collection_failed and not unresolved,
        "audits": audit_summaries,
        "raw_audit": {
            "status": "clean" if not raw_findings and not collection_failed else "findings",
            "ok": not collection_failed and not raw_findings,
            "findings": raw_findings,
        },
        "residual": residual,
        "unresolved": unresolved,
        "policy_evaluation": {
            "status": "pass" if not collection_failed and not unresolved else "fail",
            "ok": not collection_failed and not unresolved,
            "residual_count": len(residual),
            "unresolved_count": len(unresolved),
        },
        "policy": {
            "allowed_package": "chromadb",
            "allowed_ids": sorted(CHROMA_RESIDUAL_CVES),
            "reason": "local PersistentClient only; Chroma HTTP API, remote model repositories and trust_remote_code are not part of this product path",
        },
    }
    if args.evidence_dir is not None:
        (args.evidence_dir.expanduser().resolve() / "summary.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    if collection_failed:
        return 2
    return 0 if result["ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
