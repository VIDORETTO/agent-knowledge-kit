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
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = PROJECT_ROOT / "golden-set" / "test-cases.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops import __version__  # noqa: E402
from docops.observability import redact_diagnostic  # noqa: E402
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
            diagnostic = json.dumps(redact_diagnostic(line), ensure_ascii=False, sort_keys=True)
            sys.stderr.write(f"  [server] {diagnostic}\n")


def _public_evaluation(evaluated: dict[str, Any], *, case_count: int) -> dict[str, Any]:
    metrics = evaluated.get("metrics")
    if not isinstance(metrics, dict):
        metrics = evaluated
    recall = metrics.get("recall_at_5") if isinstance(metrics, dict) else None
    mrr = metrics.get("mrr_at_5") if isinstance(metrics, dict) else None
    return {
        "schema_version": 1,
        "ok": isinstance(recall, (int, float)) and isinstance(mrr, (int, float)),
        "case_count": case_count,
        "metrics": {"mrr_at_5": mrr, "recall_at_5": recall},
    }


def _prepare_cases(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Normalize expected paths and reject an unavailable/private corpus."""

    missing: list[str] = []
    invalid: list[str] = []
    prepared: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            invalid.append("<non-object-case>")
            continue
        exp = case.get("expected_filepath")
        if not isinstance(exp, str) or not exp.strip():
            invalid.append("<missing-expected-file>")
            continue
        candidate = Path(exp).expanduser()
        path = candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()
        try:
            path.relative_to(PROJECT_ROOT)
        except ValueError:
            invalid.append(exp)
            continue
        if not path.is_file():
            missing.append(path.relative_to(PROJECT_ROOT).as_posix())
            continue
        normalized = dict(case)
        normalized["expected_filepath"] = str(path)
        prepared.append(normalized)
    return prepared, missing, invalid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--min-recall", type=float, default=0.85)
    parser.add_argument("--min-mrr", type=float, default=0.7)
    args = parser.parse_args()

    payload = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("reviewed") is not True:
        sys.exit("golden set deve ser um envelope schema_version=1 com reviewed=true")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        sys.exit("golden set vazio ou inválido")

    # O servidor compara expected_filepath com o campo `source` literal (path
    # absoluto). Normaliza caminhos relativos e prova que o corpus privado
    # existe antes de iniciar o servidor; um corpus ausente não pode parecer
    # uma avaliação verde com Recall/MRR iguais a zero.
    prepared_cases, missing, invalid = _prepare_cases(cases)
    if invalid:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "ok": False,
                    "code": "golden_paths_invalid",
                    "invalid_count": len(invalid),
                },
                ensure_ascii=False,
            )
        )
        return 2
    if missing:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "ok": False,
                    "code": "corpus_missing",
                    "missing_count": len(missing),
                    "message": "the private corpus required by this golden set is unavailable",
                },
                ensure_ascii=False,
            )
        )
        return 2
    cases = prepared_cases
    for case in cases:
        if not isinstance(case, dict):
            sys.exit("golden set contém um caso inválido")
        if case.get("reviewed") is not True:
            sys.exit("todos os casos do golden set precisam de reviewed=true")
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
            env=env,
            cwd=str(PROJECT_ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        threading.Thread(target=drain, args=(proc,), daemon=True).start()
        client = McpClient(proc)
        init = client.call(
            "initialize",
            protocolVersion="2024-11-05",
            capabilities={},
            clientInfo={"name": "evaluate_golden", "version": __version__},
        )
        if init.get("error"):
            sys.exit(f"initialize falhou: {init['error']}")
        client.send_json({"jsonrpc": "2.0", "method": "notifications/initialized"})

        resp = client.call("tools/call", name="evaluate_retrieval", arguments={"test_cases": json.dumps(cases)})
        evaluated: dict[str, Any] | None = None
        for part in resp.get("result", {}).get("content", []):
            text = part.get("text", "")
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and (
                "metrics" in payload or "recall_at_5" in payload or "mrr_at_5" in payload
            ):
                evaluated = payload
        if resp.get("error") or evaluated is None:
            print(json.dumps({"schema_version": 1, "ok": False, "code": "evaluation_failed"}, ensure_ascii=False))
            return 1
        public_report = _public_evaluation(evaluated, case_count=len(cases))
        recall = public_report["metrics"]["recall_at_5"]
        mrr = public_report["metrics"]["mrr_at_5"]
        if (
            not isinstance(recall, (int, float))
            or not isinstance(mrr, (int, float))
            or recall < args.min_recall
            or mrr < args.min_mrr
        ):
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "ok": False,
                        "code": "quality_threshold_failed",
                        "metrics": {"recall_at_5": recall, "mrr_at_5": mrr},
                        "thresholds": {"recall_at_5": args.min_recall, "mrr_at_5": args.min_mrr},
                    },
                    ensure_ascii=False,
                )
            )
            return 1
        print(json.dumps(public_report, indent=2, ensure_ascii=False, sort_keys=True))
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
