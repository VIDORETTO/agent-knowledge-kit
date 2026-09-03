"""Sincroniza documents/ com o índice do knowledge-rag via MCP (stdio).

Modos:
    python scripts/update_rag.py plan       # mostra diff (add/update/remove) sem aplicar
    python scripts/update_rag.py apply      # aplica diff via add/update/remove_document e
                                            # dispara reindex_documents + poll do status
    python scripts/update_rag.py status     # estado local + get_index_stats do servidor

Estado: .rag_state.json { "<caminho relativo a documents/">: "<sha256>" }
Apenas arquivos com as extensões suportadas pelo servidor são mapeadas.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
STATE_FILE = PROJECT_ROOT / ".rag_state.json"
MUTATION_TIMEOUT_SECONDS = 2400.0

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops import __version__  # noqa: E402
from docops.runtime import discover_rag_python, runtime_environment  # noqa: E402
from docops.storage import write_json_atomic  # noqa: E402

_SUPPORTED_SUFFIXES = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".adoc",
    ".pdf",
    ".docx",
    ".py",
    ".c",
    ".h",
    ".cpp",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".csv",
    ".ipynb",
    ".xlsx",
    ".pptx",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class McpClient:
    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self._next_id = 1
        self._messages: Queue[dict | None] = Queue()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def _read_stdout(self) -> None:
        """Buffer JSON-RPC messages so recv_json can enforce a real timeout.

        ``subprocess.stdout.readline()`` blocks on Windows named pipes, so a
        deadline checked only after readline returns cannot protect a long
        document ingest. A reader thread plus Queue makes the timeout
        effective while preserving notification handling in ``call``.
        """
        for line in iter(self.proc.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            try:
                self._messages.put(json.loads(line))
            except json.JSONDecodeError:
                # Bootstrap prints are redirected to stderr, but keep this
                # tolerant for older server versions.
                continue
        self._messages.put(None)

    def send_json(self, payload: dict) -> None:
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def recv_json(self, timeout: float = 120.0) -> dict:
        try:
            message = self._messages.get(timeout=timeout)
        except Empty as exc:
            raise TimeoutError("timeout esperando resposta JSON-RPC") from exc
        if message is None:
            raise RuntimeError("stdout do servidor fechou antes de responder")
        return message

    def call(self, method: str, *, timeout: float = 120.0, **params) -> dict:
        req_id = self._next_id
        self._next_id += 1
        self.send_json({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
        while True:
            msg = self.recv_json(timeout=timeout)
            if msg.get("id") == req_id:
                return msg
            if msg.get("method") and msg.get("id") is None:
                continue

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            if stream:
                stream.close()


def drain(proc: subprocess.Popen) -> None:
    for line in iter(proc.stderr.readline, ""):
        if "WARNING" in line or "ERROR" in line or "INFO" in line:
            sys.stderr.write(f"  [server] {line}")


def connect() -> McpClient:
    rag_python = discover_rag_python(PROJECT_ROOT)
    if not rag_python.exists:
        sys.exit(f"Python do knowledge-rag não encontrado: {rag_python.path} — rode bootstrap com --rag")
    env = runtime_environment(PROJECT_ROOT)
    # The explicit add/update calls below already synchronize the corpus. The
    # filesystem watcher would otherwise launch a concurrent reindex for every
    # write, racing the MCP call and leaving duplicate/stale metadata.
    env["KNOWLEDGE_RAG_WATCHER_DISABLED"] = "1"
    env.pop("HF_ENDPOINT", None)  # hf-mirror quebra download; usar cdn.hf.co padrão
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
    threading.Thread(target=drain, args=(proc,), daemon=True).start()
    client = McpClient(proc)
    atexit.register(client.close)
    resp = client.call(
        "initialize",
        protocolVersion="2024-11-05",
        capabilities={},
        clientInfo={"name": "update_rag", "version": __version__},
    )
    if resp.get("error"):
        sys.exit(f"initialize falhou: {resp['error']}")
    client.send_json({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return client


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    write_json_atomic(STATE_FILE, state)


def scan() -> dict[str, str]:
    current = {}
    if not DOCUMENTS_DIR.exists():
        return current
    for path in sorted(DOCUMENTS_DIR.rglob("*")):
        if not path.is_symlink() and path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES:
            current[str(path.relative_to(DOCUMENTS_DIR)).replace("\\", "/")] = sha256(path)
    return current


def compute_diff(current: dict, state: dict):
    adds = [p for p in current if p not in state]
    updates = [p for p in current if p in state and state[p] != current[p]]
    removes = [p for p in state if p not in current]
    return adds, updates, removes


def plan() -> int:
    state = load_state()
    current = scan()
    adds, updates, removes = compute_diff(current, state)
    print(f"Estado atual: {len(state)} arquivos mapeados | no disco: {len(current)}")
    print(f"  add ({len(adds)}):    {', '.join(adds) or '—'}")
    print(f"  update ({len(updates)}): {', '.join(updates) or '—'}")
    print(f"  remove ({len(removes)}): {', '.join(removes) or '—'}")
    return 0


def apply(direct: bool = False) -> int:
    state = load_state()
    current = scan()
    adds, updates, removes = compute_diff(current, state)
    if not (adds or updates or removes):
        print("Nada para sincronizar.")
        return 0

    client = connect()

    if direct:
        # Modo lote: deixa o servidor varrer documents/ (detecção mtime/size é
        # mais eficiente que add_document por arquivo em corpora grandes).
        print(
            f"Modo lote: reindex_documents(force=True) para {len(adds)} add / "
            f"{len(updates)} update / {len(removes)} remove"
        )
        client.call("tools/call", name="reindex_documents", arguments={"force": True})
        deadline = time.time() + 1800
        while time.time() < deadline:
            r = client.call("tools/call", name="get_reindex_status", arguments={})
            text = "".join(p.get("text", "") for p in r.get("result", {}).get("content", []))
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {}
            status = data.get("reindex") or {}
            if not status.get("active", False):
                print("Reindex completo.")
                save_state(current)
                return 0
            print(f"  reindex: {status.get('progress', '?')} ({status.get('percent', '?')}%)")
            time.sleep(5)
        print("Timeout (30min) esperando reindex; use get_reindex_status para acompanhar.")
        save_state(current)
        return 1

    succeeded = set()
    failed = set()

    for i, rel in enumerate(adds, 1):
        path = DOCUMENTS_DIR / rel
        content = path.read_text(encoding="utf-8", errors="replace")
        try:
            r = client.call(
                "tools/call",
                timeout=MUTATION_TIMEOUT_SECONDS,
                name="add_document",
                arguments={"filepath": rel, "content": content, "category": "general"},
            )
        except (TimeoutError, RuntimeError) as exc:
            print(f"  add [{i}/{len(adds)}] {rel} FALHOU: {exc}")
            failed.add(rel)
            continue
        ok = "error" not in r and not _is_error(r)
        print(f"  add [{i}/{len(adds)}] {rel} {'OK' if ok else 'FALHOU: ' + json.dumps(r)[:160]}")
        if ok:
            succeeded.add(rel)
            state[rel] = sha256(path)
            save_state(state)  # checkpoint: permite continuar após reinício
        else:
            failed.add(rel)

    for i, rel in enumerate(updates, 1):
        path = DOCUMENTS_DIR / rel
        content = path.read_text(encoding="utf-8", errors="replace")
        try:
            r = client.call(
                "tools/call",
                timeout=MUTATION_TIMEOUT_SECONDS,
                name="update_document",
                arguments={"filepath": rel, "content": content},
            )
        except (TimeoutError, RuntimeError) as exc:
            print(f"  update [{i}/{len(updates)}] {rel} FALHOU: {exc}")
            failed.add(rel)
            continue
        ok = "error" not in r and not _is_error(r)
        print(f"  update [{i}/{len(updates)}] {rel} {'OK' if ok else 'FALHOU: ' + json.dumps(r)[:160]}")
        if ok:
            succeeded.add(rel)
            state[rel] = sha256(path)
            save_state(state)  # checkpoint
        else:
            failed.add(rel)

    for rel in removes:
        try:
            r = client.call(
                "tools/call",
                timeout=MUTATION_TIMEOUT_SECONDS,
                name="remove_document",
                arguments={"filepath": rel, "delete_file": False},
            )
        except (TimeoutError, RuntimeError) as exc:
            print(f"  remove {rel} FALHOU: {exc}")
            failed.add(rel)
            continue
        ok = "error" not in r and not _is_error(r)
        print(f"  remove {rel} {'OK' if ok else 'FALHOU: ' + json.dumps(r)[:160]}")
        if ok:
            succeeded.add(rel)
        else:
            failed.add(rel)

    # Reindex (BM25/índice) após os docs individuais, e poll do status.
    client.call("tools/call", name="reindex_documents", arguments={})
    deadline = time.time() + 300
    while time.time() < deadline:
        r = client.call("tools/call", name="get_reindex_status", arguments={})
        text = "".join(p.get("text", "") for p in r.get("result", {}).get("content", []))
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {}
        status = (data.get("reindex") or {}).get("active", False)
        if not status:
            print("Reindex completo.")
            break
        time.sleep(3)
    else:
        print("Timeout esperando reindex; use get_reindex_status para acompanhar.")

    # add/update_document normalizes the payload before writing it. Re-scan
    # after the server calls so the checkpoint describes the bytes that are
    # actually on disk; failed items intentionally retain their prior state
    # and will be retried on the next invocation.
    final_current = scan()
    for rel in succeeded:
        if rel in final_current:
            state[rel] = final_current[rel]
    for rel in removes:
        if rel in succeeded:
            state.pop(rel, None)
    save_state(state)
    print(f"Estado salvo: {len(state)} arquivos ({len(failed)} falhas).")
    return 1 if failed else 0


def _is_error(resp: dict) -> bool:
    content = resp.get("result", {}).get("content", [])
    return any("error" in p.get("text", "").lower()[:60] for p in content)


def status() -> int:
    state = load_state()
    print(f"Estado local: {len(state)} arquivos mapeados em {STATE_FILE}")
    client = connect()
    r = client.call("tools/call", name="get_index_stats", arguments={})
    for p in r.get("result", {}).get("content", []):
        try:
            stats = json.loads(p["text"])["stats"]
            print(
                f"Servidor: {stats['total_documents']} docs / {stats['total_chunks']} chunks "
                f"(embedding {stats.get('embedding_model')}, chunk_size {stats.get('chunk_size')})"
            )
        except (KeyError, json.JSONDecodeError):
            print(p.get("text", ""))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["plan", "apply", "status"])
    parser.add_argument(
        "--direct",
        action="store_true",
        help="apply em modo lote (reindex_documents force) — EXPERIMENTAL; "
        "no Windows o reindex em lote pode congelar após ~20 docs; "
        "preferir o modo por arquivo (padrão, com checkpoint)",
    )
    args = parser.parse_args()

    if not DOCUMENTS_DIR.exists():
        print(f"aviso: {DOCUMENTS_DIR} não existe")
    if args.mode == "plan":
        return plan()
    if args.mode == "apply":
        return apply(direct=args.direct)
    return status()


if __name__ == "__main__":
    sys.exit(main())
