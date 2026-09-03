"""Exercise search calls while knowledge-rag performs a background reindex."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docops.mcp_client import first_json_payload, start_mcp_server  # noqa: E402
from docops.observability import redact_report, redact_text  # noqa: E402
from docops.runtime import discover_rag_python, runtime_environment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=20.0)
    args = parser.parse_args()
    package = args.package.expanduser().resolve()
    executable = discover_rag_python(ROOT).path
    if not executable.is_file():
        print(json.dumps({"ok": False, "skipped": True, "code": "rag_python_missing"}))
        return 2
    primary = load = None
    searches = 0
    errors: list[str] = []
    reindex: dict[str, object] = {}
    try:
        environment = runtime_environment(package, vendor_root=ROOT)
        primary = start_mcp_server(executable, package, env=environment)
        load = start_mcp_server(executable, package, env=environment)
        reindex_response = primary.call("tools/call", name="reindex_documents", arguments={"force": True}, timeout=120)
        reindex = first_json_payload(reindex_response) or {}
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            search_response = load.call(
                "tools/call",
                name="search_knowledge",
                arguments={"query": "documentation", "max_results": 1},
                timeout=120,
            )
            if search_response.get("error"):
                errors.append(redact_text(search_response["error"]))
            else:
                searches += 1
            status_response = primary.call("tools/call", name="get_reindex_status", arguments={}, timeout=120)
            status_payload = first_json_payload(status_response) or {}
            status = (
                status_payload.get("reindex") if isinstance(status_payload.get("reindex"), dict) else status_payload
            )
            if not status.get("active", False):
                reindex = status
                break
            time.sleep(0.25)
    except (OSError, RuntimeError, TimeoutError) as exc:
        errors.append(redact_text(exc))
    finally:
        if load is not None:
            load.close()
        if primary is not None:
            primary.close()
    payload = redact_report(
        {"ok": not errors and searches > 0, "searches": searches, "errors": errors, "reindex": reindex}
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
