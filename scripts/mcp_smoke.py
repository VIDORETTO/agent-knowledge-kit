"""Smoke test para o servidor MCP knowledge-rag (stdio).

Sobe o servidor como subprocesso, faz o handshake MCP (initialize ->
initialized), lista as ferramentas e chama search_knowledge uma vez.

Uso:
    python scripts/mcp_smoke.py [query]

Exemplo:
    python scripts/mcp_smoke.py "retry policy"
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops import __version__  # noqa: E402
from docops.observability import redact_diagnostic, redact_report, redact_text  # noqa: E402
from docops.runtime import RAG_RUNTIME_VERSION, discover_rag_python, runtime_contract, runtime_environment  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"

# Windows often starts the parent console in cp1252. The documentation can
# contain Unicode/emoji, so keep the smoke report printable instead of
# failing after a successful MCP/search call.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _drain_stderr(proc: subprocess.Popen, lines: list[str]) -> None:
    """Lê stderr do servidor em thread (evita deadlock no pipe) e telegrafa."""
    try:
        for line in iter(proc.stderr.readline, ""):
            diagnostic = json.dumps(redact_diagnostic(line), ensure_ascii=False, sort_keys=True)
            lines.append(diagnostic)
            sys.stderr.write(f"  [server] {diagnostic}\n")
            sys.stderr.flush()
    except (OSError, ValueError):
        # The child may close the pipe while the parent is handling an early
        # termination. The captured lines are still useful for diagnostics.
        return


_STDOUT_EOF = object()


def _server_version_error(server_info: object, *, expected_version: str | None = None) -> str | None:
    """Return a version-drift error against an explicit runtime contract."""

    if not isinstance(server_info, dict):
        return "MCP initialize did not return a serverInfo object"
    expected = expected_version or RAG_RUNTIME_VERSION
    actual = server_info.get("version")
    if actual != expected:
        return f"knowledge-rag serverInfo version {actual!r} differs from selected runtime {expected!r}"
    return None


class McpClient:
    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self._next_id = 1
        self._stdout_lines: queue.Queue[str | object] = queue.Queue()
        self._stdout_reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._stdout_reader.start()

    def _read_stdout(self) -> None:
        """Move blocking pipe reads off the caller so timeout is enforceable."""
        try:
            for line in iter(self.proc.stdout.readline, ""):
                self._stdout_lines.put(line)
        except (OSError, ValueError):
            pass
        finally:
            self._stdout_lines.put(_STDOUT_EOF)

    def send_json(self, payload: dict) -> None:
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def recv_json(self, timeout: float = 60.0) -> dict:
        """Lê linhas de stdout até obter uma mensagem JSON-RPC válida."""
        deadline = time.monotonic() + timeout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("timeout esperando resposta JSON-RPC")
            try:
                line = self._stdout_lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError("timeout esperando resposta JSON-RPC") from exc
            if line is _STDOUT_EOF:
                raise RuntimeError("stdout do servidor fechou antes de responder")
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                # prints de bootstrap do servidor (não-JSON) — ignorar
                continue

    def call(self, method: str, **params) -> dict:
        req_id = self._next_id
        self._next_id += 1
        self.send_json({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        while True:
            msg = self.recv_json()
            kind = msg.get("method")
            if kind is None and msg.get("id") == req_id:
                return msg
            if kind and msg.get("id") is None:
                print(f"    [notification] {kind}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="retry policy")
    required_group = parser.add_mutually_exclusive_group()
    required_group.add_argument("--required", dest="rag_required", action="store_true")
    required_group.add_argument("--optional", dest="rag_required", action="store_false")
    parser.set_defaults(rag_required=None)
    args = parser.parse_args(sys.argv[1:])
    required = args.rag_required
    if required is None:
        required = os.environ.get("DOCOPS_REQUIRE_RAG", "1").strip().casefold() not in {"0", "false", "no"}
    query = args.query

    rag_python = discover_rag_python(PROJECT_ROOT)
    if not rag_python.exists:
        if not required:
            print(
                f"SKIPPED [rag_optional_unavailable]: Python do knowledge-rag não encontrado: {redact_text(rag_python.path)}"
            )
            return 0
        print(
            f"FALHOU [rag_required_unavailable]: Python do knowledge-rag não encontrado: {redact_text(rag_python.path)}"
        )
        return 2
    env = runtime_environment(PROJECT_ROOT)
    contract = runtime_contract(
        PROJECT_ROOT,
        python=rag_python.path,
        python_source=getattr(rag_python, "source", None),
        environ=env,
    )
    print(
        f"    runtime: source={redact_text(contract.get('python_source'))} "
        f"version={redact_text(contract.get('expected_version'))}"
    )

    proc = subprocess.Popen(
        [str(rag_python.path), "-m", "mcp_server.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(PROJECT_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    stderr_lines: list[str] = []
    drip = threading.Thread(target=_drain_stderr, args=(proc, stderr_lines), daemon=True)
    drip.start()

    try:
        client = McpClient(proc)

        init = client.call(
            "initialize",
            protocolVersion=PROTOCOL_VERSION,
            capabilities={},
            clientInfo={"name": "smoke", "version": __version__},
        )
        if init.get("error"):
            print(f"FALHOU [mcp_initialize_failed]: {redact_report(init['error'])}")
            return 1
        print(f"    initialize OK — protocolVersion {init['result'].get('protocolVersion')}")
        server_info = init["result"].get("serverInfo")
        print(f"    serverInfo: {redact_report(server_info)}")
        version_error = _server_version_error(server_info, expected_version=contract["expected_version"])
        if version_error:
            print(f"FALHOU [version_drift]: {version_error}")
            return 1

        client.send_json({"jsonrpc": "2.0", "method": "notifications/initialized"})

        tools = client.call("tools/list")
        names = sorted(
            redact_text(str(item.get("name", "<unnamed>")))
            for item in tools["result"].get("tools", [])
            if isinstance(item, dict)
        )
        print(f"    tools/list OK — {len(names)} tools:")
        for n in names:
            print(f"      - {n}")

        if "search_knowledge" in names:
            result = client.call(
                "tools/call",
                name="search_knowledge",
                arguments={"query": query, "max_results": 3},
            )
            if result.get("error"):
                print(f"FALHOU [mcp_search_failed] tools/call: {redact_report(result['error'])}")
                return 1
            content = result["result"]["content"]
            for part in content:
                text = part.get("text", "")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    print(f"    MCP response diagnostic: {redact_diagnostic(text)}")
                    continue
                results = data.get("results") if isinstance(data.get("results"), list) else []
                result_count = data.get("result_count")
                if not isinstance(result_count, int):
                    result_count = len(results)
                search_method = (
                    results[0].get("search_method", "-") if results and isinstance(results[0], dict) else "-"
                )
                print(
                    f"    search_knowledge OK — query={redact_text(data.get('query', ''))!r} "
                    f"results={len(results)} "
                    f"result_count={result_count} "
                    f"search_method={redact_text(search_method)}"
                )
                for item in results[:3]:
                    if isinstance(item, dict):
                        print(f"      [{item.get('score', 0):.3f}] result available (content omitted from smoke logs)")
                if not results:
                    print("    [WARN] 0 resultados — verifique se documents/ tem arquivos indexados")
    except (TimeoutError, RuntimeError, BrokenPipeError, OSError) as e:
        code = (
            "mcp_timeout" if isinstance(e, TimeoutError) else "mcp_eof" if isinstance(e, RuntimeError) else "mcp_pipe"
        )
        print(f"FALHOU [{code}]: {redact_text(e)}")
        print("--- stderr (últimas 40 linhas) ---")
        print("".join(stderr_lines[-40:]), end="")
        return 1
    finally:
        try:
            if proc.poll() is None:
                proc.terminate()
        except (OSError, ValueError):
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except (OSError, ValueError):
                pass
        except (OSError, ValueError):
            pass
        try:
            proc.stderr.close()
            proc.stdout.close()
        except (OSError, ValueError):
            pass
        drip.join(timeout=1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
