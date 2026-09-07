"""Portable, deterministic orchestration helpers for the documentation pipeline."""

__all__ = [
    "__version__",
    "OperationOptions",
    "OperationPlan",
    "OperationRequest",
    "OperationResult",
    "PipelineOptions",
    "approve_candidate",
    "apply",
    "cleanup",
    "inspect",
    "plan",
    "publish_candidate",
    "preview",
    "rollback_candidate",
    "reconcile_source",
    "register_source",
    "list_jobs",
    "submit_event",
    "work_once",
    "assess_conceptual_impact",
    "create_reader_session",
    "query_reader_session",
    "revoke_reader_session",
    "build_rag_snapshot",
    "read_rag_snapshot",
    "rag_snapshot_identity",
    "validate_rag_snapshot",
    "compare_embedding_profiles",
    "plan_rag_reuse",
    "snapshot_rag_package",
    "submit_learning_proposal",
    "review_learning_proposal",
    "read_learning_proposal",
    "submit_feedback",
    "build_feedback_report",
    "report_feedback",
    "CanonicalLifecycle",
    "Lifecycle",
    "LifecycleError",
    "LifecycleFacade",
    "LifecycleStateMachine",
    "RuntimeState",
    "lifecycle_status",
]
__version__ = "1.1.0"


def plan(*args, **kwargs):
    """Build a side-effect-free operation plan."""

    from .operations import plan as build_plan

    return build_plan(*args, **kwargs)


def apply(*args, **kwargs):
    """Apply a previously created operation plan."""

    from .operations import apply as apply_plan

    return apply_plan(*args, **kwargs)


def cleanup(*args, **kwargs):
    """Remove expired, non-resumable operation residue safely."""

    from .operations import cleanup as cleanup_residue

    return cleanup_residue(*args, **kwargs)


def inspect(*args, **kwargs):
    """Inspect the active package and recoverable operation residue."""

    from .operations import inspect as inspect_package

    return inspect_package(*args, **kwargs)


def preview(*args, **kwargs):
    """Turn a plan into a terminal no-effects result."""

    from .operations import preview as preview_plan

    return preview_plan(*args, **kwargs)


def approve_candidate(*args, **kwargs):
    """Record explicit authority for a reviewable candidate."""

    from .operations import approve_candidate as approve

    return approve(*args, **kwargs)


def publish_candidate(*args, **kwargs):
    """Promote an approved candidate after exact evidence revalidation."""

    from .operations import publish_candidate as publish

    return publish(*args, **kwargs)


def rollback_candidate(*args, **kwargs):
    """Restore one retained editorial generation after exact validation."""

    from .operations import rollback_candidate as rollback

    return rollback(*args, **kwargs)


def register_source(*args, **kwargs):
    """Register one source without replacing other source registrations."""

    from .source_policy import register_source as register

    return register(*args, **kwargs)


def reconcile_source(*args, **kwargs):
    """Reconcile one acquisition snapshot without implicit withdrawal."""

    from .source_policy import reconcile_source as reconcile

    return reconcile(*args, **kwargs)


def submit_event(*args, **kwargs):
    """Persist a coordination event and coalesce its durable job."""

    from .coordination import submit_event as submit

    return submit(*args, **kwargs)


def list_jobs(*args, **kwargs):
    """List the public durable-job projection."""

    from .coordination import list_jobs as list_queue_jobs

    return list_queue_jobs(*args, **kwargs)


def work_once(*args, **kwargs):
    """Claim and execute at most one durable job with resumable effects."""

    from .coordination import work_once as execute_work_once

    return execute_work_once(*args, **kwargs)


def assess_conceptual_impact(*args, **kwargs):
    """Assess conceptual impact without publishing or mutating active knowledge."""

    from .triggers import assess_conceptual_impact as assess

    return assess(*args, **kwargs)


def create_reader_session(*args, **kwargs):
    """Pin a read-only session to one package generation."""

    from .reader_sessions import create_reader_session as create

    return create(*args, **kwargs)


def query_reader_session(*args, **kwargs):
    """Query only read tools through a pinned reader session."""

    from .reader_sessions import query_reader_session as query

    return query(*args, **kwargs)


