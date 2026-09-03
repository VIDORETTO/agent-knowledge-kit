"""Check normative DOCOPS schemas against representative public envelopes."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docops import OperationOptions  # noqa: E402
from docops.contracts import contract_names, load_schema, schema_path, validate_artifact  # noqa: E402
from docops.harness import build_harness_manifest  # noqa: E402
from docops.manifest import build_manifest  # noqa: E402
from docops.operations import plan as build_plan  # noqa: E402
from docops.package_validator import ValidationResult  # noqa: E402
from docops.source_resolver import SourceResolver  # noqa: E402


def _examples() -> dict[str, object]:
    resolution = SourceResolver().resolve("https://docs.example.test/guide")
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "source.md"
        source.write_text("# Guide\n", encoding="utf-8")
        operation = build_plan(
            source,
            options=OperationOptions(output_dir=Path(temporary) / "package", slug="guide", license="MIT"),
        )
        plan_example = operation.to_dict()
    return {
        "manifest": build_manifest(
            resolution,
            entries=[],
            provenance={"license": "MIT", "redistribution": "private-only"},
            artifacts={"skill": "skill", "router": "router", "rag": "rag"},
        ),
        "harness": build_harness_manifest(ROOT),
        "golden": {
            "schema_version": 1,
            "reviewed": True,
            "cases": [{"query": "guide", "expected_filepath": "guide.md", "reviewed": True}],
        },
        "validation": ValidationResult(True).to_dict(),
        "outcome": {"status": "succeeded", "code": "completed", "phase": "validate", "message": "ok", "exit_code": 0},
        "plan": plan_example,
        "result": {
            "schema_version": 1,
            "ok": True,
            "outcome": {
                "status": "succeeded",
                "code": "completed",
                "phase": "validate",
                "message": "ok",
                "exit_code": 0,
            },
            "manifest": {},
            "validation": ValidationResult(True).to_dict(),
            "state_diff": {"added": 0, "updated": 0, "removed": 0},
            "written_files": 0,
            "errors": [],
            "warnings": [],
        },
        "evaluation": {
            "schema_version": 1,
            "ok": True,
            "metrics": {"recall_at_5": 1.0, "mrr_at_5": 1.0},
            "cases": [],
            "errors": [],
            "warnings": [],
            "diagnostics": [],
            "thresholds": {"recall_at_5": 0.85, "mrr_at_5": 0.7},
            "metadata": {"backend": "memory", "mode": "test"},
        },
        "golden-candidates": {
            "schema_version": 1,
            "reviewed": False,
            "cases": [{"query": "guide", "expected_filepath": "guide.md", "reviewed": False, "review_note": "review"}],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.parse_args(argv)
    findings: list[dict[str, str]] = []
    for name in contract_names():
        try:
            load_schema(name)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            findings.append({"code": "schema_unavailable", "artifact": name, "message": str(exc)})
    examples = _examples()
    for name, payload in examples.items():
        if name not in contract_names():
            continue
        result = validate_artifact(name, payload)
        if not result.ok:
            findings.extend(
                {"code": error["code"], "artifact": name, "message": error["message"]} for error in result.errors
            )
        if isinstance(payload, dict):
            required = load_schema(name).get("required", [])
            if isinstance(required, list) and required:
                invalid = copy.deepcopy(payload)
                invalid.pop(required[0], None)
                if validate_artifact(name, invalid).ok:
                    findings.append(
                        {
                            "code": "negative_fixture_accepted",
                            "artifact": name,
                            "message": f"removing {required[0]!r} must fail",
                        }
                    )
        package_schema = ROOT / "docops" / "schemas" / Path(schema_path(name) or "").name
        checkout_schema = ROOT / "schemas" / Path(schema_path(name) or "").name
        try:
            schema_matches = package_schema.is_file() and json.loads(
                package_schema.read_text(encoding="utf-8")
            ) == json.loads(checkout_schema.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            schema_matches = False
        if not schema_matches:
            findings.append(
                {"code": "schema_drift", "artifact": name, "message": "bundled and checkout schemas differ"}
            )
    report = {"schema_version": 1, "ok": not findings, "artifacts": list(contract_names()), "findings": findings}
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
