"""Lightweight, reproducible retrieval evaluation for a produced package."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .contracts import validate_artifact
from .manifest import redact_metadata
from .observability import redact_report, redact_text
from .package_validator import validate_package
from .readiness import assess_readiness
from .retrieval import RetrievalError, SkillRetrievalAdapter, adapter_for_package, route_query
from .storage import write_json_atomic

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
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "ok": self.ok,
            "metrics": self.metrics,
            "cases": redact_report(self.cases),
            "errors": redact_report(self.errors),
            "warnings": [redact_text(warning) for warning in self.warnings],
            "diagnostics": [redact_text(diagnostic) for diagnostic in self.diagnostics],
            "thresholds": self.thresholds,
            "metadata": redact_report(self.metadata),
        }


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value)}


def _case_payload(
    cases: Mapping[str, Any] | Iterable[Mapping[str, Any]],
) -> tuple[bool, list[Mapping[str, Any]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    if isinstance(cases, Mapping):
        contract = validate_artifact("golden", cases)
        if not contract.ok:
            errors.extend(
                {
                    "code": error["code"],
                    "message": f"golden contract {error.get('path', '$')}: {error['message']}",
                }
                for error in contract.errors
            )
        reviewed = cases.get("reviewed") is True
        if cases.get("schema_version") != 1 or type(cases.get("schema_version")) is not int:
            errors.append({"code": "golden_schema", "message": "golden set schema_version must be 1"})
        if "cases" not in cases:
            errors.append({"code": "golden_cases", "message": "golden set cases must be a list"})
        raw_cases = cases.get("cases", [])
    else:
        reviewed = False
        raw_cases = cases
        errors.append(
            {"code": "golden_schema", "message": "golden set must be an object with schema_version and cases"}
        )
    if not isinstance(raw_cases, list):
        return reviewed, [], [{"code": "golden_cases", "message": "golden set cases must be a list"}]
    case_list = [case for case in raw_cases if isinstance(case, Mapping)]
    if len(case_list) != len(raw_cases):
        errors.append({"code": "golden_case_shape", "message": "every golden case must be an object"})
    for index, case in enumerate(case_list, 1):
        query = case.get("query")
        expected_filepath = case.get("expected_filepath")
        kind = case.get("kind", "factual")
        missing_filepath = kind != "router" and (
            not isinstance(expected_filepath, str) or not expected_filepath.strip()
        )
        if not isinstance(query, str) or not query.strip() or missing_filepath:
            errors.append(
                {"code": "golden_case_fields", "message": f"golden case {index} needs query and expected_filepath"}
            )
        if isinstance(expected_filepath, str):
            relative = Path(expected_filepath.replace("\\", "/"))
            if relative.is_absolute() or _WINDOWS_ABSOLUTE.match(expected_filepath) or ".." in relative.parts:
                errors.append(
                    {"code": "golden_case_path", "message": f"golden case {index} has an unsafe expected_filepath"}
                )
        if not isinstance(kind, str) or kind not in {"conceptual", "factual", "router"}:
            errors.append({"code": "golden_case_kind", "message": f"golden case {index} has an unsupported kind"})
        if kind == "router" and case.get("expected_route") not in {"skill", "rag", "both"}:
            errors.append({"code": "golden_case_route", "message": f"golden case {index} needs expected_route"})
        if case.get("reviewed") is not True:
            errors.append(
                {"code": "golden_case_not_reviewed", "message": f"golden case {index} requires reviewed=true"}
            )
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
    for prefix in ("documents/", "rag/documents/", "skill/"):
        if normalized.startswith(prefix):
            return normalized[len(prefix) :]
    return normalized.lstrip("./")


def _safe_adapter_metadata(adapter: Any, fallback: Mapping[str, Any]) -> dict[str, Any]:
    if adapter is None:
        return dict(fallback)
    try:
        value = adapter.metadata()
    except Exception:
        return dict(fallback)
    return redact_report(redact_metadata(dict(value))) if isinstance(value, Mapping) else dict(fallback)


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
        if (
            not path.is_symlink()
            and path.is_file()
            and path.suffix.casefold()
            in {
                ".md",
                ".markdown",
                ".txt",
                ".rst",
                ".adoc",
                ".json",
                ".yaml",
                ".yml",
                ".html",
                ".htm",
                ".xml",
                ".csv",
                ".py",
                ".c",
                ".h",
                ".cpp",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
                ".ipynb",
                ".xlsx",
                ".pptx",
            }
        ):
            result.append(
                (path.relative_to(documents_dir).as_posix(), path.read_text(encoding="utf-8", errors="replace"))
            )
    return result


def generate_golden_candidates(package_root: Path | str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Generate review-required candidates from headings; never marks them approved."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("limit must be an integer from 1 through 1000")
    documents_dir = Path(package_root).resolve() / "rag" / "documents"
    candidates: list[dict[str, Any]] = []
    for relative, content in _corpus(documents_dir):
        title = next(
            (match.group(1).strip() for line in content.splitlines() if (match := re.match(r"^#\s+(.+)$", line))),
            Path(relative).stem,
        )
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


def evaluate_package(
    package_root: Path | str,
    cases: Mapping[str, Any] | Iterable[Mapping[str, Any]] | Path | str,
    *,
    thresholds: Mapping[str, float] | None = None,
    top_k: int = 5,
    adapter: Any = None,
    runtime_root: Path | str | None = None,
) -> EvaluationResult:
    """Evaluate cases through a named retrieval/skill adapter.

    The default remains the fast lexical diagnostic for compatibility.  A
    release gate must pass ``adapter="mcp"`` so its metrics are produced by
    the same backend delivered to the harness.
    """

    root = Path(package_root).resolve()
    valid_top_k = isinstance(top_k, int) and not isinstance(top_k, bool) and 1 <= top_k <= 100
    metric_top_k = top_k if valid_top_k else 5
    recall_key = f"recall_at_{metric_top_k}"
    mrr_key = f"mrr_at_{metric_top_k}"
    if isinstance(cases, (Path, str)):
        try:
            payload = json.loads(Path(cases).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return EvaluationResult(
                False, {recall_key: 0.0, mrr_key: 0.0}, [], [{"code": "golden_unreadable", "message": redact_text(exc)}]
            )
    else:
        payload = cases
    reviewed, case_list, payload_errors = _case_payload(payload)
    errors: list[dict[str, str]] = list(payload_errors)
    if not reviewed:
        errors.append(
            {"code": "golden_not_reviewed", "message": "golden cases require explicit review before evaluation"}
        )
    if not case_list:
        errors.append({"code": "golden_empty", "message": "golden set is empty"})
    validation = validate_package(root)
    if not validation.ok:
        errors.append({"code": "invalid_package", "message": "package must validate before retrieval evaluation"})
    if not valid_top_k:
        errors.append({"code": "top_k_out_of_range", "message": "top_k must be an integer from 1 through 100"})
    ranked_top_k = top_k if valid_top_k else 1
    try:
        retrieval = adapter_for_package(root, adapter, runtime_root=runtime_root)
    except (OSError, ValueError, RetrievalError) as exc:
        errors.append({"code": getattr(exc, "code", "adapter_unavailable"), "message": str(exc)})
        retrieval = None
    skill_adapter = SkillRetrievalAdapter(root)
    evaluated: list[dict[str, Any]] = []
    reciprocal_ranks: list[float] = []
    hits = 0
    route_total = 0
    route_hits = 0
    kind_totals: dict[str, int] = {"factual": 0, "conceptual": 0}
    kind_hits: dict[str, int] = {"factual": 0, "conceptual": 0}
    route_metadata = {
        "factual": _safe_adapter_metadata(retrieval, {"backend": "unavailable", "adapter": "unknown", "mode": "gate"}),
        "conceptual": _safe_adapter_metadata(
            skill_adapter, {"backend": "unavailable", "adapter": "unknown", "mode": "gate"}
        ),
        "router": {"backend": "policy", "adapter": "route_query", "mode": "gate", "profile": "documented-policy-v1"},
    }
    result: EvaluationResult | None = None
    try:
        for case in case_list:
            query = str(case.get("query") or "")
            kind = str(case.get("kind", "factual"))
            expected_root = root / "skill" if kind == "conceptual" else root / "rag" / "documents"
            expected = _expected_relative(str(case.get("expected_filepath") or ""), expected_root)
            safe_expected = redact_text(expected).replace("\\", "/")
            retrieved: list[dict[str, Any]] = []
            rank: int | None = None
            route = None
            selected_metadata: Mapping[str, Any] = route_metadata.get(kind, route_metadata["factual"])
            if kind == "router":
                route = route_query(query)
                expected_route = case.get("expected_route")
                if isinstance(expected_route, str):
                    route_total += 1
                    route_hits += int(route == expected_route)
                selected_metadata = route_metadata["router"]
            else:
                kind_totals[kind] = kind_totals.get(kind, 0) + 1
                selected_adapter = skill_adapter if kind == "conceptual" else retrieval
                if selected_adapter is None:
                    errors.append({"code": "adapter_unavailable", "message": "no adapter available for evaluation"})
                else:
                    try:
                        retrieved = selected_adapter.search(query, max_results=ranked_top_k)
                    except RetrievalError as exc:
                        error = {"code": exc.code, "message": redact_text(exc)}
                        if exc.details:
                            error.update(redact_report(exc.details))
                        errors.append(error)
                    except Exception as exc:
                        errors.append({"code": "retrieval_failed", "message": redact_text(exc)})
                paths = [str(item.get("source", "")).replace("\\", "/") for item in retrieved]
                try:
                    rank = paths.index(expected) + 1
                except ValueError:
                    rank = None
                if rank is not None:
                    hits += 1
                    kind_hits[kind] = kind_hits.get(kind, 0) + 1
                    reciprocal_ranks.append(1.0 / rank)
                else:
                    reciprocal_ranks.append(0.0)
            evaluated.append(
                {
                    "query": "<redacted-query>",
                    "expected_filepath": safe_expected,
                    "kind": kind,
                    "route": route,
                    "rank": rank,
                    "expected_found": rank is not None if kind != "router" else None,
                    "retrieved": [redact_text(str(item.get("source", ""))).replace("\\", "/") for item in retrieved],
                    "adapter": selected_metadata.get("adapter"),
                    "backend": selected_metadata.get("backend"),
                    "profile": selected_metadata.get("profile"),
                }
            )
        total = sum(1 for case in case_list if str(case.get("kind", "factual")) != "router")
        metrics: dict[str, float] = {
            recall_key: hits / total if total else 0.0,
            mrr_key: sum(reciprocal_ranks) / total if total else 0.0,
        }
        if route_total:
            metrics["route_accuracy"] = route_hits / route_total
        required = {recall_key: 0.85, mrr_key: 0.7}
        if thresholds:
            for key, value in thresholds.items():
                if key == "route_accuracy" and route_total:
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError, OverflowError):
                        errors.append(
                            {
                                "code": "threshold_invalid",
                                "message": "route_accuracy must be a finite number from 0 through 1",
                            }
                        )
                        continue
                    if not math.isfinite(numeric) or not 0 <= numeric <= 1:
                        errors.append(
                            {
                                "code": "threshold_out_of_range",
                                "message": "route_accuracy must be a finite number from 0 through 1",
                            }
                        )
                    elif metrics["route_accuracy"] < numeric:
                        errors.append(
                            {"code": "route_below_threshold", "message": "router accuracy is below its threshold"}
                        )
                    continue
                if key not in required:
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError, OverflowError):
                    errors.append(
                        {"code": "threshold_invalid", "message": f"{key} must be a finite number from 0 through 1"}
                    )
                    continue
                if not math.isfinite(numeric) or not 0 <= numeric <= 1:
                    errors.append(
                        {"code": "threshold_out_of_range", "message": f"{key} must be a finite number from 0 through 1"}
                    )
                    continue
                required[key] = numeric
        if total and metrics[recall_key] < required[recall_key]:
            errors.append(
                {
                    "code": "recall_below_threshold",
                    "message": f"Recall@{metric_top_k} {metrics[recall_key]:.4f} < {required[recall_key]:.4f}",
                }
            )
        if total and metrics[mrr_key] < required[mrr_key]:
            errors.append(
                {
                    "code": "mrr_below_threshold",
                    "message": f"MRR@{metric_top_k} {metrics[mrr_key]:.4f} < {required[mrr_key]:.4f}",
                }
            )
        if thresholds and "route_accuracy" in thresholds and not route_total:
            errors.append(
                {"code": "route_cases_missing", "message": "route_accuracy requires at least one reviewed router case"}
            )
        metadata = redact_report(redact_metadata(dict(route_metadata["factual"])))
        metadata.update(
            {
                "top_k": metric_top_k,
                "case_count": len(case_list),
                "routes": redact_report(redact_metadata(route_metadata)),
                "package_readiness": assess_readiness(root).get("state"),
                "kind_counts": kind_totals,
                "kind_recall": {kind: kind_hits[kind] / count if count else 0.0 for kind, count in kind_totals.items()},
            }
        )
        diagnostics: list[str] = []
        if metadata.get("mode") == "diagnostic":
            diagnostics.append("Lexical retrieval is a diagnostic; use adapter=mcp for the release gate.")
        result = EvaluationResult(
            not errors, metrics, evaluated, errors, diagnostics=diagnostics, thresholds=required, metadata=metadata
        )
    except Exception as exc:
        errors.append({"code": "evaluation_failed", "message": "retrieval evaluation failed safely"})
        result = EvaluationResult(
            False, {recall_key: 0.0, mrr_key: 0.0}, evaluated, errors, diagnostics=[redact_text(exc)]
        )
    finally:
        if retrieval is not None:
            try:
                retrieval.close()
            except Exception:
                pass
    if result is None:
        result = EvaluationResult(False, {recall_key: 0.0, mrr_key: 0.0}, evaluated, errors)
    contract = validate_artifact("evaluation", result.to_dict())
    if not contract.ok:
        result.errors.extend(
            {"code": error["code"], "message": f"evaluation contract {error.get('path', '$')}: {error['message']}"}
            for error in contract.errors
        )
        result.ok = False
    evidence = {
        "schema_version": 1,
        "ok": result.ok,
        "backend": result.metadata.get("backend"),
        "adapter": result.metadata.get("adapter"),
        "mode": result.metadata.get("mode"),
        "profile": result.metadata.get("profile"),
        "top_k": result.metadata.get("top_k"),
        "case_count": len(result.cases),
        "metrics": result.metrics,
    }
    try:
        (root / ".docops").mkdir(parents=True, exist_ok=True)
        write_json_atomic(root / ".docops" / "evaluation.json", evidence)
        manifest_path = root / "manifest.json"
        if manifest_path.is_file() and not manifest_path.is_symlink():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(manifest, dict):
                manifest["readiness"] = assess_readiness(root)
                metrics_value = manifest.setdefault("metrics", {})
                if isinstance(metrics_value, dict):
                    metrics_value["evaluation"] = evidence
                write_json_atomic(manifest_path, manifest)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        result.warnings.append("evaluation evidence could not be persisted")
    final_contract = validate_artifact("evaluation", result.to_dict())
    if not final_contract.ok:
        result.errors.extend(
            {"code": error["code"], "message": f"evaluation contract {error.get('path', '$')}: {error['message']}"}
            for error in final_contract.errors
        )
        result.ok = False
    return result
