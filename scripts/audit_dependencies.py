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
    return {"source": "local" if local else str(requirements), "exit_code": completed.returncode, **payload}


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
                if package_name == "chromadb" and aliases & CHROMA_RESIDUAL_CVES:
                    residual.append(finding)
                else:
                    unresolved.append(finding)
    return residual, unresolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, required=True, help="requirements file to resolve and audit")
    parser.add_argument("--local", action="store_true", help="also audit the active interpreter environment")
    parser.add_argument("--strict", action="store_true", help="fail on any finding outside the documented residual set")
    args = parser.parse_args(argv)

    requirements = args.requirements.expanduser().resolve()
    if not requirements.is_file():
        print(json.dumps({"ok": False, "error": f"requirements file not found: {requirements}"}, ensure_ascii=False))
        return 2

    audits = [_run_audit(requirements=requirements)]
    if args.local:
        audits.append(_run_audit(local=True))
    residual, unresolved = _classify(audits)
    collection_failed = any(audit["exit_code"] not in {0, 1} for audit in audits)
    result = {
        "ok": not collection_failed and not unresolved,
        "audits": [{"source": audit["source"], "exit_code": audit["exit_code"]} for audit in audits],
        "residual": residual,
        "unresolved": unresolved,
        "policy": {
            "allowed_package": "chromadb",
            "allowed_ids": sorted(CHROMA_RESIDUAL_CVES),
            "reason": "local PersistentClient only; Chroma HTTP API, remote model repositories and trust_remote_code are not part of this product path",
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    if collection_failed:
        return 2
    return 0 if result["ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
