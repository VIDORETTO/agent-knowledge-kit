from __future__ import annotations

import io
import threading
from types import SimpleNamespace

import pytest

from scripts.mcp_smoke import McpClient, _drain_stderr, _server_version_error


class _FakeProcess:
    def __init__(self, stdout) -> None:
        self.stdout = stdout
        self.stdin = io.StringIO()
        self.stderr = io.StringIO()


def test_mcp_client_times_out_without_blocking_on_stdout() -> None:
    released = threading.Event()

    class _BlockingReader:
        def readline(self):
            released.wait()
            return ""

    client = McpClient(_FakeProcess(_BlockingReader()))
    try:
        with pytest.raises(TimeoutError, match="timeout esperando"):
            client.recv_json(timeout=0.01)
    finally:
        released.set()


def test_mcp_client_reports_early_stdout_eof() -> None:
    client = McpClient(_FakeProcess(io.StringIO("")))

    with pytest.raises(RuntimeError, match="stdout do servidor fechou"):
        client.recv_json(timeout=0.2)


def test_stderr_drain_keeps_text_lines_for_failure_diagnostics(capsys: pytest.CaptureFixture[str]) -> None:
    lines: list[str] = []
    _drain_stderr(SimpleNamespace(stderr=io.StringIO("ERROR first\nWARN second\n")), lines)

    assert lines == ["ERROR first\n", "WARN second\n"]
    assert "ERROR first" in capsys.readouterr().err


def test_server_version_check_rejects_drift_and_accepts_the_installed_version() -> None:
    assert _server_version_error({"name": "knowledge-rag", "version": "4.8.5"}, expected_version="4.8.5") is None
    assert "differs" in (
        _server_version_error({"name": "knowledge-rag", "version": "4.6.0"}, expected_version="4.8.5") or ""
    )
