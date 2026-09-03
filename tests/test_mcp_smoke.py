from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts import mcp_smoke


class _FakeProcess:
    def __init__(self, stdout: str, stderr: str = "") -> None:
        self.stdout = io.StringIO(stdout)
        self.stdin = io.StringIO()
        self.stderr = io.StringIO(stderr)
        self._terminated = False

    def poll(self) -> int | None:
        return 0 if self._terminated else None

    def terminate(self) -> None:
        self._terminated = True

    def wait(self, timeout: float | None = None) -> int:
        self._terminated = True
        return 0

    def kill(self) -> None:
        self._terminated = True


def _run_smoke(monkeypatch, messages: list[dict], *, stderr: str = "") -> int:
    process = _FakeProcess("\n".join(json.dumps(message) for message in messages) + ("\n" if messages else ""), stderr)
    monkeypatch.setattr(
        mcp_smoke,
        "discover_rag_python",
        lambda *_args, **_kwargs: SimpleNamespace(path=Path(sys.executable), exists=True),
    )
    monkeypatch.setattr(mcp_smoke, "runtime_environment", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(mcp_smoke.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(mcp_smoke.sys, "argv", ["mcp_smoke.py", "retry policy"])
    return mcp_smoke.main()


def _initialize(version: str = "4.8.5") -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": mcp_smoke.PROTOCOL_VERSION,
            "serverInfo": {"name": "knowledge-rag", "version": version},
        },
    }


def test_public_smoke_cli_reports_early_stdout_eof(monkeypatch, capsys) -> None:
    result = _run_smoke(monkeypatch, [], stderr="ERROR first\nWARN second\n")

    assert result == 1
    captured = capsys.readouterr()
    assert "stdout do servidor fechou" in captured.out
    assert "stderr_error" in captured.err
    assert "stderr_warning" in captured.err
    assert "ERROR first" not in captured.err
    assert "WARN second" not in captured.err


def test_public_smoke_cli_skips_missing_optional_runtime(monkeypatch, tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing-python"
    monkeypatch.setattr(
        mcp_smoke,
        "discover_rag_python",
        lambda *_args, **_kwargs: SimpleNamespace(path=missing, exists=False),
    )
    monkeypatch.setattr(mcp_smoke.sys, "argv", ["mcp_smoke.py", "--optional", "retry policy"])

    result = mcp_smoke.main()

    assert result == 0
    assert "rag_optional_unavailable" in capsys.readouterr().out


def test_public_smoke_cli_fails_missing_required_runtime(monkeypatch, tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing-python"
    monkeypatch.setattr(
        mcp_smoke,
        "discover_rag_python",
        lambda *_args, **_kwargs: SimpleNamespace(path=missing, exists=False),
    )
    monkeypatch.setattr(mcp_smoke.sys, "argv", ["mcp_smoke.py", "--required", "retry policy"])

    result = mcp_smoke.main()

    assert result == 2
    assert "rag_required_unavailable" in capsys.readouterr().out


def test_public_smoke_cli_rejects_server_version_drift(monkeypatch, capsys) -> None:
    result = _run_smoke(monkeypatch, [_initialize("4.6.0")])

    assert result == 1
    assert "differs" in capsys.readouterr().out


def test_public_smoke_cli_completes_handshake_and_search_without_corpus_content(monkeypatch, capsys) -> None:
    messages = [
        _initialize(),
        {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "search_knowledge"}]}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [
                    {
                        "text": json.dumps(
                            {"query": "retry policy", "results": [{"score": 0.9, "content": "secret corpus text"}]}
                        )
                    }
                ]
            },
        },
    ]

    result = _run_smoke(monkeypatch, messages)

    assert result == 0
    output = capsys.readouterr().out
    assert "initialize OK" in output
    assert "tools/list OK" in output
    assert "search_knowledge OK" in output
    assert "secret corpus text" not in output
