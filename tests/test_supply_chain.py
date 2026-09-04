import hashlib
import importlib.metadata
import json
import subprocess
import sys
import venv
from pathlib import Path

_UPSTREAM_COMMIT = "f531148b0d5fe479e7f0a104daf21d8fde7d3189"


def _write_minimal_candidate(root: Path) -> tuple[Path, Path]:
    vendor = root / "skills" / "vendor" / "knowledge-rag" / "mcp_server"
    vendor.mkdir(parents=True)
    (vendor / "__init__.py").write_text('__version__ = "4.8.5"\n', encoding="utf-8")
    (vendor.parent / "PROVENANCE.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "knowledge-rag",
                "version": "4.8.5",
                "license": "MIT",
                "upstream": "https://github.com/lyonzin/knowledge-rag",
                "upstream_ref": "v4.8.5",
                "upstream_commit": _UPSTREAM_COMMIT,
            }
        ),
        encoding="utf-8",
    )
    decision = root / "docs" / "CHROMA-RESIDUAL-DECISION.md"
    decision.parent.mkdir(parents=True)
    decision.write_text("decision gate fixture\n", encoding="utf-8")
    wheel = root / "dist" / "consulta_documentacao-1.1.0-py3-none-any.whl"
    wheel.parent.mkdir()
    wheel.write_bytes(b"candidate wheel bytes")
    return wheel, vendor.parent


