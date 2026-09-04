from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

import docops


def _request(source: Path, output: Path, *, mode: str = "run") -> docops.OperationRequest:
    return docops.OperationRequest(
        source,
        docops.OperationOptions(output_dir=output, source_root=source.parent, slug="guide", license="MIT", mode=mode),
    )


def test_public_plan_preview_apply_noop_and_cleanup_form_one_lifecycle_contract(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nPublic seam.\n", encoding="utf-8")
    output = tmp_path / "package"

    operation = docops.plan(_request(source, output, mode="dry-run"))
    preview = docops.preview(operation)
    assert preview.ok
    assert preview.outcome["code"] == "planned"
    assert not output.exists()

    applied = docops.apply(docops.plan(_request(source, output)))
    assert applied.ok, applied.errors
    repeated = docops.apply(docops.plan(_request(source, output, mode="update")))
    assert repeated.ok, repeated.errors
    assert repeated.outcome["status"] == "succeeded"

    cleaned = docops.cleanup(output)
    assert cleaned["ok"] is True
    inspected = docops.inspect(output)
    assert inspected["managed"] is True
    assert inspected["active"]["validation"]["ok"] is True


def test_public_apply_rejects_a_plan_that_is_stale_after_source_mutation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    document = source / "guide.md"
    document.write_text("# Guide\nBefore.\n", encoding="utf-8")
    output = tmp_path / "package"
    assert docops.apply(docops.plan(_request(source, output))).ok

    document.write_text("# Guide\nAfter.\n", encoding="utf-8")
    stale = docops.plan(_request(source, output, mode="update"))
    document.write_text("# Guide\nChanged again.\n", encoding="utf-8")
    result = docops.apply(stale)

    assert not result.ok
    assert result.outcome["code"] == "stale_plan"
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == "# Guide\nBefore.\n"


def test_public_cleanup_preserves_all_generated_residue_when_promotion_journal_is_incomplete(
    tmp_path: Path,
) -> None:
    output = tmp_path / "package"
    journal = output.parent / ".package.docops.promotion.json"
    journal.write_text("not-json", encoding="utf-8")
    staging = output.parent / ".package.staging-crashed"
    backup = output.parent / ".package.backup-crashed"
    staging.mkdir()
    backup.mkdir()
    (staging / "marker").write_text("staging", encoding="utf-8")
    (backup / "marker").write_text("backup", encoding="utf-8")

    cleaned = docops.cleanup(output, retention_seconds=0)
    inspected = docops.inspect(output)

    assert cleaned["ok"] is True
    assert {item["type"] for item in cleaned["preserved"]} >= {"staging", "backup", "promotion-journal"}
    assert staging.is_dir()
    assert backup.is_dir()
    assert inspected["recovery"]["status"] == "incomplete"


def test_public_recovery_and_cleanup_diagnostics_redact_private_residue_names(tmp_path: Path) -> None:
    output = tmp_path / "tenant-secret-package"
    stage = output.parent / f".{output.name}.staging-private-attempt"
    backup = output.parent / f".{output.name}.backup-private-attempt"
    stage.mkdir()
    backup.mkdir()
    journal = output.parent / f".{output.name}.docops.promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "output_name": output.name,
                "stage_name": stage.name,
                "backup_name": backup.name,
                "plan_hash": "opaque-plan-hash",
                "phase": "prepared",
                "had_active": True,
                "active_generation_valid": False,
                "stage_generation_valid": False,
            }
        ),
        encoding="utf-8",
    )

    inspected = docops.inspect(output)
    cleaned = docops.cleanup(output, retention_seconds=0)
    public_diagnostics = json.dumps({"inspect": inspected, "cleanup": cleaned})

    assert output.name not in public_diagnostics
    assert stage.name not in public_diagnostics
    assert backup.name not in public_diagnostics


def test_public_inspect_reports_reader_busy_when_writer_does_not_settle(tmp_path: Path) -> None:
    output = tmp_path / "package"
    lock = output.parent / f".{output.name}.docops.writer.lock"
    lock.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pid": os.getpid(),
                "started_at": time.time(),
                "hostname": socket.gethostname(),
                "token": "live-writer-token",
            }
        ),
        encoding="utf-8",
    )
    try:
        started = time.monotonic()
        inspected = docops.inspect(output)
    finally:
        lock.unlink(missing_ok=True)

    assert time.monotonic() - started >= 4.5
    assert inspected["inspection"]["status"] == "timed_out"
    assert inspected["inspection"]["code"] == "reader_busy"


def test_public_cleanup_bounds_corrupt_journal_residue_without_deleting_best_recovery_candidates(
    tmp_path: Path,
) -> None:
    output = tmp_path / "package"
    journal = output.parent / ".package.docops.promotion.json"
    journal.write_text("not-json", encoding="utf-8")
    old_stage = output.parent / ".package.staging-old"
    best_stage = output.parent / ".package.staging-best"
    old_backup = output.parent / ".package.backup-old"
    best_backup = output.parent / ".package.backup-best"
    for residue in (old_stage, best_stage, old_backup, best_backup):
        residue.mkdir()
        (residue / "marker").write_text(residue.name, encoding="utf-8")
    for residue in (old_stage, old_backup):
        os.utime(residue, (1.0, 1.0))

    cleaned = docops.cleanup(output, retention_seconds=0)

    assert cleaned["ok"] is True
    assert not old_stage.exists()
    assert not old_backup.exists()
    assert best_stage.is_dir()
    assert best_backup.is_dir()
    preserved_types = [item["type"] for item in cleaned["preserved"]]
    assert preserved_types.count("staging") == 1
    assert preserved_types.count("backup") == 1
