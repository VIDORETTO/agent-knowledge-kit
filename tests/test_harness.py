# seam-scope: implementation-infrastructure (harness unit tests)
from __future__ import annotations

import json
from pathlib import Path

from docops.harness import build_harness_manifest, write_harness_manifest


def test_harness_manifest_uses_only_relative_paths_and_no_author_machine_path(tmp_path: Path) -> None:
    payload = build_harness_manifest(tmp_path)

    assert payload["schema_version"] == 1
    assert payload["skills"] == ["skill", "router"]
    assert payload["mcp"]["transport"] == "stdio"
    assert payload["mcp"]["cwd"] == "."
    assert payload["mcp"]["env"]["KNOWLEDGE_RAG_READ_ONLY"] == "1"
    assert "Users" not in json.dumps(payload)

    path = write_harness_manifest(tmp_path)
    assert path == tmp_path / "harness.json"
    assert json.loads(path.read_text(encoding="utf-8")) == payload