def _rewrite_evidence(output: Path, evidence: dict[str, object]) -> None:
    locks = evidence["locks"]
    (output / "locks.json").write_text(json.dumps(locks, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "supply-chain.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = []
    for filename in ("locks.json", "sbom.json", "supply-chain.json"):
        digest = hashlib.sha256((output / filename).read_bytes()).hexdigest()
        lines.append(f"{digest}  {filename}")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_core_supply_chain_allows_only_the_absent_optional_rag_root(tmp_path: Path) -> None:
    root = tmp_path / "candidate"
    wheel, _vendor = _write_minimal_candidate(root)
    (root / "requirements.lock").write_text("knowledge-rag==4.8.5\n", encoding="utf-8")
    isolated = tmp_path / "isolated"
    venv.EnvBuilder(with_pip=True).create(isolated)
    python = isolated / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    output = root / "evidence"

    generated = subprocess.run(
        [
            sys.executable,
            "scripts/generate_supply_chain.py",
            "--root",
            str(root),
            "--wheel",
            str(wheel),
            "--python",
            str(python),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert generated.returncode == 0, generated.stdout + generated.stderr
    evidence = json.loads((output / "supply-chain.json").read_text(encoding="utf-8"))
    resolution = evidence["locks"]["resolution"]
    assert evidence["profile"] == "core"
    assert resolution["profile"] == "core"
    assert resolution["optional_direct"] == ["knowledge-rag"]
    assert resolution["required_direct"] == []
    assert resolution["missing_direct"] == ["knowledge-rag"]
    assert resolution["required_missing_direct"] == []

    verified = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr

    mismatched = json.loads(json.dumps(evidence))
    mismatched["locks"]["resolution"]["status"] = "warning"
    mismatched["locks"]["resolution"]["mismatched_direct"] = [
        {"name": "knowledge-rag", "required": "==4.8.5", "observed": "4.8.4"}
    ]
    mismatched["locks"]["resolver"] = mismatched["locks"]["resolution"]
    _rewrite_evidence(output, mismatched)
    rejected_mismatch = subprocess.run(
        [sys.executable, "scripts/verify_supply_chain.py", "--root", str(root), "--evidence", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected_mismatch.returncode == 1
    assert "direct_resolution_mismatch" in rejected_mismatch.stdout

    tampered_profile = json.loads(json.dumps(evidence))
    tampered_profile["profile"] = "rag"
    _rewrite_evidence(output, tampered_profile)
    rejected_profile = subprocess.run(
        [sys.executable, "scripts/verify_supply_chain.py", "--root", str(root), "--evidence", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected_profile.returncode == 1
    assert "resolution_profile_invalid" in rejected_profile.stdout

    (root / "requirements.lock").write_text("knowledge-rag==4.8.5\nmissing-core-root==1.0\n", encoding="utf-8")
    missing_output = root / "evidence-missing-required"
    generated_missing = subprocess.run(
        [
            sys.executable,
            "scripts/generate_supply_chain.py",
            "--root",
            str(root),
            "--wheel",
            str(wheel),
            "--python",
            str(python),
            "--output",
            str(missing_output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert generated_missing.returncode == 0, generated_missing.stdout + generated_missing.stderr
    rejected_missing = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(missing_output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected_missing.returncode == 1
    assert "direct_resolution_mismatch" in rejected_missing.stdout

    (root / "requirements.lock").write_text("knowledge-rag==4.8.5\n", encoding="utf-8")
    model_cache = root / "model-cache"
    model_cache.mkdir()
    (model_cache / "embedding.onnx").write_bytes(b"model")
    rag_output = root / "evidence-rag"
    generated_rag = subprocess.run(
        [
            sys.executable,
            "scripts/generate_supply_chain.py",
            "--root",
            str(root),
            "--wheel",
            str(wheel),
            "--python",
            str(python),
            "--model-cache",
            str(model_cache),
            "--profile",
            "rag",
            "--require-model",
            "--output",
            str(rag_output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert generated_rag.returncode == 0, generated_rag.stdout + generated_rag.stderr
    rejected_rag = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(rag_output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected_rag.returncode == 1
    assert "direct_resolution_mismatch" in rejected_rag.stdout


def test_supply_chain_cli_emits_verifiable_candidate_evidence(tmp_path: Path) -> None:
    root = tmp_path / "candidate"
    vendor = root / "skills" / "vendor" / "knowledge-rag" / "mcp_server"
    vendor.mkdir(parents=True)
    (vendor / "__init__.py").write_text('__version__ = "4.8.5"\n', encoding="utf-8")
    (vendor.parent / "PROVENANCE.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "knowledge-rag",
                "version": "4.8.5",
                "license": "MIT",
                "upstream": "https://github.com/lyonzin/knowledge-rag",
                "upstream_ref": "v4.8.5",
                "upstream_commit": _UPSTREAM_COMMIT,
            }
        ),
        encoding="utf-8",
    )
    (root / "requirements.lock").write_text(
        f"pip=={importlib.metadata.version('pip')}\n",
        encoding="utf-8",
    )
    decision = root / "docs" / "CHROMA-RESIDUAL-DECISION.md"
    decision.parent.mkdir(parents=True)
    decision.write_text(
        """| Campo | Valor obrigatório | Estado atual |
|---|---|---|
| decisão | `accept`, `mitigate`, `upgrade` ou `remove` | `pending-maintainer-decision` |
| responsável | identidade do mantenedor | não registrado |
| data | ISO-8601 | não registrada |
| versão | versão efetivamente auditada | `chromadb==1.5.9` |
| justificativa | motivo da decisão | não registrada |
| reavaliação | data ou condição objetiva | não registrada |
""",
        encoding="utf-8",
    )
    wheel = root / "dist" / "consulta_documentacao-1.1.0-py3-none-any.whl"
    wheel.parent.mkdir()
    wheel.write_bytes(b"candidate wheel bytes")
    model_cache = root / "models_cache" / "model-snapshot"
    model_cache.mkdir(parents=True)
    (model_cache / "model.onnx").write_bytes(b"model bytes")
    output = root / "evidence"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/generate_supply_chain.py",
            "--root",
            str(root),
            "--wheel",
            str(wheel),
            "--model-cache",
            str(model_cache),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["ok"] is True
    evidence = json.loads((output / "supply-chain.json").read_text(encoding="utf-8"))
    assert evidence["wheel"]["sha256"]
    assert evidence["vendor"]["sha256"]
    assert evidence["models"][0]["sha256"]
    assert evidence["sbom"]["components"]
    assert evidence["vendor"]["upstream_ref"] == "v4.8.5"
    assert evidence["vendor"]["upstream_commit"] == _UPSTREAM_COMMIT
    assert evidence["vendor"]["provenance_sha256"]
    assert evidence["locks"]["resolution"]["method"] == "pip-inspect-lock-closure"
    assert evidence["locks"]["resolution"]["scope"] == "active-interpreter-lock-closure"
    assert evidence["locks"]["resolution"]["missing_direct"] == []
    assert evidence["locks"]["resolution"]["mismatched_direct"] == []
    assert len(evidence["locks"]["resolution"]["component_digest"]) == 64
    assert set(evidence["vulnerability_policy"]["residual_cves"]) == {
        "CVE-2026-45829",
        "CVE-2026-45830",
        "CVE-2026-45831",
        "CVE-2026-45833",
    }
    assert (output / "sbom.json").is_file()
    assert (output / "SHA256SUMS").is_file()

    verified = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stderr

    pending = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(output),
            "--require-human-decision",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert pending.returncode == 1
    assert "human_decision_pending" in pending.stdout
    decision.write_text("| decisão | opção | accept |\n", encoding="utf-8")
    incomplete_decision = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(output),
            "--require-human-decision",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert incomplete_decision.returncode == 1
    assert "human_decision_incomplete" in incomplete_decision.stdout

    decision.write_text(
        """| Campo | Valor obrigatório | Estado atual |
|---|---|---|
| decisão | opção | accept |
| responsável | identidade | Ada Maintainer |
| data | ISO-8601 | 2026-09-04 |
| versão | auditada | chromadb==1.5.9 |
| justificativa | motivo | uso local sem transporte de rede |
| reavaliação | prazo | 2026-12-01 |
""",
        encoding="utf-8",
    )
    completed_decision = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(output),
            "--require-human-decision",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed_decision.returncode == 0, completed_decision.stderr

    provenance_path = root / "skills" / "vendor" / "knowledge-rag" / "PROVENANCE.json"
    provenance_path.write_text(
        provenance_path.read_text(encoding="utf-8").replace(_UPSTREAM_COMMIT, "0" * 40), encoding="utf-8"
    )
    tampered_provenance = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert tampered_provenance.returncode == 1
    assert "vendor" in tampered_provenance.stdout.casefold()

    wheel.write_bytes(b"tampered wheel bytes")
    tampered = subprocess.run(
        [
            sys.executable,
            "scripts/verify_supply_chain.py",
            "--root",
            str(root),
            "--evidence",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert tampered.returncode == 1
    assert "digest" in tampered.stdout.casefold()
