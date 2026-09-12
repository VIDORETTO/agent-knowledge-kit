# seam-scope: implementation-infrastructure (release contraction boundary fixtures)
from __future__ import annotations

import pytest

from docops.release_v2 import audit_release_surface, require_cutover_approved


def test_surface_auditor_reports_forbidden_terms_without_content_leak(tmp_path) -> None:
    source = tmp_path / "docops" / "example.py"
    source.parent.mkdir()
    source.write_text("course page knowledge-rag\n", encoding="utf-8")

    report = audit_release_surface(tmp_path, surface="all")

    assert report.ok is False
    assert report.findings[0]["path"] == "docops/example.py"
    assert "course page knowledge-rag" not in str(report.to_dict())


def test_surface_auditor_allows_explicit_migration_surface(tmp_path) -> None:
    source = tmp_path / "docops" / "migration.py"
    source.parent.mkdir()
    source.write_text("course is excluded\n", encoding="utf-8")

    assert audit_release_surface(tmp_path, surface="editorial").ok


def test_legacy_contraction_requires_an_approved_decision() -> None:
    with pytest.raises(RuntimeError):
        require_cutover_approved({"status": "not_run", "ok": False})

    require_cutover_approved({"status": "cutover_approved", "ok": True})