def revoke_reader_session(*args, **kwargs):
    """Revoke a reader session without changing package content."""

    from .reader_sessions import revoke_reader_session as revoke

    return revoke(*args, **kwargs)


def build_rag_snapshot(*args, **kwargs):
    """Build a relocatable content snapshot without mutating the package."""

    from .rag_sync import build_rag_snapshot as build

    return build(*args, **kwargs)


def read_rag_snapshot(*args, **kwargs):
    """Read and verify a relocatable RAG snapshot."""

    from .rag_sync import read_rag_snapshot as read

    return read(*args, **kwargs)


def rag_snapshot_identity(*args, **kwargs):
    """Return the compact identity used to pin a reader to a snapshot."""

    from .rag_sync import rag_snapshot_identity as identity

    return identity(*args, **kwargs)


def validate_rag_snapshot(*args, **kwargs):
    """Validate a snapshot against a package generation and revocations."""

    from .rag_sync import validate_rag_snapshot as validate

    return validate(*args, **kwargs)


def compare_embedding_profiles(*args, **kwargs):
    """Compare embedding profiles without changing the active package."""

    from .rag_sync import compare_embedding_profiles as compare

    return compare(*args, **kwargs)


def plan_rag_reuse(*args, **kwargs):
    """Plan incremental reuse or a declared full rebuild."""

    from .rag_sync import plan_rag_reuse as plan

    return plan(*args, **kwargs)


def snapshot_rag_package(*args, **kwargs):
    """Build and optionally persist a snapshot plus its non-mutating reuse plan."""

    from .rag_sync import snapshot_rag_package as snapshot

    return snapshot(*args, **kwargs)


def submit_learning_proposal(*args, **kwargs):
    """Capture one minimized conversation-derived proposal in quarantine."""

    from .learning import submit_learning_proposal as submit

    return submit(*args, **kwargs)


def review_learning_proposal(*args, **kwargs):
    """Review one quarantined proposal with explicit human authority."""

    from .learning import review_learning_proposal as review

    return review(*args, **kwargs)


def read_learning_proposal(*args, **kwargs):
    """Read one learning proposal through its validation boundary."""

    from .learning import read_learning_proposal as read

    return read(*args, **kwargs)


def submit_feedback(*args, **kwargs):
    """Persist a redacted usage signal without changing active knowledge."""

    from .feedback import submit_feedback as submit

    return submit(*args, **kwargs)


def build_feedback_report(*args, **kwargs):
    """Aggregate usage signals into review-only investigations."""

    from .feedback import build_feedback_report as build

    return build(*args, **kwargs)


def report_feedback(*args, **kwargs):
    """Compatibility alias for the public feedback report operation."""

    from .feedback import report_feedback as report

    return report(*args, **kwargs)


def lifecycle_status(*args, **kwargs):
    """Return the versioned status projection of the canonical lifecycle."""

    from .lifecycle import lifecycle_status as status

    return status(*args, **kwargs)


def __getattr__(name):
    if name in {"OperationOptions", "OperationPlan", "OperationRequest"}:
        from .operations import OperationOptions, OperationPlan, OperationRequest

        return {
            "OperationOptions": OperationOptions,
            "OperationPlan": OperationPlan,
            "OperationRequest": OperationRequest,
        }[name]
    if name == "OperationResult":
        from .api_types import PipelineResult

        return PipelineResult
    if name == "PipelineOptions":
        from .api_types import PipelineOptions

        return PipelineOptions
    if name in {
        "CanonicalLifecycle",
        "Lifecycle",
        "LifecycleError",
        "LifecycleFacade",
        "LifecycleStateMachine",
        "RuntimeState",
    }:
        from .lifecycle import (
            CanonicalLifecycle,
            Lifecycle,
            LifecycleError,
            LifecycleFacade,
            LifecycleStateMachine,
            RuntimeState,
        )

        return {
            "CanonicalLifecycle": CanonicalLifecycle,
            "Lifecycle": Lifecycle,
            "LifecycleError": LifecycleError,
            "LifecycleFacade": LifecycleFacade,
            "LifecycleStateMachine": LifecycleStateMachine,
            "RuntimeState": RuntimeState,
        }[name]
    raise AttributeError(name)
