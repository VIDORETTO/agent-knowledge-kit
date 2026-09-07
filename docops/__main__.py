"""Command line entry point for the portable documentation operator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent_skill import install_agents_bootstrap, skill_metadata
from .candidates import submit_enrichment
from .config_audit import audit_config_file
from .contracts import validate_artifact
from .coordination import list_jobs, submit_event, work_once
from .doctor import run_doctor
from .evaluator import evaluate_package, generate_golden_candidates
from .feedback import build_feedback_report, submit_feedback
from .harness import export_enrichment_request
from .learning import review_learning_proposal, submit_learning_proposal
from .lifecycle import LifecycleFacade
from .manifest import redact_metadata
from .observability import redact_report, redact_text
from .operations import (
    CandidatePublicationError,
    OperationOptions,
    approve_candidate,
    preview,
    publish_candidate,
    rollback_candidate,
)
from .operations import apply as apply_operation
from .operations import cleanup as cleanup_residue
from .operations import plan as build_plan
from .package_validator import validate_package
from .rag_sync import RagSnapshotError, compare_embedding_profiles, snapshot_rag_package
from .reader_sessions import create_reader_session, query_reader_session, revoke_reader_session
from .source_policy import reconcile_source, register_source
from .source_resolver import SourceResolver
from .triggers import assess_conceptual_impact

# The flat commands remain the compatibility surface during expand-contract.
# Keep this mapping explicit so each legacy entry point has one documented
# canonical spelling and can be removed by policy instead of by accident.
CLI_COMPATIBILITY_MAP = {
    "doctor": "doctor",
    "skill": "skill",
    "agents-bootstrap": "agents-bootstrap",
    "resolve": "source resolve",
    "plan": "package plan",
    "run": "package run",
    "validate": "package validate",
    "cleanup": "package cleanup",
    "evaluate": "quality evaluate",
    "golden-candidates": "quality golden-candidates",
    "candidate-request": "lifecycle candidate enrichment-request",
    "candidate-submit": "lifecycle candidate enrich",
    "candidate-approve": "lifecycle candidate approve",
    "candidate-publish": "lifecycle candidate publish",
    "candidate-rollback": "lifecycle candidate rollback",
    "source-register": "lifecycle source register",
    "source-reconcile": "lifecycle source reconcile",
    "event-submit": "lifecycle event submit",
    "jobs": "lifecycle worker list",
    "jobs-list": "lifecycle worker list",
    "work": "lifecycle worker run",
    "impact-assess": "lifecycle impact assess",
    "reader-session": "lifecycle reader session",
    "reader-query": "lifecycle reader query",
    "reader-session-revoke": "lifecycle reader revoke",
    "rag-snapshot": "lifecycle rag snapshot",
    "rag-profile-compare": "lifecycle rag profile-compare",
    "learning-submit": "lifecycle learning submit",
    "learning_submit": "lifecycle learning submit",
    "learning-review": "lifecycle learning review",
    "learning_review": "lifecycle learning review",
    "feedback-submit": "lifecycle feedback submit",
    "feedback_submit": "lifecycle feedback submit",
    "feedback-report": "lifecycle feedback report",
    "feedback_report": "lifecycle feedback report",
    "config-audit": "security config-audit",
    "lifecycle-status": "lifecycle status",
}

_CANONICAL_TO_FLAT = {
    tuple(canonical.split()): legacy
    for legacy, canonical in CLI_COMPATIBILITY_MAP.items()
    if canonical != legacy and legacy not in {"jobs-list", "learning_submit", "learning_review", "feedback_submit"}
}
_CANONICAL_HELP = """Canonical domain commands:

  lifecycle status
  lifecycle source {register,reconcile}
  lifecycle event submit
  lifecycle worker {list,run}
  lifecycle candidate {enrichment-request,enrich,approve,publish,rollback}
  lifecycle reader {session,query,revoke}
  lifecycle rag {snapshot,profile-compare}
  lifecycle learning {submit,review}
  lifecycle feedback {submit,report}

