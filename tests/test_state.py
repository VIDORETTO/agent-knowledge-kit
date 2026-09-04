# seam-scope: implementation-infrastructure (state unit tests)
from __future__ import annotations

from pathlib import Path

from docops.state import CheckpointStore, SourceRecord, StateStore, content_identity


def test_state_reconciles_create_repeat_update_and_remove_without_duplicate_identity(tmp_path: Path) -> None:
    state = StateStore(tmp_path / "state.json")
    first = SourceRecord(
        canonical="https://docs.example.test/guide",
        version="v1",
        content_hash="a" * 64,
        destination="guide.md",
    )

    assert state.plan([first]).added == [first]
    state.commit([first])
    assert state.plan([first]).is_empty

    updated = SourceRecord(first.canonical, first.version, "b" * 64, first.destination)
    diff = state.plan([updated])
    assert diff.added == []
    assert diff.updated == [(first, updated)]

    state.commit([updated])
    diff = state.plan([])
    assert diff.removed == [updated]


def test_content_identity_includes_canonical_source_version_and_hash() -> None:
    one = content_identity("https://docs.example.test", "v1", "a" * 64)
    same = content_identity("https://docs.example.test", "v1", "a" * 64)
    different_version = content_identity("https://docs.example.test", "v2", "a" * 64)

    assert one == same
    assert one != different_version
    assert len(one) == 64


def test_checkpoint_is_atomic_and_can_be_loaded_after_a_partial_phase(tmp_path: Path) -> None:
    checkpoints = CheckpointStore(tmp_path / "checkpoints.json")
    checkpoints.save("acquisition", {"status": "completed", "accepted": 2})

    assert checkpoints.load("acquisition") == {"status": "completed", "accepted": 2}
    assert checkpoints.load("missing") is None
