"""Compatibility adapter for the pre-1.0 pipeline module.

The transaction engine lives in :mod:`docops.operations`.  This module keeps
the historical import path working for callers that still use
``docops.pipeline``; it intentionally contains no second implementation of
source acquisition, generation, indexing or promotion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .api_types import PipelineOptions, PipelineResult
from .operations import OperationPlan, preview
from .operations import apply as apply_operation
from .operations import cleanup as cleanup_residue
from .operations import inspect as inspect_operation
from .operations import plan as build_plan


def plan(source: str | Path, *, options: PipelineOptions) -> OperationPlan:
    """Build a side-effect-free plan through the supported engine."""

    return build_plan(source, options=options)


def apply(operation_plan: OperationPlan) -> PipelineResult:
    """Apply a plan through the supported transaction engine."""

    return apply_operation(operation_plan)


def inspect(package_root: Path | str) -> dict[str, Any]:
    """Inspect a package through the supported lifecycle seam."""

    return inspect_operation(package_root)


def cleanup(package_root: Path | str, **kwargs: Any) -> dict[str, Any]:
    """Clean residue through the supported lifecycle seam."""

    return cleanup_residue(package_root, **kwargs)


def run_pipeline(source: str | Path, *, options: PipelineOptions) -> PipelineResult:
    """Compatibility entry point delegating to ``plan`` and ``apply``."""

    operation = plan(source, options=options)
    if options.mode == "dry-run":
        return preview(operation)
    return apply(operation)


__all__ = ["PipelineOptions", "PipelineResult", "apply", "cleanup", "inspect", "plan", "run_pipeline"]
