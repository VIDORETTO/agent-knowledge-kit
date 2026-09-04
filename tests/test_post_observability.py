# seam-scope: compatibility-infrastructure (redaction/adapter fixtures)
from __future__ import annotations

import io
import json

import pytest

from docops.mcp_client import JsonRpcMcpClient, McpEofError
from docops.observability import exception_diagnostic, redact_diagnostic, redact_report


def test_mcp_diagnostic_is_structured_limited_and_never_echoes_canaries() -> None:
    author_path = "C:" + r"\Users\gabri\private\guide.md"
    author_prefix = "C:" + r"\Users\gabri"
    event = redact_diagnostic(
        "ERROR token=super-secret-value path=" + author_path + " corpus=private text",
    )

    serialized = json.dumps(event)
    assert event["code"] == "stderr_error"
    assert len(serialized) < 500
    assert "super-secret-value" not in serialized
    assert author_prefix not in serialized
    assert "private text" not in serialized


def test_report_redacts_paths_and_corpus_content_in_structured_metadata() -> None:
    private_path = "C:" + r"\Users\gabri\private\guide.md"
    report = redact_report(
        {
            "query": "token=super-secret-value",
            "path": private_path,
            "content": "private corpus text",
        }
    )

    assert report["query"] == "<redacted-query>"
    assert report["path"] == "<local-path>"
    assert report["content"] == "<redacted-content>"

    ordinary = redact_report({"query": "customer-merger-confidential-roadmap"})
    assert ordinary["query"] == "<redacted-query>"


def test_report_redacts_canaries_in_unclassified_string_fields() -> None:
    secret = "u" * 24
    private_path = "C:" + r"\Users\gabri\private\note.txt"

    report = redact_report({"note": "token=" + secret + " path=" + private_path})

    assert secret not in report["note"]
    assert private_path not in report["note"]
    assert redact_report({"error": None})["error"] is None


def test_mcp_pipe_read_failure_is_reported_as_eof_with_child_exit_code() -> None:
    class BrokenReader:
        def readline(self) -> str:
            raise OSError("pipe closed")

    class FakeProcess:
        stdout = BrokenReader()
        stderr = io.StringIO()

        def poll(self) -> int:
            return 17

    client = JsonRpcMcpClient(FakeProcess())

    with pytest.raises(McpEofError) as caught:
        client.receive(0.5)

    assert caught.value.code == "mcp_eof"
    assert caught.value.exit_code == 17


def test_mcp_pipe_write_failure_is_reported_as_eof() -> None:
    class BrokenWriter:
        def write(self, _value: str) -> None:
            raise ValueError("I/O operation on closed pipe")

        def flush(self) -> None:
            return

    class FakeProcess:
        stdin = BrokenWriter()
        stdout = io.StringIO()
        stderr = io.StringIO()

        def poll(self) -> int:
            return 19

    client = JsonRpcMcpClient(FakeProcess())

    with pytest.raises(McpEofError) as caught:
        client.send({"jsonrpc": "2.0"})

    assert caught.value.code == "mcp_eof"
    assert caught.value.exit_code == 19


def test_exception_diagnostics_distinguish_timeout_from_eof_without_echoing_details() -> None:
    from docops.mcp_client import McpTimeoutError

    timeout = exception_diagnostic(McpTimeoutError("private timeout query"))
    eof = exception_diagnostic(McpEofError("private EOF query", exit_code=23))

    assert timeout == {
        "code": "mcp_timeout",
        "severity": "error",
        "category": "protocol",
        "redacted": True,
    }
    assert eof == {
        "code": "mcp_eof",
        "severity": "error",
        "category": "protocol",
        "redacted": True,
        "process_exit_code": 23,
    }
    assert "private" not in json.dumps([timeout, eof])
