"""Lightweight, reproducible retrieval evaluation for a produced package."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .package_validator import validate_package

_TOKEN = re.compile(r"[\wÀ-ÿ][\wÀ-ÿ./:-]*", re.UNICODE)
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


@dataclass
class EvaluationResult:
    ok: bool
    metrics: dict[str, float]
    cases: list[dict[str, Any]]
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    thresholds: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "ok": self.ok,
            "metrics": self.metrics,
            "cases": self.cases,
            "errors": self.errors,
            "warnings": self.warnings,
            "diagnostics": self.diagnostics,
            "thresholds": self.thresholds,
        }


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value)}


def _case_payload(
    cases: Mapping[str, Any] | Iterable[Mapping[str, Any]],
) -> tuple[bool, list[Mapping[str, Any]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    if isinstance(cases, Mapping):
        reviewed = cases.get("reviewed") is True
        if cases.get("schema_version") != 1 or type(cases.get("schema_version")) is not int:
            errors.append({"code": "golden_schema", "message": "golden set schema_version must be 1"})
        if "cases" not in cases:
            errors.append({"code": "golden_cases", "message": "golden set cases must be a list"})
        raw_cases = cases.get("cases", [])
    else:
        reviewed = False
        raw_cases = cases
        errors.append({"code": "golden_schema", "message": "golden set must be an object with schema_version and cases"})
    if not isinstance(raw_cases, list):
        return reviewed, [], [{"code": "golden_cases", "message": "golden set cases must be a list"}]
    case_list = [case for case in raw_cases if isinstance(case, Mapping)]
    if len(case_list) != len(raw_cases):
        errors.append({"code": "golden_case_shape", "message": "every golden case must be an object"})
    for index, case in enumerate(case_list, 1):
        query = case.get("query")
        expected_filepath = case.get("expected_filepath")
        if not isinstance(query, str) or not query.strip() or not isinstance(expected_filepath, str) or not expected_filepath.strip():
            errors.append({"code": "golden_case_fields", "message": f"golden case {index} needs query and expected_filepath"})
        if isinstance(expected_filepath, str):
            relative = Path(expected_filepath.replace("\\", "/"))
            if relative.is_absolute() or _WINDOWS_ABSOLUTE.match(expected_filepath) or ".." in relative.parts:
                errors.append({"code": "golden_case_path", "message": f"golden case {index} has an unsafe expected_filepath"})
        kind = case.get("kind", "factual")
        if not isinstance(kind, str) or kind not in {"conceptual", "factual"}:
            errors.append({"code": "golden_case_kind", "message": f"golden case {index} has an unsupported kind"})
        if case.get("reviewed") is not True:
            errors.append({"code": "golden_case_not_reviewed", "message": f"golden case {index} requires reviewed=true"})
    reviewed = reviewed and bool(case_list) and not errors
    return reviewed, case_list, errors


def _expected_relative(value: str, documents_dir: Path) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(documents_dir.resolve()).as_posix()
        except ValueError:
            return candidate.as_posix()
    normalized = value.replace("\\", "/")
    for prefix in ("documents/", "rag/documents/"):
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized.lstrip("./")


def _score(query: str, path: str, content: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    path_tokens = _tokens(path)
    content_tokens = _tokens(content)
    overlap = len(query_tokens & content_tokens) / len(query_tokens)
    path_overlap = len(query_tokens & path_tokens) / len(query_tokens)
    phrase = 1.0 if query.casefold() in content.casefold() else 0.0
    return overlap + path_overlap * 0.5 + phrase * 0.5


def _corpus(documents_dir: Path) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for path in sorted(documents_dir.rglob("*")):
        if not path.is_symlink() and path.is_file() and path.suffix.casefold() in {
            ".md", ".markdown", ".txt", ".rst", ".adoc", ".json", ".yaml", ".yml",
            ".html", ".htm", ".xml", ".csv", ".py", ".c", ".h", ".cpp", ".js",
            ".jsx", ".ts", ".tsx", ".ipynb", ".xlsx", ".pptx",
        }:
            result.append((path.relative_to(documents_dir).as_posix(), path.read_text(encoding="utf-8", errors="replace")))
    return result


def evaluate_package(
    package_root: Path | str,
    cases: Mapping[str, Any] | Iterable[Mapping[str, Any]] | Path | str,
    *,
    thresholds: Mapping[str, float] | None = None,
    top_k: int = 5,
) -> EvaluationResult:
    """Evaluate lexical retrieval while keeping the quality gate reviewable."""

    root = Path(package_root).resolve()
    valid_top_k = isinstance(top_k, int) and not isinstance(top_k, bool) and 1 <= top_k <= 100
    metric_top_k = top_k if valid_top_k else 5
    recall_key = f"recall_at_{metric_top_k}"
    mrr_key = f"mrr_at_{metric_top_k}"
    if isinstance(cases, (Path, str)):
        try:
            payload = json.loads(Path(cases).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return EvaluationResult(
                False,
                {recall_key: 0.0, mrr_key: 0.0},
                [],
                [{"code": "golden_unreadable", "message": str(exc)}],
            )
    else:
        payload = cases
    reviewed, case_list, payload_errors = _case_payload(payload)
    errors: list[dict[str, str]] = list(payload_errors)
    if not reviewed:
        errors.append({"code": "golden_not_reviewed", "message": "golden cases require explicit review before evaluation"})
    if not case_list:
        errors.append({"code": "golden_empty", "message": "golden set is empty"})
    validation = validate_package(root)
    if not validation.ok:
        errors.append({"code": "invalid_package", "message": "package must validate before retrieval evaluation"})
    documents_dir = root / "rag" / "documents"
    corpus = _corpus(documents_dir) if documents_dir.is_dir() else []
    evaluated: list[dict[str, Any]] = []
    reciprocal_ranks: list[float] = []
    hits = 0
    if not valid_top_k:
        errors.append({"code": "top_k_out_of_range", "message": "top_k must be an integer from 1 through 100"})
    ranked_top_k = top_k if valid_top_k else 1
    for case in case_list:
        query = str(case.get("query") or "")
        expected = _expected_relative(str(case.get("expected_filepath") or ""), documents_dir)
        ranked = sorted(
            ((score, path) for path, content in corpus for score in [_score(query, path, content)]),
            key=lambda item: (-item[0], item[1]),
        )[:ranked_top_k]
        paths = [path for _, path in ranked]
        try:
            rank = paths.index(expected) + 1
        except ValueError:
            rank = None
        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
        evaluated.append(
            {
                "query": query,
                "expected_filepath": expected,
                "kind": case.get("kind", "factual"),
                "rank": rank,
                "expected_found": rank is not None,
                "retrieved": paths,
            }
        )
    total = len(case_list)
    metrics = {
        recall_key: hits / total if total else 0.0,
        mrr_key: sum(reciprocal_ranks) / total if total else 0.0,
    }
    required = {recall_key: 0.85, mrr_key: 0.7}
    if thresholds:
        for key, value in thresholds.items():
            if key not in required:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError, OverflowError):
                errors.append({"code": "threshold_invalid", "message": f"{key} must be a finite number from 0 through 1"})
                continue
            if not math.isfinite(numeric) or not 0 <= numeric <= 1:
                errors.append({"code": "threshold_out_of_range", "message": f"{key} must be a finite number from 0 through 1"})
                continue
            required[key] = numeric
    if total and metrics[recall_key] < required[recall_key]:
        errors.append({"code": "recall_below_threshold", "message": f"Recall@{metric_top_k} {metrics[recall_key]:.4f} < {required[recall_key]:.4f}"})
    if total and metrics[mrr_key] < required[mrr_key]:
        errors.append({"code": "mrr_below_threshold", "message": f"MRR@{metric_top_k} {metrics[mrr_key]:.4f} < {required[mrr_key]:.4f}"})
    diagnostics: list[str] = []
    if validation.ok:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("source", {}).get("version") and manifest.get("metrics", {}).get("rag", {}).get("mode") == "corpus-ready":
            diagnostics.append("RAG index metadata is corpus-ready; run the real knowledge-rag MCP evaluation before release.")
    return EvaluationResult(not errors, metrics, evaluated, errors, diagnostics=diagnostics, thresholds=required)


def generate_golden_candidates(package_root: Path | str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Generate review-required candidates from headings; never marks them approved."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("limit must be an integer from 1 through 1000")
    documents_dir = Path(package_root).resolve() / "rag" / "documents"
    candidates: list[dict[str, Any]] = []
    for relative, content in _corpus(documents_dir):
        title = next((match.group(1).strip() for line in content.splitlines() if (match := re.match(r"^#\s+(.+)$", line))), Path(relative).stem)
        candidates.append(
            {
                "query": title,
                "expected_filepath": relative,
                "kind": "factual",
                "reviewed": False,
                "review_note": "Review query and expected source independently before approval.",
            }
        )
        if len(candidates) >= limit:
            break
    return candidates
