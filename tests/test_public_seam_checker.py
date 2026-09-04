from __future__ import annotations

from pathlib import Path

from scripts.check_public_seams import audit


def test_checker_detects_multiline_and_nested_internal_imports(tmp_path: Path) -> None:
    (tmp_path / "test_hidden.py").write_text(
        """def fixture():
    from docops.pipeline import (
        PipelineOptions,
        run_pipeline,
    )
""",
        encoding="utf-8",
    )

    report = audit(tmp_path)

    assert report["ok"] is False
    assert report["findings"][0]["code"] == "unclassified_internal_import"


def test_checker_rejects_an_arbitrary_seam_scope_label(tmp_path: Path) -> None:
    (tmp_path / "test_hidden.py").write_text(
        "# seam-scope: trust-me\nfrom docops.pipeline import run_pipeline\n",
        encoding="utf-8",
    )

    report = audit(tmp_path)

    assert report["ok"] is False
    assert report["findings"][0]["code"] == "invalid_seam_scope"


def test_checker_accepts_public_api_and_explicit_infrastructure_scope(tmp_path: Path) -> None:
    (tmp_path / "test_public.py").write_text("import docops\n", encoding="utf-8")
    (tmp_path / "test_fixture.py").write_text(
        "# seam-scope: implementation-infrastructure (focused parser fixture)\n"
        "from docops.normalizer import normalize_file\n",
        encoding="utf-8",
    )

    assert audit(tmp_path)["ok"] is True
