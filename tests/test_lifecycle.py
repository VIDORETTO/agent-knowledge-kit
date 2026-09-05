from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(*args: str, expected_returncode: int = 0) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "docops", *args, "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == expected_returncode, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_lifecycle_events_are_debounced_and_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nStable.\n", encoding="utf-8")
    package = tmp_path / "package"
    package.mkdir()

    first = _run(
        "lifecycle",
        "event",
        "submit",
        "--package",
        str(package),
        "--type",
        "document.changed",
        "--source",
        str(source),
        "--source-root",
        str(tmp_path),
        "--revision",
        "r1",
        "--event-id",
        "event-1",
    )
    second = _run(
        "lifecycle",
        "event",
        "submit",
        "--package",
        str(package),
        "--type",
        "document.changed",
        "--source",
        str(source),
        "--source-root",
        str(tmp_path),
        "--revision",
        "r1",
        "--event-id",
        "event-1",
    )
    status = _run("lifecycle", "status", "--package", str(package))

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["duplicate"] is True
    assert status["events"]["pending"] == 1
    assert status["jobs"]["pending"] == 1


def test_lifecycle_candidate_requires_approval_and_publishes_with_rollback(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    guide = source / "guide.md"
    guide.write_text("# Guide\nVersion one.\n", encoding="utf-8")
    package = tmp_path / "package"
    initial = _run(
        "run",
        str(source),
        "--output",
        str(package),
        "--slug",
        "guide",
        "--license",
        "MIT",
    )
    assert initial["ok"] is True

    guide.write_text("# Guide\nVersion two.\n", encoding="utf-8")
    candidate = _run(
        "lifecycle",
        "candidate",
        "prepare",
        "--package",
        str(package),
        "--source",
        str(source),
        "--slug",
        "guide",
        "--license",
        "MIT",
    )
    candidate_id = candidate["candidate_id"]
    not_approved = _run(
        "lifecycle",
        "candidate",
        "publish",
        "--package",
        str(package),
        "--candidate-id",
        candidate_id,
        expected_returncode=1,
    )
    assert not_approved["ok"] is False
    assert not_approved["code"] == "candidate_not_approved"

    approval = _run(
        "lifecycle",
        "candidate",
        "approve",
        "--package",
        str(package),
        "--candidate-id",
        candidate_id,
        "--actor",
        "reviewer@example.test",
    )
    assert approval["ok"] is True
    published = _run(
        "lifecycle",
        "candidate",
        "publish",
        "--package",
        str(package),
        "--candidate-id",
        candidate_id,
    )
    assert published["ok"] is True
    assert (package / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == "# Guide\nVersion two.\n"
    release_id = published["release_id"]

    guide.write_text("# Guide\nVersion three.\n", encoding="utf-8")
    second_candidate = _run(
        "lifecycle",
        "candidate",
        "prepare",
        "--package",
        str(package),
        "--source",
        str(source),
        "--slug",
        "guide",
        "--license",
        "MIT",
    )
    _run(
        "lifecycle",
        "candidate",
        "approve",
        "--package",
        str(package),
        "--candidate-id",
        second_candidate["candidate_id"],
        "--actor",
        "reviewer@example.test",
    )
    second_release = _run(
        "lifecycle",
        "candidate",
        "publish",
        "--package",
        str(package),
        "--candidate-id",
        second_candidate["candidate_id"],
    )
    assert second_release["ok"] is True
    assert (package / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == "# Guide\nVersion three.\n"

    rolled_back = _run(
        "lifecycle",
        "candidate",
        "rollback",
        "--package",
        str(package),
        "--release-id",
        release_id,
    )
    assert rolled_back["ok"] is True
    assert (package / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == "# Guide\nVersion two.\n"


def test_conversation_learning_stays_quarantined_until_independent_review(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    opinion = _run(
        "lifecycle",
        "learning",
        "submit",
        "--package",
        str(package),
        "--claim",
        "The agent prefers short answers.",
        "--claim-type",
        "opinion",
    )
    blocked = _run(
        "lifecycle",
        "learning",
        "review",
        "--package",
        str(package),
        "--proposal-id",
        opinion["proposal_id"],
        "--decision",
        "admit",
        "--reviewer",
        "reviewer@example.test",
        expected_returncode=1,
    )
    assert blocked["code"] == "admission_requires_independent_evidence"

    fact = _run(
        "lifecycle",
        "learning",
        "submit",
        "--package",
        str(package),
        "--claim",
        "The retry limit is three attempts.",
        "--claim-type",
        "fact",
        "--evidence-json",
        '[{"source":"docs/retries.md","locator":"#policy"}]',
    )
    admitted = _run(
        "lifecycle",
        "learning",
        "review",
        "--package",
        str(package),
        "--proposal-id",
        fact["proposal_id"],
        "--decision",
        "admit",
        "--reviewer",
        "reviewer@example.test",
    )
    status = _run("lifecycle", "status", "--package", str(package))

    assert admitted["status"] == "admitted"
    assert status["proposals"]["admitted"] == 1
    assert not (package / "rag" / "documents").exists()


def test_worker_processes_a_due_event_into_a_review_candidate_without_touching_active(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    guide = source / "guide.md"
    guide.write_text("# Guide\nBefore.\n", encoding="utf-8")
    package = tmp_path / "package"
    initial = _run("run", str(source), "--output", str(package), "--slug", "guide", "--license", "MIT")
    assert initial["ok"] is True
    guide.write_text("# Guide\nAfter.\n", encoding="utf-8")

    _run(
        "lifecycle",
        "event",
        "submit",
        "--package",
        str(package),
        "--type",
        "document.changed",
        "--source",
        str(source),
        "--source-root",
        str(tmp_path),
        "--revision",
        "r2",
        "--debounce-seconds",
        "0",
    )
    worked = _run("lifecycle", "work", "--package", str(package), "--force")
    status = _run("lifecycle", "status", "--package", str(package))

    assert worked["ok"] is True
    assert worked["result"]["ok"] is True
    assert status["candidates"]["review_required"] == 1
    assert (package / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == "# Guide\nBefore.\n"


def test_source_reconcile_is_read_only_when_hashes_are_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    guide = source / "guide.md"
    guide.write_text("# Guide\nStable.\n", encoding="utf-8")
    package = tmp_path / "package"
    initial = _run("run", str(source), "--output", str(package), "--slug", "guide", "--license", "MIT")
    assert initial["ok"] is True

    unchanged = _run(
        "lifecycle",
        "source",
        "reconcile",
        "--package",
        str(package),
        "--source",
        str(source),
        "--source-root",
        str(tmp_path),
        "--slug",
        "guide",
        "--license",
        "MIT",
    )
    guide.write_text("# Guide\nChanged.\n", encoding="utf-8")
    changed = _run(
        "lifecycle",
        "source",
        "reconcile",
        "--package",
        str(package),
        "--source",
        str(source),
        "--source-root",
        str(tmp_path),
        "--slug",
        "guide",
        "--license",
        "MIT",
    )
    status = _run("lifecycle", "status", "--package", str(package))

    assert unchanged["changed"] is False
    assert changed["changed"] is True
    assert status["jobs"]["pending"] == 1
