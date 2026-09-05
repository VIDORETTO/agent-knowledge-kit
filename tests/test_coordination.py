from __future__ import annotations

from docops.coordination import TriggerPolicy, assess_skill_trigger


def test_ten_distinct_conceptual_changes_request_one_skill_review() -> None:
    events = [
        {
            "event_id": f"event-{index}",
            "event_type": "document.changed",
            "source_id": f"doc-{index}",
            "observed_revision": f"r-{index}",
            "occurred_at": "2026-09-05T00:00:00Z",
            "payload": {"conceptual_impact": True},
        }
        for index in range(10)
    ]

    decision = assess_skill_trigger(events, corpus_documents=100, now=1788566400.0)

    assert decision.requested is True
    assert "document_count" in decision.reasons
    assert decision.affected_documents == 10


def test_reindex_only_and_reverted_changes_do_not_count_as_conceptual_novelty() -> None:
    events = [
        {
            "event_id": "reindex",
            "event_type": "document.changed",
            "source_id": "doc-reindex",
            "payload": {"reindex_only": True},
        },
        {
            "event_id": "changed",
            "event_type": "document.changed",
            "source_id": "doc-reverted",
            "payload": {"conceptual_impact": True},
        },
        {
            "event_id": "reverted",
            "event_type": "document.changed",
            "source_id": "doc-reverted",
            "payload": {"reverted": True},
        },
    ]

    decision = assess_skill_trigger(
        events,
        corpus_documents=100,
        now=1788566400.0,
        policy=TriggerPolicy(min_documents=1, min_documents_with_fraction=1),
    )

    assert decision.requested is False
    assert decision.affected_documents == 0


def test_critical_conflict_bypasses_batch_threshold() -> None:
    decision = assess_skill_trigger(
        [
            {
                "event_id": "conflict",
                "event_type": "source.conflict",
                "source_id": "doc-1",
                "payload": {"critical": True},
            }
        ],
        corpus_documents=1000,
        now=1788566400.0,
    )

    assert decision.requested is True
    assert decision.reasons == ("critical_impact",)
