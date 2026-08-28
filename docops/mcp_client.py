"""Minimal stdio JSON-RPC client used by deterministic integration commands."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Mapping


class JsonRpcMcpClient:
    """MCP client with a reader queue so timeouts work on Windows pipes."""

    def __init__(self, process: subprocess.Popen[str]) -> None:
        self.process = process
        self._next_id = 1
        self._messages: Queue[dict[str, Any] | None] = Queue()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _read_stdout(self) -> None:
        if self.process.stdout is None:
            self._messages.put(None)
            return
        for line in iter(self.process.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                self._messages.put(value)
        self._messages.put(None)

    def _drain_stderr(self) -> None:
        if self.process.stderr is None:
            return
        for _line in iter(self.process.stderr.readline, ""):
            # Stderr is deliberately drained but not copied into the report;
            # server logs can contain document text and credentials supplied by
            # the host and must not become machine-readable output.
            continue

    def send(self, payload: Mapping[str, Any]) -> None:
        if self.process.stdin is None:
            raise RuntimeError("MCP stdin is closed")
        self.process.stdin.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def receive(self, timeout: float) -> dict[str, Any]:
        try:
            message = self._messages.get(timeout=timeout)
        except Empty as exc:
            raise TimeoutError("timeout waiting for MCP JSON-RPC response") from exc
        if message is None:
            raise RuntimeError("MCP server closed stdout before responding")
        return message

    def call(self, method: str, *, timeout: float = 120.0, **params: Any) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            remaining = max(0.01, deadline - time.monotonic())
            message = self.receive(remaining)
            if message.get("id") == request_id:
                return message
            # Notifications and responses to another request are ignored; this
            # client sends one request at a time, but MCP servers may emit logs.

    def close(self) -> None:
        process = self.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # This is the exact child process started by this client.
                process.kill()
                process.wait(timeout=10)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()


def start_mcp_server(python: Path | str, root: Path | str, *, env: Mapping[str, str] | None = None) -> JsonRpcMcpClient:
    """Start a local MCP server and complete the initialization handshake."""

    project_root = Path(root).resolve()
    environment = dict(os.environ if env is None else env)
    process = subprocess.Popen(
        [str(python), "-m", "mcp_server.server"],
        cwd=str(project_root),
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    client = JsonRpcMcpClient(process)
    try:
        response = client.call(
            "initialize",
            protocolVersion="2024-11-05",
            capabilities={},
            clientInfo={"name": "docops", "version": "0.1.0"},
        )
    except Exception:
        client.close()
        raise
    if response.get("error"):
        client.close()
        raise RuntimeError(f"MCP initialize failed: {response['error']}")
    client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return client


def text_payload(response: Mapping[str, Any]) -> list[str]:
    content = response.get("result", {}).get("content", []) if isinstance(response.get("result"), Mapping) else []
    return [str(part.get("text", "")) for part in content if isinstance(part, Mapping) and part.get("text") is not None]


def first_json_payload(response: Mapping[str, Any]) -> dict[str, Any] | None:
    for text in text_payload(response):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None
