from __future__ import annotations

import json
from pathlib import Path

import docops.rag_sync as rag_sync
from docops.rag_sync import RagSynchronizer, package_rag_config


def test_package_rag_config_is_relative_and_local_only(tmp_path: Path) -> None:
    config = package_rag_config()

    assert config["paths"] == {
        "documents_dir": "./rag/documents",
        "data_dir": "./rag/data",
        "models_cache_dir": "./rag/models_cache",
    }
    assert config["server"]["transport"] == "stdio"
    assert config["server"]["auth"]["bearer_token"] == ""
    assert {".py", ".html", ".ipynb"} <= set(config["documents"]["supported_formats"])


def test_rag_synchronizer_runs_reindex_status_stats_and_smoke(monkeypatch, tmp_path: Path) -> None:
    package = tmp_path / "package"
    (package / "rag" / "documents").mkdir(parents=True)
    (package / "rag" / "documents" / "guide.md").write_text("# Guide", encoding="utf-8")
    executable = tmp_path / "python"
    executable.touch()
    calls: list[str] = []

    class FakeClient:
        def call(self, _method: str, *, name: str, arguments: dict, **_kwargs: object) -> dict:
            calls.append(name)
            payload = {
                "reindex_documents": {"status": "started"},
                "get_reindex_status": {"active": False, "progress": 1},
                "get_index_stats": {"stats": {"total_documents": 1, "total_chunks": 1}},
                "search_knowledge": {"results": []},
            }[name]
            return {"result": {"content": [{"text": json.dumps(payload)}]}}

        def close(self) -> None:
            calls.append("close")

    monkeypatch.setattr(rag_sync, "start_mcp_server", lambda *_args, **_kwargs: FakeClient())

    result = RagSynchronizer(python=executable).sync(package)

    assert result.ok, result.error
    assert result.smoke == {"ok": True, "result_count": 0}
    assert calls == ["reindex_documents", "get_reindex_status", "get_index_stats", "search_knowledge", "close"]


def test_rag_synchronizer_rejects_a_symlinked_package_config(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    external = tmp_path / "external.yaml"
    external.write_text("server:\n  transport: stdio\n", encoding="utf-8")
    try:
        (package / "config.yaml").symlink_to(external)
    except OSError:
        return

    result = RagSynchronizer().sync(package)

    assert not result.ok
    assert result.error["code"] == "unsafe_rag_config"


def test_rag_synchronizer_fails_when_mcp_returns_no_json_payload(monkeypatch, tmp_path: Path) -> None:
    package = tmp_path / "package"
    (package / "rag" / "documents").mkdir(parents=True)
    (package / "rag" / "documents" / "guide.md").write_text("# Guide", encoding="utf-8")
    executable = tmp_path / "python"
    executable.touch()

    class EmptyClient:
        def call(self, *_args: object, **_kwargs: object) -> dict:
            return {"result": {"content": []}}

        def close(self) -> None:
            return

    monkeypatch.setattr(rag_sync, "start_mcp_server", lambda *_args, **_kwargs: EmptyClient())

    result = RagSynchronizer(python=executable).sync(package)

    assert not result.ok
    assert result.error["code"] == "rag_integration_failed"
