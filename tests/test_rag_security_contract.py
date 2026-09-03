from __future__ import annotations

from pathlib import Path

SERVER_SOURCE = Path(__file__).parents[1] / "skills" / "vendor" / "knowledge-rag" / "mcp_server" / "server.py"


def test_rag_security_contract_is_local_persistent_and_does_not_enable_remote_code() -> None:
    source = SERVER_SOURCE.read_text(encoding="utf-8")

    assert "chromadb.PersistentClient(" in source
    assert "chromadb.HttpClient(" not in source
    assert "trust_remote_code" not in source
    assert "models_cache_dir" in source
