"""Stable serializable types shared by the public API and compatibility CLI."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .observability import redact_report, redact_text
from .package_validator import ValidationResult
from .primitives import absolute_path_without_resolving


@dataclass
class PipelineOptions:
    """Mutable 1.0 CLI options retained as a compatibility input type."""

    output_dir: Path
    catalog: Path | None = None
    slug: str | None = None
    version: str | None = None
    scope: str | None = None
    language: str | None = None
    mode: str = "run"
    license: str | None = None
    redistribution: str = "private-only"
    index_rag: bool = False
    max_pages: int = 50
    max_depth: int = 2
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    allow_private_network: bool = False
    runtime_root: Path | None = None
    source_root: Path | None = None
    lease_policy: str = "fail"
    lease_timeout_seconds: float = 0.0
    stale_lease_seconds: float = 300.0

    def __post_init__(self) -> None:
        self.output_dir = absolute_path_without_resolving(self.output_dir)
        if self.mode not in {"create", "update", "run", "dry-run"}:
            raise ValueError("mode must be create, update, run or dry-run")
        if self.redistribution not in {"private-only", "internal", "public"}:
            raise ValueError("redistribution must be private-only, internal or public")
        if (
            isinstance(self.max_pages, bool)
            or not isinstance(self.max_pages, int)
            or isinstance(self.max_depth, bool)
            or not isinstance(self.max_depth, int)
            or self.max_pages < 1
            or self.max_depth < 0
        ):
            raise ValueError("max_pages must be positive and max_depth cannot be negative")
        if self.runtime_root is not None:
            self.runtime_root = Path(self.runtime_root).expanduser().resolve()
        self.source_root = Path(self.source_root or Path.cwd()).expanduser().resolve()
        if self.lease_policy not in {"fail", "wait"}:
            raise ValueError("lease_policy must be fail or wait")
        if self.lease_timeout_seconds < 0 or self.stale_lease_seconds <= 0:
            raise ValueError("lease timeouts must be non-negative and stale_lease_seconds must be positive")


class _FrozenDict(dict[str, Any]):
    """JSON-compatible dictionary that rejects every mutation."""

    def __init__(self, value: Mapping[str, Any]) -> None:
        dict.__init__(self, value)

    @staticmethod
    def _blocked(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("immutable result mapping")

    __setitem__ = _blocked
    __delitem__ = _blocked
    clear = _blocked
    pop = _blocked
    popitem = _blocked
    setdefault = _blocked
    update = _blocked
    __ior__ = _blocked


class _FrozenList(list[Any]):
    """JSON-compatible list that rejects every mutation."""

    def __init__(self, value: Any) -> None:
        list.__init__(self, value)

    @staticmethod
    def _blocked(*_args: Any, **_kwargs: Any) -> None:
        raise AttributeError("immutable result sequence")

    __setitem__ = _blocked
    __delitem__ = _blocked
    __iadd__ = _blocked
    __imul__ = _blocked
    append = _blocked
    clear = _blocked
    extend = _blocked
    insert = _blocked
    pop = _blocked
    remove = _blocked
    reverse = _blocked
    sort = _blocked


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _FrozenDict({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return _FrozenList(_freeze(item) for item in value)
    if isinstance(value, set):
        return _FrozenList(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, frozenset)):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class _FrozenValidationResult:
    """Immutable snapshot of the mutable validator result at the API boundary."""

    ok: bool
    errors: tuple[Mapping[str, Any], ...]
    warnings: tuple[Mapping[str, Any], ...]
    checks: Mapping[str, Any]

    @classmethod
    def from_result(cls, result: ValidationResult) -> "_FrozenValidationResult":
        return cls(
            result.ok,
            tuple(_freeze(error) for error in result.errors),
            tuple(_freeze(warning) for warning in result.warnings),
            _freeze(result.checks),
        )

    def to_dict(self) -> dict[str, Any]:
        return redact_report(
            {
                "schema_version": 1,
                "ok": self.ok,
                "errors": _thaw(self.errors),
                "warnings": _thaw(self.warnings),
                "checks": _thaw(self.checks),
            }
        )


@dataclass(frozen=True)
class PipelineResult:
    """Immutable terminal result shared by the API and legacy CLI adapter."""

    ok: bool
    output_dir: Path
    manifest: Mapping[str, Any]
    validation: ValidationResult | _FrozenValidationResult | None = None
    state_diff: Mapping[str, int] = field(default_factory=lambda: {"added": 0, "updated": 0, "removed": 0})
    written_files: int = 0
    errors: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    outcome: Mapping[str, Any] = field(
        default_factory=lambda: {
            "status": "failed",
            "code": "unknown",
            "phase": "unknown",
            "message": "operation did not produce an outcome",
            "exit_code": 1,
        }
    )
    exit_code: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest", _freeze(self.manifest))
        if self.validation is not None and not isinstance(self.validation, _FrozenValidationResult):
            object.__setattr__(self, "validation", _FrozenValidationResult.from_result(self.validation))
        object.__setattr__(self, "state_diff", _freeze(self.state_diff))
        object.__setattr__(self, "errors", _freeze(self.errors))
        object.__setattr__(self, "warnings", _freeze(self.warnings))
        object.__setattr__(self, "outcome", _freeze(self.outcome))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "ok": self.ok,
            "output_dir": redact_text(self.output_dir),
            "manifest": redact_report(self.manifest),
            "validation": self.validation.to_dict() if self.validation else None,
            "state_diff": _thaw(self.state_diff),
            "written_files": self.written_files,
            "errors": redact_report(_thaw(self.errors)),
            "warnings": [redact_text(warning) for warning in self.warnings],
            "outcome": redact_report(_thaw(self.outcome)),
            "exit_code": self.exit_code,
        }

    def json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