Flat commands are temporary compatibility aliases. They emit the same JSON
contract and exit code as their canonical spelling; deprecation metadata is
kept out of structured output. Remove an alias only after all callers have
migrated and the alias-usage gate is zero for one complete release window.
"""


def _expand_canonical_argv(argv: list[str]) -> list[str]:
    """Translate one canonical hierarchy prefix to its legacy parser seam."""

    for prefix in sorted(_CANONICAL_TO_FLAT, key=len, reverse=True):
        if tuple(argv[: len(prefix)]) == prefix:
            return [_CANONICAL_TO_FLAT[prefix], *argv[len(prefix) :]]
    return list(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docops",
        description="Portable documentation lifecycle operator",
        epilog=_CANONICAL_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    skill = commands.add_parser("skill", help="inspect the first-party DOCOPS agent skill")
    skill_commands = skill.add_subparsers(dest="skill_command", required=True)
    skill_path = skill_commands.add_parser("path", help="show the bundled docops-agent skill path")
    skill_path.add_argument("--skill-root", type=Path)
    skill_path.add_argument("--json", action="store_true")
    agents_bootstrap = commands.add_parser("agents-bootstrap", help="install the DOCOPS rule in AGENTS.md")
    agents_bootstrap.add_argument("--root", type=Path, default=Path.cwd())
    agents_bootstrap.add_argument("--check", action="store_true", help="do not write; fail if the rule is absent")
    agents_bootstrap.add_argument("--json", action="store_true")
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
    plan.add_argument("--layer", dest="layer_values", action="append", choices=("conceptual", "factual"))
    plan.add_argument("--layers", dest="layers_csv")
    plan.add_argument("--publication-policy", choices=("direct", "candidate"), default="direct")
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
    run.add_argument("--layer", dest="layer_values", action="append", choices=("conceptual", "factual"))
    run.add_argument("--layers", dest="layers_csv")
    run.add_argument("--publication-policy", choices=("direct", "candidate"), default="direct")
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
    evaluate.add_argument("--response-receipt", type=Path)
    evaluate.add_argument("--response-fidelity-threshold", type=float, default=0.98)
    evaluate.add_argument("--citation-coverage-threshold", type=float, default=0.98)
    evaluate.add_argument("--json", action="store_true")
    candidates = commands.add_parser("golden-candidates", help="generate unreviewed golden candidates")
    candidates.add_argument("package", type=Path)
    candidates.add_argument("--limit", type=int, default=20)
    candidates.add_argument("--json", action="store_true")
    candidate_request = commands.add_parser(
        "candidate-request", help="export an external enrichment task for a candidate"
    )
    candidate_request.add_argument("--package", type=Path, required=True)
    candidate_request.add_argument("--candidate-id", required=True)
    candidate_request.add_argument("--language")
    candidate_request.add_argument("--json", action="store_true")
    candidate_submit = commands.add_parser("candidate-submit", help="receive an external enrichment result")
    candidate_submit.add_argument("--package", type=Path, required=True)
    candidate_submit.add_argument("--candidate-id", required=True)
    candidate_submit.add_argument("--source-dir", type=Path, required=True)
    candidate_submit.add_argument("--receipt", type=Path, required=True)
    candidate_submit.add_argument("--json", action="store_true")
    candidate_approve = commands.add_parser(
        "candidate-approve",
        help="record explicit authority for a reviewable candidate",
    )
    candidate_approve.add_argument("--package", type=Path, required=True)
    candidate_approve.add_argument("--candidate-id", required=True)
    candidate_approve.add_argument("--actor", required=True)
    candidate_approve.add_argument(
        "--role",
        choices=("human_approver", "delegated_policy"),
        required=True,
    )
    candidate_approve.add_argument(
        "--authority-json",
        help="authenticated external authority attestation; proof is hashed before storage",
    )
    candidate_approve.add_argument("--json", action="store_true")
    candidate_publish = commands.add_parser(
        "candidate-publish",
        help="publish an approved candidate after exact evidence revalidation",
    )
    candidate_publish.add_argument("--package", type=Path, required=True)
    candidate_publish.add_argument("--candidate-id", required=True)
    candidate_publish.add_argument("--json", action="store_true")
    candidate_rollback = commands.add_parser(
        "candidate-rollback",
        help="restore a retained editorial generation after validation",
    )
    candidate_rollback.add_argument("--package", type=Path, required=True)
    candidate_rollback.add_argument("--release-id", required=True)
    candidate_rollback.add_argument("--json", action="store_true")
    source_register = commands.add_parser("source-register", help="register one documentation source")
    source_register.add_argument("--package", type=Path, required=True)
    source_register.add_argument("--source-id", required=True)
    source_register.add_argument("--canonical", required=True)
    source_register.add_argument("--kind", choices=("local", "repository", "web"), default="web")
    source_register.add_argument("--scope", default="/**")
    source_register.add_argument("--version-policy", choices=("latest", "pinned"), default="latest")
    source_register.add_argument("--version")
    source_register.add_argument("--language")
    source_register.add_argument("--rights", default="unknown")
    source_register.add_argument("--privacy", default="unknown")
    source_register.add_argument("--authority", default="operator")
    source_register.add_argument("--owner", default="local")
    source_register.add_argument(
        "--readmit",
        action="store_true",
        help="explicitly reauthorize a previously withdrawn source",
    )
    source_register.add_argument("--json", action="store_true")
    source_reconcile = commands.add_parser("source-reconcile", help="reconcile one acquisition snapshot")
    source_reconcile.add_argument("--package", type=Path, required=True)
    source_reconcile.add_argument("--snapshot", type=Path, required=True)
    source_reconcile.add_argument("--source-id")
    source_reconcile.add_argument("--withdraw", action="store_true")
    source_reconcile.add_argument("--json", action="store_true")
    event_submit = commands.add_parser("event-submit", help="persist one coordination event")
    event_submit.add_argument("--queue", type=Path, required=True)
    event_submit.add_argument("--event", type=Path, required=True)
    event_submit.add_argument("--now")
    event_submit.add_argument("--json", action="store_true")
    jobs = commands.add_parser("jobs", aliases=("jobs-list",), help="list durable coordination jobs")
    jobs.add_argument("--queue", type=Path, required=True)
    jobs.add_argument("--now")
    jobs.add_argument("--json", action="store_true")
    work = commands.add_parser("work", help="execute at most one durable coordination job")
    work.add_argument("--once", action="store_true", required=True)
    work.add_argument("--queue", type=Path, required=True)
    work.add_argument("--now")
    work.add_argument("--worker-id")
    work.add_argument("--lease-seconds", type=int, default=120)
    work.add_argument("--json", action="store_true")
    impact = commands.add_parser("impact-assess", help="assess conceptual impact from source events")
    impact.add_argument("--package", type=Path, required=True)
    impact.add_argument("--events", type=Path, required=True)
    impact.add_argument("--threshold", type=int, default=10)
    impact.add_argument("--budget", type=int, default=4)
    impact.add_argument("--corpus-documents", type=int, default=100)
    impact.add_argument("--now")
    impact.add_argument("--causation-id")
    impact.add_argument("--json", action="store_true")
    reader_session = commands.add_parser("reader-session", help="create a pinned read-only reader session")
    reader_session.add_argument("--package", type=Path, required=True)
    reader_session.add_argument("--adapter", choices=("memory", "mcp"), default="memory")
    reader_session.add_argument("--session-id")
    reader_session.add_argument("--snapshot", type=Path, help="explicit relocatable RAG snapshot to pin")
    reader_session.add_argument("--now")
    reader_session.add_argument("--expires-at")
    reader_session.add_argument("--json", action="store_true")
    reader_query = commands.add_parser("reader-query", help="query through a pinned reader session")
    reader_query.add_argument("--package", type=Path, required=True)
    reader_query.add_argument("--session", required=True)
    reader_query.add_argument("--tool", required=True)
    reader_query.add_argument("--query", required=True)
    reader_query.add_argument("--adapter", choices=("memory", "mcp"))
    reader_query.add_argument("--max-results", type=int, default=5)
    reader_query.add_argument("--now")
    reader_query.add_argument("--runtime-root", type=Path)
    reader_query.add_argument("--json", action="store_true")
    reader_revoke = commands.add_parser("reader-session-revoke", help="revoke a pinned reader session")
    reader_revoke.add_argument("--package", type=Path, required=True)
    reader_revoke.add_argument("--session", required=True)
    reader_revoke.add_argument("--now")
    reader_revoke.add_argument("--reason")
    reader_revoke.add_argument("--json", action="store_true")
    rag_snapshot = commands.add_parser("rag-snapshot", help="plan safe RAG snapshot reuse without promotion")
    rag_snapshot.add_argument("--package", type=Path, required=True)
    rag_snapshot.add_argument("--previous", type=Path)
    rag_snapshot.add_argument("--snapshot-out", type=Path)
    rag_snapshot.add_argument("--backend", default="knowledge-rag")
    rag_snapshot.add_argument("--supports-incremental", action="store_true")
    rag_snapshot.add_argument("--server-version")
    rag_snapshot.add_argument("--verify-query")
    rag_snapshot.add_argument("--verify-adapter", choices=("memory", "mcp"), default="memory")
    rag_snapshot.add_argument("--runtime-root", type=Path)
    rag_snapshot.add_argument("--json", action="store_true")
    rag_profile_compare = commands.add_parser(
        "rag-profile-compare",
        help="compare embedding profiles without changing the active index",
    )
    rag_profile_compare.add_argument("--package", type=Path, required=True)
    rag_profile_compare.add_argument("--profiles", default="compact,multilingual")
    rag_profile_compare.add_argument("--language")
    rag_profile_compare.add_argument("--select-profile")
    rag_profile_compare.add_argument("--json", action="store_true")
    learning_submit = commands.add_parser(
        "learning-submit",
        aliases=("learning_submit",),
        help="capture a minimized learning proposal in quarantine",
    )
    learning_submit.add_argument("--package", type=Path, required=True)
    learning_submit.add_argument("--proposal", type=Path, required=True)
    learning_submit.add_argument("--capture-opt-in", action="store_true")
    learning_submit.add_argument("--now")
    learning_submit.add_argument("--json", action="store_true")
    learning_review = commands.add_parser(
        "learning-review",
        aliases=("learning_review",),
        help="review, admit, reject or revoke a learning proposal",
    )
    learning_review.add_argument("--package", type=Path, required=True)
    learning_review.add_argument("--proposal-id", required=True)
    learning_review.add_argument("--decision", choices=("admit", "reject", "revoke"), required=True)
    learning_review.add_argument("--actor", required=True)
    learning_review.add_argument("--role", default="human_approver", choices=("human_approver",))
    learning_review.add_argument("--evidence", type=Path)
    learning_review.add_argument("--now")
    learning_review.add_argument("--reason")
    learning_review.add_argument("--json", action="store_true")
    feedback_submit = commands.add_parser(
        "feedback-submit",
        aliases=("feedback_submit",),
        help="capture one redacted usage signal and optionally queue its report",
    )
    feedback_submit.add_argument("--package", type=Path, required=True)
    feedback_submit.add_argument("--feedback", type=Path, required=True)
    feedback_submit.add_argument("--queue", type=Path)
    feedback_submit.add_argument("--now")
    feedback_submit.add_argument("--json", action="store_true")
    feedback_report = commands.add_parser(
        "feedback-report",
        aliases=("feedback_report",),
        help="aggregate usage feedback into review-only investigations",
    )
    feedback_report.add_argument("--package", type=Path, required=True)
    feedback_report.add_argument("--window-days", type=int, default=7)
    feedback_report.add_argument("--now")
    feedback_report.add_argument("--json", action="store_true")
    lifecycle_status = commands.add_parser("lifecycle-status", help="show the versioned lifecycle status")
    lifecycle_status.add_argument("--package", type=Path, required=True)
    lifecycle_status.add_argument("--runtime-root", type=Path)
    lifecycle_status.add_argument("--json", action="store_true")
    lifecycle = commands.add_parser(
        "lifecycle",
        help="canonical hierarchy for reviewed lifecycle operations",
        description="Canonical lifecycle command hierarchy",
        epilog=_CANONICAL_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    lifecycle.set_defaults(_canonical_namespace=True)
    config_audit = commands.add_parser("config-audit", help="audit MCP transport security")
    config_audit.add_argument("config", type=Path)
    config_audit.add_argument("--json", action="store_true")
    return parser


def _layers_from_args(args: argparse.Namespace) -> tuple[str, ...]:
    values = list(args.layer_values or [])
    if args.layers_csv:
        values.extend(part.strip() for part in args.layers_csv.split(","))
    return tuple(values) if values else ("conceptual", "factual")


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "skill":
        if args.skill_command != "path":
            return 2
        result = {"ok": True, **skill_metadata(args.skill_root)}
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) if args.json else result["path"])
        return 0
    if args.command == "agents-bootstrap":
        result = install_agents_bootstrap(args.root, check=args.check)
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) if args.json else result["status"])
        return 0 if result["ok"] else 2
    if args.command == "lifecycle-status":
        result = LifecycleFacade(args.package, runtime_root=args.runtime_root).status()
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) if args.json else result)
        return 0 if result.get("ok") else 1
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
                layers=_layers_from_args(args),
                publication_policy=args.publication_policy,
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
                layers=_layers_from_args(args),
                publication_policy=args.publication_policy,
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
                "response_fidelity": args.response_fidelity_threshold,
                "citation_coverage": args.citation_coverage_threshold,
            },
            top_k=args.top_k,
            adapter=args.adapter,
            runtime_root=args.runtime_root,
            response_receipt=args.response_receipt,
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
    if args.command == "candidate-request":
        payload = export_enrichment_request(args.package, args.candidate_id, language=args.language)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "candidate-submit":
        payload = submit_enrichment(args.package, args.candidate_id, args.source_dir, args.receipt)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "candidate-approve":
        authority = None
        if args.authority_json is not None:
            try:
                authority = json.loads(args.authority_json)
            except json.JSONDecodeError as exc:
                raise CandidatePublicationError(
                    "approval_authority_invalid",
                    "--authority-json must contain valid JSON",
                ) from exc
        payload = approve_candidate(
            args.package,
            args.candidate_id,
            actor=args.actor,
            role=args.role,
            authority=authority,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "candidate-publish":
        payload = publish_candidate(args.package, args.candidate_id)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "candidate-rollback":
        payload = rollback_candidate(args.package, args.release_id)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "source-register":
        payload = register_source(
            args.package,
            source_id=args.source_id,
            canonical=args.canonical,
            kind=args.kind,
            scope=args.scope,
            version_policy=args.version_policy,
            version=args.version,
            language=args.language,
            rights=args.rights,
            privacy=args.privacy,
            authority=args.authority,
            owner=args.owner,
            readmit=args.readmit,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "source-reconcile":
        payload = reconcile_source(
            args.package,
            args.snapshot,
            source_id=args.source_id,
            withdraw=args.withdraw,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if payload.get("ok") else 2
    if args.command == "event-submit":
        payload = submit_event(args.queue, args.event, now=args.now)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command in {"jobs", "jobs-list"}:
        payload = list_jobs(args.queue, now=args.now)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "work":
        payload = work_once(
            args.queue,
            now=args.now,
            worker_id=args.worker_id,
            lease_seconds=args.lease_seconds,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if payload.get("ok") else 2
    if args.command == "impact-assess":
        payload = assess_conceptual_impact(
            args.package,
            args.events,
            now=args.now,
            threshold=args.threshold,
            budget=args.budget,
            corpus_documents=args.corpus_documents,
            causation_id=args.causation_id,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "reader-session":
        payload = create_reader_session(
            args.package,
            adapter=args.adapter,
            session_id=args.session_id,
            snapshot=args.snapshot,
            now=args.now,
            expires_at=args.expires_at,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "reader-query":
        payload = query_reader_session(
            args.package,
            args.session,
            tool=args.tool,
            query=args.query,
            adapter=args.adapter,
            max_results=args.max_results,
            now=args.now,
            runtime_root=args.runtime_root,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "reader-session-revoke":
        payload = revoke_reader_session(
            args.package,
            args.session,
            now=args.now,
            reason=args.reason,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "rag-snapshot":
        try:
            payload = snapshot_rag_package(
                args.package,
                previous=args.previous,
                snapshot_out=args.snapshot_out,
                backend=args.backend,
                supports_incremental=args.supports_incremental,
                server_version=args.server_version,
                verify_query=args.verify_query,
                verify_adapter=args.verify_adapter,
                runtime_root=args.runtime_root,
            )
        except RagSnapshotError as exc:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "ok": False,
                        "active_preserved": True,
                        "error": {"code": exc.code, "message": redact_text(exc)},
                    },
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 1
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "rag-profile-compare":
        try:
            profiles = tuple(part.strip() for part in args.profiles.split(","))
            payload = compare_embedding_profiles(
                args.package,
                profiles=profiles,
                language=args.language,
                selected_profile=args.select_profile,
            )
        except RagSnapshotError as exc:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "ok": False,
                        "publication_allowed": False,
                        "error": {"code": exc.code, "message": redact_text(exc)},
                    },
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 1
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command in {"learning-submit", "learning_submit"}:
        payload = submit_learning_proposal(
            args.package,
            args.proposal,
            capture_opt_in=args.capture_opt_in,
            now=args.now,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command in {"learning-review", "learning_review"}:
        evidence = None
        if args.evidence:
            evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        payload = review_learning_proposal(
            args.package,
            args.proposal_id,
            decision=args.decision,
            actor=args.actor,
            role=args.role,
            evidence=evidence,
            now=args.now,
            reason=args.reason,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command in {"feedback-submit", "feedback_submit"}:
        payload = submit_feedback(
            args.package,
            args.feedback,
            now=args.now,
            queue_path=args.queue,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command in {"feedback-report", "feedback_report"}:
        payload = build_feedback_report(
            args.package,
            now=args.now,
            window_days=args.window_days,
        )
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
    return 2


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(_expand_canonical_argv(raw_argv))
    try:
        return _dispatch(args)
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "ok": False,
                    "errors": [
                        {
                            "code": str(getattr(exc, "code", "invalid_request")),
                            "message": redact_text(exc),
                        }
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
