"""Smoke test para o servidor MCP knowledge-rag (stdio).

Sobe o servidor como subprocesso, faz o handshake MCP (initialize ->
initialized), lista as ferramentas e chama search_knowledge uma vez.

Uso:
    python scripts/mcp_smoke.py [query]

Exemplo:
    python scripts/mcp_smoke.py "retry policy"
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops import __version__  # noqa: E402
from docops.runtime import discover_rag_python, runtime_environment  # noqa: E402

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
            lines.append(line)
            sys.stderr.write(f"  [server] {line}")
            sys.stderr.flush()
    except (OSError, ValueError):
        # The child may close the pipe while the parent is handling an early
        # termination. The captured lines are still useful for diagnostics.
        return


_STDOUT_EOF = object()


def _server_version_error(server_info: object, *, expected_version: str | None = None) -> str | None:
    """Return a version-drift error when the installed package exposes one."""

    if not isinstance(server_info, dict):
        return "MCP initialize did not return a serverInfo object"
    expected = expected_version
    if expected is None:
        try:
            expected = package_version("knowledge-rag")
        except PackageNotFoundError:
            return None
    actual = server_info.get("version")
    if actual != expected:
        return f"knowledge-rag serverInfo version {actual!r} differs from installed package {expected!r}"
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
        self.send_json(
            {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        )
        while True:
            msg = self.recv_json()
            kind = msg.get("method")
            if kind is None and msg.get("id") == req_id:
                return msg
            if kind and msg.get("id") is None:
                print(f"    [notification] {kind}")


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "retry policy"

    rag_python = discover_rag_python(PROJECT_ROOT)
    if not rag_python.exists:
        print(f"FALHOU: Python do knowledge-rag não encontrado: {rag_python.path}")
        return 1
    env = runtime_environment(PROJECT_ROOT)

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
            print(f"FALHOU initialize: {init['error']}")
            return 1
        print(f"    initialize OK — protocolVersion {init['result'].get('protocolVersion')}")
        server_info = init["result"].get("serverInfo")
        print(f"    serverInfo: {server_info}")
        version_error = _server_version_error(server_info)
        if version_error:
            print(f"FALHOU: {version_error}")
            return 1

        client.send_json({"jsonrpc": "2.0", "method": "notifications/initialized"})

        tools = client.call("tools/list")
        names = sorted(t["name"] for t in tools["result"]["tools"])
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
                print(f"FALHOU tools/call: {result['error']}")
                return 1
            content = result["result"]["content"]
            for part in content:
                text = part.get("text", "")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    print(text)
                    continue
                rc = data.get("result_count", data.get("results", []))
                print(f"    search_knowledge OK — query={data.get('query')!r} "
                      f"results={len(data.get('results', None) or [])} "
                      f"result_count={rc} "
                      f"search_method={data.get('results', [{}])[0].get('search_method', '-') if data.get('results') else '-'}")
                for r in (data.get("results") or [])[:3]:
                    print(f"      [{r.get('score', 0):.3f}] {r.get('source')} — {r.get('content', '')[:70]}...")
                if not data.get("results"):
                    print("    [WARN] 0 resultados — verifique se documents/ tem arquivos indexados")
    except (TimeoutError, RuntimeError, BrokenPipeError, OSError) as e:
        print(f"FALHOU: {e}")
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
