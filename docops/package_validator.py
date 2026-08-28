"""Deterministic validation of the package produced by the operator."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config_audit import audit_config_file
from .divergence import inspect_package_divergence


@dataclass
class ValidationResult:
    """Result of validating a knowledge package."""

    ok: bool
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
        }


def _error(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def _safe_relative(root: Path, raw: Any, errors: list[dict[str, str]], code: str) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        _error(errors, code, "artifact path must be a non-empty relative string")
        return None
    candidate = Path(raw.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        _error(errors, code, f"artifact path must remain inside package: {raw!r}")
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        _error(errors, code, f"artifact path escapes package: {raw!r}")
        return None
    return resolved


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fields: dict[str, str] = {}
    for line in text[3:end].splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip("\"'")
    return fields


def validate_package(package_root: Path | str) -> ValidationResult:
    """Validate skill, router, RAG metadata, manifest and provenance.

    The checks use only files and JSON metadata. They never start an MCP
    server, download a model, execute a skill, or call an LLM.
    """

    root = Path(package_root).resolve()
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checks: dict[str, dict[str, Any]] = {}
    manifest_path = root / "manifest.json"
    manifest: dict[str, Any] = {}

    if not manifest_path.is_file():
        _error(errors, "missing_manifest", "manifest.json is required")
    else:
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _error(errors, "invalid_manifest", f"could not read manifest.json: {exc}")
        else:
            if isinstance(loaded, dict):
                manifest = loaded
            else:
                _error(errors, "invalid_manifest", "manifest.json must contain an object")

    if manifest.get("schema_version") != 1:
        _error(errors, "manifest_schema", "manifest schema_version must be 1")
    if not isinstance(manifest.get("run_id"), str) or not manifest["run_id"].strip():
        _error(errors, "manifest_run_id", "manifest run_id is required")

    source = manifest.get("source")
    if not isinstance(source, dict) or not source.get("canonical") or not source.get("input"):
        _error(errors, "source_provenance", "source.input and source.canonical are required")
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict) or not provenance.get("license"):
        _error(errors, "license_provenance", "provenance.license is required")
    elif provenance.get("redistribution") == "public" and str(provenance.get("license")).casefold() == "unknown":
        _error(errors, "license_required", "public packages require a declared source license")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        _error(errors, "artifact_map", "manifest artifacts must map skill, router and rag")
        artifacts = {}

    paths: dict[str, Path] = {}
    for name in ("skill", "router", "rag"):
        path = _safe_relative(root, artifacts.get(name), errors, f"{name}_path")
        if path is not None:
            paths[name] = path

    if "harness" in artifacts:
        harness_path = _safe_relative(root, artifacts.get("harness"), errors, "harness_path")
        if harness_path is not None and not harness_path.is_file():
            _error(errors, "missing_harness_manifest", "manifest harness artifact does not exist")
        elif harness_path is not None:
            try:
                harness = json.loads(harness_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                _error(errors, "invalid_harness_manifest", f"could not read harness manifest: {exc}")
            else:
                if not isinstance(harness, dict) or harness.get("schema_version") != 1:
                    _error(errors, "harness_schema", "harness manifest schema_version must be 1")
                elif harness.get("package_root") != "." or not isinstance(harness.get("mcp"), dict) or harness["mcp"].get("cwd") != ".":
                    _error(errors, "harness_paths", "harness manifest must use relative package paths")

    skill_dir = paths.get("skill")
    skill_file = skill_dir / "SKILL.md" if skill_dir else None
    if not skill_file or not skill_file.is_file():
        _error(errors, "missing_skill", "skill/SKILL.md (or the manifest skill path) is required")
    else:
        fields = _frontmatter(skill_file)
        checks["skill"] = {"ok": True, "path": "skill/SKILL.md", "name": fields.get("name")}
        if not fields.get("name") or not fields.get("description"):
            _error(errors, "skill_frontmatter", "skill SKILL.md needs name and description frontmatter")

    router_dir = paths.get("router")
    router_file = router_dir / "SKILL.md" if router_dir else None
    if not router_file or not router_file.is_file():
        _error(errors, "missing_router", "router/SKILL.md (or the manifest router path) is required")
    else:
        router_text = router_file.read_text(encoding="utf-8", errors="replace")
        checks["router"] = {"ok": True, "path": "router/SKILL.md"}
        if "search_knowledge" not in router_text:
            _error(errors, "router_rag_reference", "router must reference search_knowledge")
        if not re.search(r"cit(?:e|ation)", router_text, re.IGNORECASE):
            _error(errors, "router_citation_rule", "router must state a citation rule")
        if skill_file and skill_file.is_file():
            skill_name = _frontmatter(skill_file).get("name", "")
            if skill_name and skill_name not in router_text:
                _error(errors, "router_skill_reference", "router must reference the generated skill name")

    rag_dir = paths.get("rag")
    rag_docs = rag_dir / "documents" if rag_dir else None
    rag_index = rag_dir / "index.json" if rag_dir else None
    if not rag_dir or not rag_dir.is_dir():
        _error(errors, "missing_rag", "rag artifact directory is required")
    elif not rag_docs or not rag_docs.is_dir():
        _error(errors, "missing_rag_documents", "rag/documents directory is required")
    elif not rag_index or not rag_index.is_file():
        _error(errors, "missing_rag_index", "rag/index.json readiness metadata is required")
    else:
        try:
            index = json.loads(rag_index.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _error(errors, "invalid_rag_index", f"could not read rag/index.json: {exc}")
        else:
            if not isinstance(index, dict) or index.get("status") != "ready":
                _error(errors, "rag_not_ready", "rag/index.json must have status=ready")
            else:
                docs = list(rag_docs.rglob("*"))
                file_count = sum(1 for path in docs if path.is_file())
                if file_count < 1:
                    _error(errors, "empty_rag", "rag/documents must contain at least one source")
                checks["rag"] = {
                    "ok": file_count > 0,
                    "path": "rag",
                    "documents": index.get("documents", file_count),
                    "chunks": index.get("chunks", 0),
                }
                if isinstance(index.get("documents"), int) and index["documents"] != file_count:
                    _error(errors, "rag_document_count", "rag/index.json documents count does not match rag/documents")
                if isinstance(manifest.get("entries"), list) and not (rag_dir / "sources.json").is_file():
                    _error(errors, "missing_sources_manifest", "rag/sources.json is required for generated packages")

    manifest_entries = manifest.get("entries")
    if isinstance(manifest_entries, list):
        accepted_entries = [entry for entry in manifest_entries if isinstance(entry, dict) and entry.get("status") == "accepted"]
        identities = [
            (str(entry.get("canonical")), str(entry.get("version") or manifest.get("source", {}).get("version") or ""))
            for entry in accepted_entries
        ]
        if len(identities) != len(set(identities)):
            _error(errors, "duplicate_source", "manifest contains duplicate canonical source/version entries")
        rag_documents = root / "rag" / "documents"
        if rag_documents.is_dir() and accepted_entries:
            file_count = sum(1 for path in rag_documents.rglob("*") if path.is_file())
            if file_count != len(accepted_entries):
                _error(errors, "manifest_document_count", "accepted manifest entries do not match rag/documents")

    checks["manifest"] = {"ok": not any(error["code"].startswith("manifest") for error in errors)}
    config_path = root / "config.yaml"
    if config_path.is_file():
        config_result = audit_config_file(config_path)
        checks["config"] = config_result.to_dict()
        for error in config_result.errors:
            _error(errors, error["code"], error["message"])
    divergence = inspect_package_divergence(root)
    checks["synchronization"] = divergence.to_dict()
    warnings.extend(divergence.warnings)
    return ValidationResult(not errors, errors, warnings, checks)
