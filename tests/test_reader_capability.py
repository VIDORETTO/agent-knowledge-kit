from __future__ import annotations

from pathlib import Path

from docops.runtime import runtime_environment


def test_runtime_seam_can_issue_query_only_or_maintenance_capability(tmp_path: Path) -> None:
    reader = runtime_environment(tmp_path, read_only=True)
    writer = runtime_environment(tmp_path, read_only=False)

    assert reader["KNOWLEDGE_RAG_READ_ONLY"] == "1"
    assert writer["KNOWLEDGE_RAG_READ_ONLY"] == "0"
