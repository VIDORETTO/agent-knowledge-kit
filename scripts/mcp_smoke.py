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
import subprocess
import sys
import threading
import time
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


def _drain_stderr(proc: subprocess.Popen) -> None:
    """Lê stderr do servidor em thread (evita deadlock no pipe) e telegrafa."""
    for line in iter(proc.stderr.readline, ""):
        sys.stderr.write(f"  [server] {line}")
        sys.stderr.flush()


class McpClient:
    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self._next_id = 1

    def send_json(self, payload: dict) -> None:
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def recv_json(self, timeout: float = 60.0) -> dict:
        """Lê linhas de stdout até obter uma mensagem JSON-RPC válida."""
        deadline = time.time() + timeout

        for line in iter(self.proc.stdout.readline, ""):
            if time.time() > deadline:
                raise TimeoutError("timeout esperando resposta JSON-RPC")
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                # prints de bootstrap do servidor (não-JSON) — ignorar
                continue
        raise RuntimeError("stdout do servidor fechou antes de responder")

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

    drip = threading.Thread(target=_drain_stderr, args=(proc,), daemon=True)
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
        print(f"    serverInfo: {init['result'].get('serverInfo')}")

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
    except (TimeoutError, RuntimeError) as e:
        print(f"FALHOU: {e}")

        stderr = b"".join(proc.stderr.readlines()).decode("utf-8", "replace")
        print("--- stderr (últimas 40 linhas) ---")
        print("\n".join(stderr.splitlines()[-40:]))
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass
        try:
            proc.stderr.close()
            proc.stdout.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
