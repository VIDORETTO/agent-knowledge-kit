"""Roda evaluate_retrieval do knowledge-rag com o golden set.

Uso:
    python scripts/evaluate_golden.py [--cases golden-set/test-cases.json]

Entrada: envelope revisado {"schema_version": 1, "reviewed": true,
"cases": [{"query": ..., "expected_filepath": ..., "reviewed": true}, ...]}
(JSON). Imprime MRR@5, Recall@5 e o breakdown por pergunta; a versão atual do
servidor não expõe Precision@5.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = PROJECT_ROOT / "golden-set" / "test-cases.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops import __version__  # noqa: E402
from docops.runtime import discover_rag_python, runtime_environment  # noqa: E402


class McpClient:
    def __init__(self, proc):
        self.proc = proc
        self._next_id = 1

    def send_json(self, payload: dict) -> None:
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def recv_json(self, timeout: float = 180.0) -> dict:
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
                continue
        raise RuntimeError("stdout do servidor fechou antes de responder")

    def call(self, method: str, **params) -> dict:
        req_id = self._next_id
        self._next_id += 1
        self.send_json({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        while True:
            msg = self.recv_json()
            if msg.get("id") == req_id:
                return msg
            if msg.get("method") and msg.get("id") is None:
                continue


def drain(proc) -> None:
    for line in iter(proc.stderr.readline, ""):
        if "ERROR" in line or "WARN" in line:
            sys.stderr.write(f"  [server] {line}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    args = parser.parse_args()

    payload = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("reviewed") is not True:
        sys.exit("golden set deve ser um envelope schema_version=1 com reviewed=true")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        sys.exit("golden set vazio ou inválido")

    # O server compara expected_filepath com o campo `source` literal (path
    # absoluto). Normaliza "relativos a PROJECT_ROOT" para caminho absoluto.
    for case in cases:
        if not isinstance(case, dict):
            sys.exit("golden set contém um caso inválido")
        if case.get("reviewed") is not True:
            sys.exit("todos os casos do golden set precisam de reviewed=true")
        exp = case.get("expected_filepath", "")
        if exp and not exp.startswith(str(PROJECT_ROOT)):
            case["expected_filepath"] = str((PROJECT_ROOT / exp).resolve())
    print(f"Evaluando {len(cases)} test cases de {args.cases}")

    rag_python = discover_rag_python(PROJECT_ROOT)
    if not rag_python.exists:
        sys.exit(f"Python do knowledge-rag não encontrado: {rag_python.path} — rode bootstrap com --rag")
    env = runtime_environment(PROJECT_ROOT)
    proc = None
    try:
        proc = subprocess.Popen(
            [str(rag_python.path), "-m", "mcp_server.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env, cwd=str(PROJECT_ROOT),
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        threading.Thread(target=drain, args=(proc,), daemon=True).start()
        client = McpClient(proc)
        init = client.call("initialize", protocolVersion="2024-11-05", capabilities={},
                           clientInfo={"name": "evaluate_golden", "version": __version__})
        if init.get("error"):
            sys.exit(f"initialize falhou: {init['error']}")
        client.send_json({"jsonrpc": "2.0", "method": "notifications/initialized"})

        resp = client.call("tools/call", name="evaluate_retrieval",
                           arguments={"test_cases": json.dumps(cases)})
        for part in resp.get("result", {}).get("content", []):
            text = part.get("text", "")
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                print(text)
                continue
            print(json.dumps(payload, indent=2, ensure_ascii=False))
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
