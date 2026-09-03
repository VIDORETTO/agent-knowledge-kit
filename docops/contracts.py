"""Small, dependency-free validator for the public DOCOPS contracts.

The JSON files in ``schemas/`` are the normative source in a checkout.  This
module deliberately implements only the JSON-Schema vocabulary used by those
files so the operator remains usable from a wheel without adding a validation
dependency or contacting a network service.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

_SCHEMA_FILES = {
    "manifest": "manifest.schema.json",
    "harness": "harness.schema.json",
    "golden": "golden.schema.json",
    "validation": "validation.schema.json",
    "plan": "plan.schema.json",
    "result": "result.schema.json",
    "outcome": "outcome.schema.json",
    "evaluation": "evaluation.schema.json",
    "golden-candidates": "golden-candidates.schema.json",
}


@dataclass(frozen=True)
class ContractResult:
    """A serializable result for one normative artifact contract."""

    ok: bool
    artifact: str
    errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "ok": self.ok, "artifact": self.artifact, "errors": self.errors}


def _schema_roots() -> tuple[Path, ...]:
    module_root = Path(__file__).resolve()
    return (
        module_root.parents[1] / "schemas",
        module_root.parent / "schemas",
    )


def schema_path(artifact: str) -> Path | None:
    """Return the installed or checkout schema path for ``artifact``."""

    filename = _SCHEMA_FILES.get(artifact)
    if filename is None:
        return None
    for root in _schema_roots():
        candidate = root / filename
        if candidate.is_file():
            return candidate
    return None


def load_schema(artifact: str) -> dict[str, Any]:
    """Load one public schema, raising a useful error when it is unavailable."""

    path = schema_path(artifact)
    if path is None:
        raise FileNotFoundError(f"schema not found for artifact {artifact!r}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"schema for {artifact!r} must be an object")
    return value


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _error(errors: list[dict[str, str]], code: str, path: str, message: str) -> None:
    errors.append({"code": code, "path": path or "$", "message": message})


def _resolve_ref(schema: Mapping[str, Any], reference: str) -> Mapping[str, Any] | None:
    if not reference.startswith("#/"):
        return None
    value: Any = schema
    for part in reference[2:].split("/"):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value if isinstance(value, Mapping) else None


def _validate(
    value: Any, rule: Mapping[str, Any], root_schema: Mapping[str, Any], path: str, errors: list[dict[str, str]]
) -> None:
    reference = rule.get("$ref")
    if isinstance(reference, str):
        target = _resolve_ref(root_schema, reference)
        if target is None:
            _error(errors, "contract_ref", path, f"unsupported schema reference {reference!r}")
        else:
            _validate(value, target, root_schema, path, errors)
        return

    if "const" in rule and value != rule["const"]:
        _error(errors, "contract_const", path, f"value must equal {rule['const']!r}")
    enum = rule.get("enum")
    if isinstance(enum, list) and value not in enum:
        _error(errors, "contract_enum", path, f"value must be one of {enum!r}")

    expected = rule.get("type")
    if isinstance(expected, str) and not _json_type_matches(value, expected):
        _error(errors, "contract_type", path, f"expected JSON type {expected}")
        return
    if isinstance(expected, list) and not any(
        isinstance(item, str) and _json_type_matches(value, item) for item in expected
    ):
        _error(errors, "contract_type", path, f"expected one of JSON types {expected!r}")
        return

    if isinstance(value, Mapping):
        required = rule.get("required", [])
        if isinstance(required, list):
            for name in required:
                if isinstance(name, str) and name not in value:
                    _error(errors, "contract_required", f"{path}.{name}" if path else name, "required field is missing")
        properties = rule.get("properties", {})
        if isinstance(properties, Mapping):
            for name, child_rule in properties.items():
                if name in value and isinstance(child_rule, Mapping):
                    _validate(value[name], child_rule, root_schema, f"{path}.{name}" if path else str(name), errors)
    if isinstance(value, list) and isinstance(rule.get("items"), Mapping):
        for index, item in enumerate(value):
            _validate(item, rule["items"], root_schema, f"{path}[{index}]", errors)
    if isinstance(value, str) and isinstance(rule.get("minLength"), int) and len(value) < rule["minLength"]:
        _error(errors, "contract_min_length", path, "string is shorter than the minimum length")
    if isinstance(value, list) and isinstance(rule.get("minItems"), int) and len(value) < rule["minItems"]:
        _error(errors, "contract_min_items", path, "array has fewer items than the minimum")


def validate_artifact(artifact: str, payload: Any) -> ContractResult:
    """Validate a public artifact against its checked-in JSON schema."""

    if artifact not in _SCHEMA_FILES:
        return ContractResult(
            False, artifact, [{"code": "contract_unknown", "path": "$", "message": "unknown public artifact"}]
        )
    try:
        schema = load_schema(artifact)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return ContractResult(
            False, artifact, [{"code": "contract_schema_unavailable", "path": "$", "message": str(exc)}]
        )
    errors: list[dict[str, str]] = []
    _validate(payload, schema, schema, "$", errors)
    return ContractResult(not errors, artifact, errors)


def contract_names() -> tuple[str, ...]:
    """Return the public artifact names covered by this validator."""

    return tuple(_SCHEMA_FILES)
