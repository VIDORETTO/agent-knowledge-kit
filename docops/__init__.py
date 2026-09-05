"""Portable, deterministic orchestration helpers for the documentation pipeline."""

__all__ = [
    "__version__",
    "OperationOptions",
    "OperationPlan",
    "OperationRequest",
    "OperationResult",
    "PipelineOptions",
    "apply",
    "cleanup",
    "inspect",
    "plan",
    "preview",
    "record_skill_enrichment",
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


def record_skill_enrichment(*args, **kwargs):
    """Record validated enrichment produced by an external skill tool."""

    from .readiness import record_skill_enrichment as record_enrichment

    return record_enrichment(*args, **kwargs)


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
    raise AttributeError(name)
