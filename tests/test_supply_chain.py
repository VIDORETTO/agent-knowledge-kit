import json
import subprocess
import sys
from pathlib import Path


def test_supply_chain_cli_emits_verifiable_candidate_evidence(tmp_path: Path) -> None:
    root = tmp_path / "candidate"
    vendor = root / "skills" / "vendor" / "knowledge-rag" / "mcp_server"
    vendor.mkdir(parents=True)
    (vendor / "__init__.py").write_text('__version__ = "4.8.5"\n', encoding="utf-8")
    (root / "requirements.lock").write_text("knowledge-rag==4.8.5\n", encoding="utf-8")
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
