import json
import subprocess
import sys
from pathlib import Path


def test_candidate_bundle_has_new_identity_and_reproducible_release_assets(tmp_path: Path) -> None:
    output = tmp_path / "candidate"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_candidate.py",
            "--root",
            ".",
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
    assert report["version"] != "1.0.0"
    manifest = json.loads((output / "candidate-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == report["version"]
    assert manifest["source_commit"]
    assert manifest["source_candidate_digest"]
    assert manifest["candidate_audit"]["ok"] is True
    assert any(path.endswith(".whl") for path in manifest["assets"])
    assert "evidence/sbom.json" in manifest["assets"]
    assert "README.md" in manifest["assets"]
    assert "community/CODE_OF_CONDUCT.md" in manifest["assets"]
    assert (output / "SHA256SUMS").is_file()

    verified = subprocess.run(
        [sys.executable, "scripts/verify_candidate.py", "--root", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stdout

    wheel = output / Path(manifest["wheel"]["path"])
    wheel.write_bytes(b"tampered candidate wheel")
    tampered = subprocess.run(
        [sys.executable, "scripts/verify_candidate.py", "--root", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert tampered.returncode == 1
    assert "digest" in tampered.stdout.casefold()
