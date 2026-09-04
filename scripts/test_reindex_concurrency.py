"""Exercise search calls while knowledge-rag performs a background reindex."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docops.mcp_client import first_json_payload, start_mcp_server  # noqa: E402
from docops.observability import exception_diagnostic, redact_report  # noqa: E402
from docops.runtime import discover_rag_python, runtime_environment  # noqa: E402


def _runtime_environment_for_package(package: Path) -> dict[str, str]:
    """Start the stress workload with the reviewed backend used by DOCOPS."""

    vendor = ROOT / "skills" / "vendor" / "knowledge-rag"
    return runtime_environment(package, vendor_root=vendor)


def _gate_event(code: str) -> dict[str, object]:
    return {"code": code, "severity": "error", "category": "stress", "redacted": True}


def safe_reindex_status(status: Mapping[str, object]) -> dict[str, object]:
    """Summarize terminal reindex state without retaining backend details."""

    active = status.get("active")
    if active is True:
        return {"active": True, "status": "running", "error_count": None}
    if active is not False:
        return {"active": active, "status": "incomplete", "error_count": None}
    if status.get("last_error"):
        return {"active": False, "status": "failed", "error_count": None}
    result = status.get("last_result")
    if not isinstance(result, Mapping):
        return {"active": False, "status": "incomplete", "error_count": None}
    errors = result.get("errors")
    error_count = errors if isinstance(errors, int) and not isinstance(errors, bool) else None
    terminal_status = "succeeded" if error_count == 0 else "failed"
    return {"active": False, "status": terminal_status, "error_count": error_count}


def stress_gate_findings(
    *,
    errors: list[object],
    warnings: list[object],
    searches: int,
    min_searches: int,
    reindex: Mapping[str, object],
    final_state: Mapping[str, object],
    final_index: Mapping[str, object],
) -> list[dict[str, object]]:
    """Return fail-closed findings for the public stress-report signals."""

    findings: list[dict[str, object]] = []
    if errors:
        findings.append(_gate_event("stress_errors_present"))
    if warnings:
        findings.append(_gate_event("stress_warnings_present"))
    if searches < min_searches:
        findings.append(_gate_event("stress_load_below_minimum"))
    recovery = final_state.get("recovery")
    if (
        final_state.get("managed") is not True
        or not isinstance(recovery, Mapping)
        or recovery.get("status") != "stable"
    ):
        findings.append(_gate_event("stress_final_state_invalid"))
    if not all(
        isinstance(final_index.get(key), int)
        and not isinstance(final_index.get(key), bool)
        and final_index.get(key, 0) > 0
        for key in ("backend_total_documents", "backend_total_chunks")
    ):
        findings.append(_gate_event("stress_final_index_invalid"))
    residue_counts = final_state.get("residue_counts")
    residue_keys = ("staging", "backups", "recoverable_attempts", "attempts")
    if isinstance(residue_counts, Mapping) and any(
        isinstance(residue_counts.get(key), int)
        and not isinstance(residue_counts.get(key), bool)
        and residue_counts.get(key, 0) > 0
        for key in residue_keys
    ):
        findings.append(_gate_event("stress_residue_present"))
    if reindex.get("active") is not False:
        findings.append(_gate_event("reindex_not_terminal"))
    elif reindex.get("status") != "succeeded" or reindex.get("error_count") != 0:
        findings.append(_gate_event("reindex_failed"))
    return findings


def recoverable_residue_counts(residues: object) -> dict[str, int]:
    """Separate recovery residue from retained attempt audit history."""

    values = residues if isinstance(residues, Mapping) else {}
    staging = values.get("staging")
    backups = values.get("backups")
    attempts = values.get("attempts")
    attempt_values = attempts if isinstance(attempts, list) else []
    recoverable_attempts = 0
    for attempt in attempt_values:
        if not isinstance(attempt, Mapping):
            recoverable_attempts += 1
            continue
        attempt_staging = attempt.get("staging")
        outcome = attempt.get("outcome")
        staging_present = isinstance(attempt_staging, Mapping) and attempt_staging.get("present") is True
        terminal_success = (
            isinstance(outcome, Mapping) and outcome.get("status") == "succeeded" and outcome.get("code") == "completed"
        )
        if staging_present or not terminal_success:
            recoverable_attempts += 1
    return {
        "staging": len(staging) if isinstance(staging, list) else 0,
        "backups": len(backups) if isinstance(backups, list) else 0,
        "recoverable_attempts": recoverable_attempts,
        "attempt_records": len(attempt_values),
    }


def _mcp_error(response: object) -> str | None:
    if not isinstance(response, dict):
        return "mcp_response_invalid"
    error = response.get("error")
    if error:
        return "mcp_protocol_error"
    result = response.get("result")
    if isinstance(result, dict) and result.get("isError") is True:
        return "mcp_tool_error"
    return None


def _search_error(response: object) -> str | None:
    protocol_error = _mcp_error(response)
    if protocol_error:
        return protocol_error
    payload = first_json_payload(response) if isinstance(response, Mapping) else None
    if not isinstance(payload, Mapping):
        return "search_payload_invalid"
    if payload.get("status") == "error":
        return "search_backend_error"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--readers", type=int, default=4)
    parser.add_argument(
        "--min-searches",
        type=int,
        default=40,
        help="minimum successful searches across concurrent readers before the workload can pass",
    )
    args = parser.parse_args()
    if args.seconds <= 0 or args.readers < 1 or args.min_searches < 1:
        print(json.dumps({"ok": False, "code": "invalid_load_parameters"}))
        return 2
    package = args.package.expanduser().resolve()
    executable = discover_rag_python(ROOT).path
    if not executable.is_file():
        print(json.dumps({"ok": False, "skipped": True, "code": "rag_python_missing"}))
        return 2
    primary = None
    readers = []
    threads: list[threading.Thread] = []
    searches = 0
    warmup_searches = 0
    errors: list[str] = []
    warnings: list[str] = []
    reindex: dict[str, object] = {}
    final_index: dict[str, object] = {}
    counter_lock = threading.Lock()
    stop = threading.Event()
    request_timeout = max(1.0, min(5.0, args.seconds))
    try:
        environment = _runtime_environment_for_package(package)
        primary = start_mcp_server(executable, package, env=environment)
        readers = [start_mcp_server(executable, package, env=environment) for _ in range(args.readers)]
        # Initialization is intentionally lazy in knowledge-rag. Establish an
        # operational reader barrier before the writer starts so the measured
        # failures represent reindex concurrency rather than model cold-start.
        for client in readers:
            warmup_response = client.call(
                "tools/call",
                name="search_knowledge",
                arguments={"query": "documentation", "max_results": 1},
                timeout=max(30.0, request_timeout),
            )
            warmup_error = _search_error(warmup_response)
            if warmup_error:
                raise RuntimeError(f"reader warmup failed: {warmup_error}")
            warmup_searches += 1
        deadline = time.monotonic() + args.seconds

        def search_worker(client: object) -> None:
            nonlocal searches
            while not stop.is_set() and time.monotonic() < deadline:
                try:
                    response = client.call(  # type: ignore[attr-defined]
                        "tools/call",
                        name="search_knowledge",
                        arguments={"query": "documentation", "max_results": 1},
                        timeout=request_timeout,
                    )
                except (OSError, RuntimeError, TimeoutError) as exc:
                    with counter_lock:
                        errors.append(exception_diagnostic(exc, fallback_code="search_failed"))
                    continue
                with counter_lock:
                    search_error = _search_error(response)
                    if search_error:
                        errors.append(search_error)
                    else:
                        searches += 1

        for client in readers:
            thread = threading.Thread(target=search_worker, args=(client,), daemon=True)
            thread.start()
            threads.append(thread)
        reindex_response = primary.call(
            "tools/call", name="reindex_documents", arguments={"force": True}, timeout=request_timeout
        )
        if _mcp_error(reindex_response):
            raise RuntimeError("reindex request returned an MCP error")
        reindex = first_json_payload(reindex_response) or {}
        if not reindex:
            warnings.append("backend returned an unstructured reindex start response")
        while time.monotonic() < deadline:
            status_response = primary.call(
                "tools/call", name="get_reindex_status", arguments={}, timeout=request_timeout
            )
            if _mcp_error(status_response):
                raise RuntimeError("reindex status returned an MCP error")
            status_payload = first_json_payload(status_response) or {}
            status = (
                status_payload.get("reindex") if isinstance(status_payload.get("reindex"), dict) else status_payload
            )
            if isinstance(status, dict):
                reindex = status
            else:
                warnings.append("backend returned an unstructured reindex status")
            time.sleep(0.25)
        stop.set()
        for thread in threads:
            thread.join(timeout=5)
        final_response = primary.call("tools/call", name="get_reindex_status", arguments={}, timeout=request_timeout)
        if _mcp_error(final_response):
            raise RuntimeError("final reindex status returned an MCP error")
        final_payload = first_json_payload(final_response) or {}
        final_state = final_payload.get("reindex") if isinstance(final_payload.get("reindex"), dict) else final_payload
        if isinstance(final_state, dict):
            reindex = final_state
        elif final_state:
            warnings.append("backend returned an unstructured final reindex status")
        if not isinstance(final_state, dict) or final_state.get("active") is not False:
            errors.append("reindex did not reach a terminal inactive state")
        stats_response = primary.call("tools/call", name="get_index_stats", arguments={}, timeout=request_timeout)
        if _mcp_error(stats_response):
            raise RuntimeError("final index stats returned an MCP error")
        stats_payload = first_json_payload(stats_response) or {}
        stats = stats_payload.get("stats") if isinstance(stats_payload.get("stats"), dict) else stats_payload
        if not isinstance(stats, dict):
            errors.append("backend returned unstructured final index stats")
        else:
            final_index = {
                "backend_total_documents": stats.get("total_documents"),
                "backend_total_chunks": stats.get("total_chunks"),
            }
            if not all(isinstance(value, int) for value in final_index.values()):
                errors.append("backend final index stats are missing named totals")
            try:
                package_index = json.loads((package / "rag" / "index.json").read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                package_index = {}
            expected_index = {
                key: package_index.get(key) for key in ("backend_total_documents", "backend_total_chunks")
            }
            if expected_index != final_index:
                errors.append("backend final index stats differ from package metrics")
    except (OSError, RuntimeError, TimeoutError) as exc:
        errors.append(exception_diagnostic(exc, fallback_code="stress_operation_failed"))
    finally:
        stop.set()
        for thread in threads:
            thread.join(timeout=5)
        for client in readers:
            client.close()
        if primary is not None:
            primary.close()
    final_report: dict[str, object] = {}
    try:
        import docops

        inspection = docops.inspect(package)
        final_report = {
            "managed": inspection.get("managed"),
            "recovery": inspection.get("recovery"),
            "index": final_index,
            "residue_counts": recoverable_residue_counts(inspection.get("residues", {})),
        }
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(exception_diagnostic(exc, fallback_code="final_inspection_failed"))
    safe_reindex = safe_reindex_status(reindex)
    gate_findings = stress_gate_findings(
        errors=errors,
        warnings=warnings,
        searches=searches,
        min_searches=args.min_searches,
        reindex=safe_reindex,
        final_state=final_report,
        final_index=final_index,
    )
    payload = redact_report(
        {
            "ok": not gate_findings,
            "readers": args.readers,
            "seconds": args.seconds,
            "min_searches": args.min_searches,
            "searches": searches,
            "warmup_searches": warmup_searches,
            "errors": errors,
            "warnings": warnings,
            "gate_findings": gate_findings,
            "reindex": safe_reindex,
            "final_index": final_index,
            "final_state": final_report,
        }
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
