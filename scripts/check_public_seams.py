"""Enforce that implementation imports in tests are explicitly classified."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

_SCOPE = re.compile(r"^# seam-scope: (?:implementation|compatibility)-infrastructure \([^()\r\n]+\)$")


def _has_internal_import(text: str) -> bool:
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name.startswith("docops.") for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and isinstance(node.module, str) and node.module.startswith("docops."):
            return True
    return False


def audit(tests_root: Path) -> dict[str, object]:
    findings: list[dict[str, str]] = []
    for path in sorted(tests_root.rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        header = text.splitlines()[:12]
        declared_scopes = [line for line in header if line.startswith("# seam-scope:")]
        if declared_scopes and not any(_SCOPE.fullmatch(line) for line in declared_scopes):
            findings.append(
                {
                    "code": "invalid_seam_scope",
                    "file": path.as_posix(),
                    "message": "seam-scope must classify an implementation or compatibility infrastructure fixture",
                }
            )
        elif _has_internal_import(text) and not any(_SCOPE.fullmatch(line) for line in declared_scopes):
            findings.append(
                {
                    "code": "unclassified_internal_import",
                    "file": path.as_posix(),
                    "message": "implementation imports require an explicit seam-scope classification",
                }
            )
    return {"schema_version": 1, "ok": not findings, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", type=Path, default=Path(__file__).resolve().parents[1] / "tests")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = audit(args.tests.expanduser().resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
