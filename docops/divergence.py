"""Detect version drift between generated skill and indexed source metadata."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DivergenceReport:
    synchronized: bool
    warnings: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "synchronized": self.synchronized, "warnings": self.warnings}


def inspect_package_divergence(package_root: Path | str) -> DivergenceReport:
    """Compare the source version recorded by the manifest and skill."""

    root = Path(package_root).resolve()
    manifest_path = root / "manifest.json"
    skill_path = root / "skill" / "SKILL.md"
    if not manifest_path.is_file() or not skill_path.is_file():
        return DivergenceReport(False, [{"code": "divergence_inputs_missing", "message": "manifest and skill are required"}])
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DivergenceReport(False, [{"code": "divergence_manifest_invalid", "message": "manifest could not be read"}])
    source = manifest.get("source") if isinstance(manifest, dict) else {}
    source_version = source.get("version") if isinstance(source, dict) else None
    skill_text = skill_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^- Version: `([^`]*)`$", skill_text, re.MULTILINE)
    skill_version = match.group(1) if match else None
    if source_version and skill_version and str(source_version) != skill_version:
        return DivergenceReport(
            False,
            [{"code": "skill_rag_divergence", "message": f"skill version {skill_version!r} differs from source version {source_version!r}"}],
        )
    if source_version and not skill_version:
        return DivergenceReport(False, [{"code": "skill_version_missing", "message": "skill has no source version marker"}])
    return DivergenceReport(True)
