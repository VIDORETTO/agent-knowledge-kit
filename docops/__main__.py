"""Command line entry point for the portable documentation operator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config_audit import audit_config_file
from .contracts import validate_artifact
from .doctor import run_doctor
from .evaluator import evaluate_package, generate_golden_candidates
from .lifecycle import LifecycleStore, prepare_candidate, reconcile_source, work_once
from .manifest import redact_metadata
from .observability import redact_report, redact_text
from .operations import OperationOptions, preview
from .operations import apply as apply_operation
from .operations import cleanup as cleanup_residue
from .operations import plan as build_plan
from .package_validator import validate_package
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
    plan = commands.add_parser("plan", help="plan a package operation without writing artifacts")
    plan.add_argument("source")
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--catalog", type=Path)
    plan.add_argument("--slug")
    plan.add_argument("--version")
    plan.add_argument("--scope")
    plan.add_argument("--language")
    plan.add_argument("--mode", choices=("create", "update", "run", "dry-run"), default="run")
    plan.add_argument("--license", default=None)
    plan.add_argument("--redistribution", default="private-only")
    plan.add_argument("--index-rag", action="store_true")
    plan.add_argument("--allow-private-network", action="store_true")
    plan.add_argument("--max-pages", type=int, default=50)
    plan.add_argument("--max-depth", type=int, default=2)
    plan.add_argument("--include", dest="include_patterns", action="append", default=[])
    plan.add_argument("--exclude", dest="exclude_patterns", action="append", default=[])
    plan.add_argument("--runtime-root", type=Path)
    plan.add_argument("--source-root", type=Path)
    plan.add_argument("--lease-policy", choices=("fail", "wait"), default="fail")
    plan.add_argument("--lease-timeout-seconds", type=float, default=0.0)
    plan.add_argument("--stale-lease-seconds", type=float, default=300.0)
    plan.add_argument("--json", action="store_true")
    run = commands.add_parser("run", help="produce a knowledge package")
    run.add_argument("source")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--catalog", type=Path)
    run.add_argument("--slug")
    run.add_argument("--version")
    run.add_argument("--scope")
    run.add_argument("--language")
    run.add_argument("--mode", choices=("create", "update", "run", "dry-run"), default="run")
    run.add_argument("--license", default=None)
    run.add_argument("--redistribution", default="private-only")
    run.add_argument("--index-rag", action="store_true")
    run.add_argument("--allow-private-network", action="store_true")
    run.add_argument("--max-pages", type=int, default=50)
    run.add_argument("--max-depth", type=int, default=2)
    run.add_argument("--include", dest="include_patterns", action="append", default=[])
    run.add_argument("--exclude", dest="exclude_patterns", action="append", default=[])
    run.add_argument("--runtime-root", type=Path)
    run.add_argument("--source-root", type=Path)
    run.add_argument("--lease-policy", choices=("fail", "wait"), default="fail")
    run.add_argument("--lease-timeout-seconds", type=float, default=0.0)
    run.add_argument("--stale-lease-seconds", type=float, default=300.0)
    run.add_argument("--json", action="store_true")
    validate = commands.add_parser("validate", help="validate a produced knowledge package")
    validate.add_argument("package", type=Path)
    validate.add_argument("--json", action="store_true")
    cleanup = commands.add_parser("cleanup", help="remove expired operation residue safely")
    cleanup.add_argument("package", type=Path)
    cleanup.add_argument("--retention-seconds", type=float, default=7 * 24 * 60 * 60)
    cleanup.add_argument("--keep-attempts", type=int, default=20)
    cleanup.add_argument("--json", action="store_true")
    evaluate = commands.add_parser("evaluate", help="evaluate reviewed golden cases")
    evaluate.add_argument("--package", type=Path, required=True)
    evaluate.add_argument("--cases", type=Path, required=True)
    evaluate.add_argument("--recall-threshold", type=float, default=0.85)
    evaluate.add_argument("--mrr-threshold", type=float, default=0.7)
    evaluate.add_argument("--top-k", type=int, default=5)
    evaluate.add_argument("--adapter", choices=("lexical", "memory", "mcp"), default="lexical")
    evaluate.add_argument("--runtime-root", type=Path)
    evaluate.add_argument("--json", action="store_true")
    candidates = commands.add_parser("golden-candidates", help="generate unreviewed golden candidates")
    candidates.add_argument("package", type=Path)
    candidates.add_argument("--limit", type=int, default=20)
    candidates.add_argument("--json", action="store_true")
    config_audit = commands.add_parser("config-audit", help="audit MCP transport security")
    config_audit.add_argument("config", type=Path)
    config_audit.add_argument("--json", action="store_true")

    lifecycle = commands.add_parser("lifecycle", help="coordinate candidates, jobs and reviewed learning")
    lifecycle_commands = lifecycle.add_subparsers(dest="lifecycle_command", required=True)

    status = lifecycle_commands.add_parser("status", help="show private lifecycle counters")
    status.add_argument("--package", type=Path, required=True)
    status.add_argument("--runtime-root", type=Path)
    status.add_argument("--json", action="store_true")

    source = lifecycle_commands.add_parser("source", help="manage the source registry")
    source_commands = source.add_subparsers(dest="source_command", required=True)
    register = source_commands.add_parser("register")
    register.add_argument("--package", type=Path, required=True)
    register.add_argument("--runtime-root", type=Path)
    register.add_argument("--source-id", required=True)
    register.add_argument("--canonical", required=True)
    register.add_argument("--kind", default="local")
    register.add_argument("--scope")
    register.add_argument("--version-policy", default="explicit")
    register.add_argument("--language")
    register.add_argument("--owner", required=True)
    register.add_argument("--status", default="admitted")
    register.add_argument("--json", action="store_true")
    reconcile = source_commands.add_parser("reconcile")
    reconcile.add_argument("--package", type=Path, required=True)
    reconcile.add_argument("--runtime-root", type=Path)
    reconcile.add_argument("--source", required=True)
    reconcile.add_argument("--source-root", type=Path)
    reconcile.add_argument("--slug")
    reconcile.add_argument("--version")
    reconcile.add_argument("--scope")
    reconcile.add_argument("--language")
    reconcile.add_argument("--license")
    reconcile.add_argument("--index-rag", action="store_true")
    reconcile.add_argument("--json", action="store_true")

    event = lifecycle_commands.add_parser("event", help="submit a debounced source event")
    event_commands = event.add_subparsers(dest="event_command", required=True)
    submit_event = event_commands.add_parser("submit")
    submit_event.add_argument("--package", type=Path, required=True)
    submit_event.add_argument("--runtime-root", type=Path)
    submit_event.add_argument("--type", dest="event_type", required=True)
    submit_event.add_argument("--source")
    submit_event.add_argument("--source-id")
    submit_event.add_argument("--revision")
    submit_event.add_argument("--event-id")
    submit_event.add_argument("--causation-id")
    submit_event.add_argument("--debounce-seconds", type=float, default=60.0)
    submit_event.add_argument("--slug")
    submit_event.add_argument("--version")
    submit_event.add_argument("--scope")
    submit_event.add_argument("--language")
    submit_event.add_argument("--license")
    submit_event.add_argument("--source-root", type=Path)
    submit_event.add_argument("--index-rag", action="store_true")
    submit_event.add_argument("--json", action="store_true")

    work = lifecycle_commands.add_parser("work", help="process one due lifecycle job")
    work.add_argument("--package", type=Path, required=True)
    work.add_argument("--runtime-root", type=Path)
    work.add_argument("--force", action="store_true", help="process the earliest job before debounce expires")
    work.add_argument("--json", action="store_true")

    candidate = lifecycle_commands.add_parser("candidate", help="prepare, approve, publish or inspect a candidate")
    candidate_commands = candidate.add_subparsers(dest="candidate_command", required=True)
    prepare = candidate_commands.add_parser("prepare")
    prepare.add_argument("--package", type=Path, required=True)
    prepare.add_argument("--runtime-root", type=Path)
    prepare.add_argument("--source", required=True)
    prepare.add_argument("--source-root", type=Path)
    prepare.add_argument("--slug")
    prepare.add_argument("--version")
    prepare.add_argument("--scope")
    prepare.add_argument("--language")
    prepare.add_argument("--license")
    prepare.add_argument("--index-rag", action="store_true")
    prepare.add_argument("--json", action="store_true")
    candidate_status = candidate_commands.add_parser("status")
    candidate_status.add_argument("--package", type=Path, required=True)
    candidate_status.add_argument("--runtime-root", type=Path)
    candidate_status.add_argument("--candidate-id", required=True)
    candidate_status.add_argument("--json", action="store_true")
    approve = candidate_commands.add_parser("approve")
    approve.add_argument("--package", type=Path, required=True)
    approve.add_argument("--runtime-root", type=Path)
    approve.add_argument("--candidate-id", required=True)
    approve.add_argument("--actor", required=True)
    approve.add_argument("--role", default="reviewer")
    approve.add_argument("--policy-revision", default="policy-v1")
    approve.add_argument("--json", action="store_true")
    publish = candidate_commands.add_parser("publish")
    publish.add_argument("--package", type=Path, required=True)
    publish.add_argument("--runtime-root", type=Path)
    publish.add_argument("--candidate-id", required=True)
    publish.add_argument("--json", action="store_true")
    rollback = candidate_commands.add_parser("rollback")
    rollback.add_argument("--package", type=Path, required=True)
    rollback.add_argument("--runtime-root", type=Path)
    rollback.add_argument("--release-id", required=True)
    rollback.add_argument("--json", action="store_true")

    learning = lifecycle_commands.add_parser("learning", help="quarantine and review conversation claims")
    learning_commands = learning.add_subparsers(dest="learning_command", required=True)
    learning_submit = learning_commands.add_parser("submit")
    learning_submit.add_argument("--package", type=Path, required=True)
    learning_submit.add_argument("--runtime-root", type=Path)
    learning_submit.add_argument("--claim", required=True)
    learning_submit.add_argument("--claim-type", required=True)
    learning_submit.add_argument("--origin-json", default="{}")
    learning_submit.add_argument("--evidence-json", default="[]")
    learning_submit.add_argument("--scope")
    learning_submit.add_argument("--version")
    learning_submit.add_argument("--privacy", default="private")
    learning_submit.add_argument("--json", action="store_true")
    learning_review = learning_commands.add_parser("review")
    learning_review.add_argument("--package", type=Path, required=True)
    learning_review.add_argument("--runtime-root", type=Path)
    learning_review.add_argument("--proposal-id", required=True)
    learning_review.add_argument("--decision", choices=("admit", "reject", "quarantine"), required=True)
    learning_review.add_argument("--reviewer", required=True)
    learning_review.add_argument("--note", default="")
    learning_review.add_argument("--json", action="store_true")

    feedback = lifecycle_commands.add_parser("feedback", help="record quality signals without changing knowledge")
    feedback_commands = feedback.add_subparsers(dest="feedback_command", required=True)
    feedback_submit = feedback_commands.add_parser("submit")
    feedback_submit.add_argument("--package", type=Path, required=True)
    feedback_submit.add_argument("--runtime-root", type=Path)
    feedback_submit.add_argument("--kind", required=True)
    feedback_submit.add_argument("--query")
    feedback_submit.add_argument("--generation")
    feedback_submit.add_argument("--occurrence-id")
    feedback_submit.add_argument("--payload-json", default="{}")
    feedback_submit.add_argument("--json", action="store_true")
    feedback_status = feedback_commands.add_parser("status")
    feedback_status.add_argument("--package", type=Path, required=True)
    feedback_status.add_argument("--runtime-root", type=Path)
    feedback_status.add_argument("--json", action="store_true")
    return parser
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
        resolver = (
            SourceResolver.from_catalog_file(args.catalog, root=args.root)
            if args.catalog
            else SourceResolver(root=args.root)
        )
        resolution = resolver.resolve(args.source, version=args.version, scope=args.scope, language=args.language)
        print(
            json.dumps(
                redact_report(redact_metadata(resolution.to_dict())), indent=2, ensure_ascii=False, sort_keys=True
            )
        )
        return 0 if resolution.selected is not None and not resolution.requires_decision else 2
    if args.command == "plan":
        operation = build_plan(
            args.source,
            options=OperationOptions(
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
                runtime_root=args.runtime_root,
                source_root=args.source_root,
                lease_policy=args.lease_policy,
                lease_timeout_seconds=args.lease_timeout_seconds,
                stale_lease_seconds=args.stale_lease_seconds,
            ),
        )
        print(operation.json())
        return 0 if operation.ok else 2
    if args.command == "run":
        operation = build_plan(
            args.source,
            options=OperationOptions(
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
                runtime_root=args.runtime_root,
                source_root=args.source_root,
                lease_policy=args.lease_policy,
                lease_timeout_seconds=args.lease_timeout_seconds,
                stale_lease_seconds=args.stale_lease_seconds,
            ),
        )
        result = preview(operation) if args.mode == "dry-run" else apply_operation(operation)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        return result.exit_code if not result.ok else 0
    if args.command == "validate":
        result = validate_package(args.package)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result.ok else 1
    if args.command == "cleanup":
        result = cleanup_residue(
            args.package,
            retention_seconds=args.retention_seconds,
            keep_attempts=args.keep_attempts,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("ok") else 3 if result.get("code") == "writer_busy" else 1
    if args.command == "evaluate":
        metric_top_k = args.top_k if 1 <= args.top_k <= 100 else 5
        result = evaluate_package(
            args.package,
            args.cases,
            thresholds={
                f"recall_at_{metric_top_k}": args.recall_threshold,
                f"mrr_at_{metric_top_k}": args.mrr_threshold,
            },
            top_k=args.top_k,
            adapter=args.adapter,
            runtime_root=args.runtime_root,
        )
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result.ok else 1
    if args.command == "golden-candidates":
        payload = {
            "schema_version": 1,
            "reviewed": False,
            "cases": generate_golden_candidates(args.package, limit=args.limit),
        }
        contract = validate_artifact("golden-candidates", payload)
        if not contract.ok:
            raise ValueError("generated golden candidates violate their contract")
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "config-audit":
        try:
            result = audit_config_file(args.config)
        except (OSError, ValueError) as exc:
            print(
                json.dumps(
                    {"schema_version": 1, "ok": False, "errors": [{"code": "config_unreadable", "message": str(exc)}]},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 1
        print(result.to_json())
        return 0 if result.ok else 1
    if args.command == "lifecycle":
        store = LifecycleStore(args.package, args.runtime_root)
        if args.lifecycle_command == "status":
            result = store.status()
        elif args.lifecycle_command == "source":
            if args.source_command == "register":
                result = store.register_source(
                    {
                        "source_id": args.source_id,
                        "canonical": args.canonical,
                        "kind": args.kind,
                        "scope": args.scope,
                        "version_policy": args.version_policy,
                        "language": args.language,
                        "owner": args.owner,
                        "status": args.status,
                    }
                )
            elif args.source_command == "reconcile":
                result = reconcile_source(
                    args.package,
                    source=args.source,
                    runtime_root=args.runtime_root,
                    options={
                        "source_root": str(args.source_root) if args.source_root else None,
                        "slug": args.slug,
                        "version": args.version,
                        "scope": args.scope,
                        "language": args.language,
                        "license": args.license,
                        "index_rag": args.index_rag,
                    },
                )
            else:
                return 2
        elif args.lifecycle_command == "event":
            if args.event_command != "submit":
                return 2
            result = store.submit_event(
                event_type=args.event_type,
                source_id=args.source_id,
                observed_revision=args.revision,
                event_id=args.event_id,
                causation_id=args.causation_id,
                debounce_seconds=args.debounce_seconds,
                payload={
                    "source": args.source,
                    "options": {
                        "source_root": str(args.source_root) if args.source_root else None,
                        "slug": args.slug,
                        "version": args.version,
                        "scope": args.scope,
                        "language": args.language,
                        "license": args.license,
                        "index_rag": args.index_rag,
                    },
                },
            )
        elif args.lifecycle_command == "work":
            result = work_once(args.package, runtime_root=args.runtime_root, force=args.force)
        elif args.lifecycle_command == "candidate":
            if args.candidate_command == "prepare":
                result = prepare_candidate(
                    args.package,
                    source=args.source,
                    runtime_root=args.runtime_root,
                    options={
                        "source_root": str(args.source_root) if args.source_root else None,
                        "slug": args.slug,
                        "version": args.version,
                        "scope": args.scope,
                        "language": args.language,
                        "license": args.license,
                        "index_rag": args.index_rag,
                    },
                )
            elif args.candidate_command == "status":
                candidate_value = store.candidate(args.candidate_id)
                result = (
                    {"ok": True, **candidate_value} if candidate_value else {"ok": False, "code": "candidate_not_found"}
                )
            elif args.candidate_command == "approve":
                result = store.approve_candidate(
                    args.candidate_id,
                    actor=args.actor,
                    role=args.role,
                    policy_revision=args.policy_revision,
                )
            elif args.candidate_command == "publish":
                result = store.publish_candidate(args.candidate_id)
            elif args.candidate_command == "rollback":
                result = store.rollback(args.release_id)
            else:
                return 2
        elif args.lifecycle_command == "learning":
            if args.learning_command == "submit":
                try:
                    origin = json.loads(args.origin_json)
                    evidence = json.loads(args.evidence_json)
                except json.JSONDecodeError as exc:
                    result = {"ok": False, "code": "learning_json_invalid", "message": redact_text(exc)}
                else:
                    result = store.submit_learning(
                        claim=args.claim,
                        claim_type=args.claim_type,
                        origin=origin if isinstance(origin, dict) else {},
                        evidence=evidence if isinstance(evidence, list) else [],
                        scope=args.scope,
                        version=args.version,
                        privacy=args.privacy,
                    )
            elif args.learning_command == "review":
                result = store.review_learning(
                    args.proposal_id,
                    decision=args.decision,
                    reviewer=args.reviewer,
                    note=args.note,
                )
            else:
                return 2
        elif args.lifecycle_command == "feedback":
            if args.feedback_command == "status":
                result = store.status()
            elif args.feedback_command == "submit":
                try:
                    payload = json.loads(args.payload_json)
                except json.JSONDecodeError as exc:
                    result = {"ok": False, "code": "feedback_json_invalid", "message": redact_text(exc)}
                else:
                    result = store.submit_feedback(
                        kind=args.kind,
                        query=args.query,
                        generation=args.generation,
                        occurrence_id=args.occurrence_id,
                        payload=payload if isinstance(payload, dict) else {},
                    )
            else:
                return 2
        else:
            return 2
        print(json.dumps(redact_report(result), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("ok") is True else 1
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
                    "errors": [{"code": "invalid_request", "message": redact_text(exc)}],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
