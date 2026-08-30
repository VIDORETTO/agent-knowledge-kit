"""Command line entry point for the portable documentation operator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config_audit import audit_config_file
from .doctor import run_doctor
from .evaluator import evaluate_package, generate_golden_candidates
from .manifest import redact_metadata
from .package_validator import validate_package
from .pipeline import PipelineOptions, run_pipeline
from .source_resolver import SourceResolver


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docops")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="diagnose a clean clone")
    doctor.add_argument("--root", type=Path, default=Path.cwd())
    doctor.add_argument("--json", action="store_true", help="emit JSON")
    resolve = commands.add_parser("resolve", help="resolve a documentation source")
    resolve.add_argument("source")
    resolve.add_argument("--root", type=Path, default=Path.cwd())
    resolve.add_argument("--catalog", type=Path)
    resolve.add_argument("--version")
    resolve.add_argument("--scope")
    resolve.add_argument("--language")
    resolve.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="produce a knowledge package")
    run.add_argument("source")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--catalog", type=Path)
    run.add_argument("--slug")
    run.add_argument("--version")
    run.add_argument("--scope")
    run.add_argument("--language")
    run.add_argument("--mode", choices=("create", "update", "dry-run"), default="create")
    run.add_argument("--license", default=None)
    run.add_argument("--redistribution", default="private-only")
    run.add_argument("--index-rag", action="store_true")
    run.add_argument("--allow-private-network", action="store_true")
    run.add_argument("--max-pages", type=int, default=50)
    run.add_argument("--max-depth", type=int, default=2)
    run.add_argument("--include", dest="include_patterns", action="append", default=[])
    run.add_argument("--exclude", dest="exclude_patterns", action="append", default=[])
    run.add_argument("--json", action="store_true")
    validate = commands.add_parser("validate", help="validate a produced knowledge package")
    validate.add_argument("package", type=Path)
    validate.add_argument("--json", action="store_true")
    evaluate = commands.add_parser("evaluate", help="evaluate reviewed golden cases")
    evaluate.add_argument("--package", type=Path, required=True)
    evaluate.add_argument("--cases", type=Path, required=True)
    evaluate.add_argument("--recall-threshold", type=float, default=0.85)
    evaluate.add_argument("--mrr-threshold", type=float, default=0.7)
    evaluate.add_argument("--top-k", type=int, default=5)
    evaluate.add_argument("--json", action="store_true")
    candidates = commands.add_parser("golden-candidates", help="generate unreviewed golden candidates")
    candidates.add_argument("package", type=Path)
    candidates.add_argument("--limit", type=int, default=20)
    candidates.add_argument("--json", action="store_true")
    config_audit = commands.add_parser("config-audit", help="audit MCP transport security")
    config_audit.add_argument("config", type=Path)
    config_audit.add_argument("--json", action="store_true")
    return parser


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        report = run_doctor(args.root)
        if args.json:
            print(report.to_json())
        else:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0 if report.ok else 1
    if args.command == "resolve":
        resolver = SourceResolver.from_catalog_file(args.catalog, root=args.root) if args.catalog else SourceResolver(root=args.root)
        resolution = resolver.resolve(args.source, version=args.version, scope=args.scope, language=args.language)
        print(json.dumps(redact_metadata(resolution.to_dict()), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if resolution.selected is not None and not resolution.requires_decision else 2
    if args.command == "run":
        result = run_pipeline(
            args.source,
            options=PipelineOptions(
                output_dir=args.output,
                catalog=args.catalog,
                slug=args.slug,
                version=args.version,
                scope=args.scope,
                language=args.language,
                mode=args.mode,
                license=args.license,
                redistribution=args.redistribution,
                index_rag=args.index_rag,
                allow_private_network=args.allow_private_network,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                include_patterns=tuple(args.include_patterns),
                exclude_patterns=tuple(args.exclude_patterns),
            ),
        )
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result.ok else 1
    if args.command == "validate":
        result = validate_package(args.package)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result.ok else 1
    if args.command == "evaluate":
        metric_top_k = args.top_k if 1 <= args.top_k <= 100 else 5
        result = evaluate_package(
            args.package,
            args.cases,
            thresholds={f"recall_at_{metric_top_k}": args.recall_threshold, f"mrr_at_{metric_top_k}": args.mrr_threshold},
            top_k=args.top_k,
        )
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result.ok else 1
    if args.command == "golden-candidates":
        print(json.dumps({"schema_version": 1, "reviewed": False, "cases": generate_golden_candidates(args.package, limit=args.limit)}, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "config-audit":
        try:
            result = audit_config_file(args.config)
        except (OSError, ValueError) as exc:
            print(json.dumps({"schema_version": 1, "ok": False, "errors": [{"code": "config_unreadable", "message": str(exc)}]}, indent=2, ensure_ascii=False))
            return 1
        print(result.to_json())
        return 0 if result.ok else 1
    return 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "ok": False,
                    "errors": [{"code": "invalid_request", "message": str(exc)}],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
