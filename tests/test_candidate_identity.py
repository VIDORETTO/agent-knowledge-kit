from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _prepare_candidate(tmp_path: Path) -> tuple[Path, dict[str, object]]:
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
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(completed.stdout)
    assert report["ok"] is True
    manifest = json.loads((output / "candidate-manifest.json").read_text(encoding="utf-8"))
    return output, manifest


def test_release_candidate_identity_is_structured_and_fail_closed_without_ci_evidence(tmp_path: Path) -> None:
    output, manifest = _prepare_candidate(tmp_path)

    assert isinstance(manifest.get("identity"), dict)
    identity = manifest["identity"]
    assert identity["source_commit"] == manifest["source_commit"]
    assert identity["candidate_digest"] == manifest["source_candidate_digest"]
    assert identity["files"] == manifest["source_files"]

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_candidate.py",
            "--root",
            str(output),
            "--source-root",
            ".",
            "--release",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert any(
        error["code"] in {"release_identity_unverified", "ci_evidence_missing", "supply_chain_failed"}
        for error in payload["errors"]
    )


def test_release_verification_requires_an_independent_source_root(tmp_path: Path) -> None:
    output, _manifest = _prepare_candidate(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_candidate.py",
            "--root",
            str(output),
            "--release",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert any(error["code"] == "source_root_required" for error in payload["errors"])


def test_candidate_falls_back_when_bootstrap_no_install_leaves_a_venv_without_pip(tmp_path: Path) -> None:
    clone = tmp_path / "clean-clone"
    shutil.copytree(
        Path("."),
        clone,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".venv-*",
            ".pytest_cache",
            ".ruff_cache",
            "*.egg-info",
            "artifacts",
            "build",
            "data",
            "dist",
            "models_cache",
        ),
    )
    bootstrapped = subprocess.run(
        [sys.executable, "scripts/bootstrap.py", "--root", str(clone), "--no-install"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert bootstrapped.returncode == 0, bootstrapped.stdout + bootstrapped.stderr

    environment = dict(os.environ)
    for name in ("GITHUB_SHA", "GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_WORKFLOW"):
        environment.pop(name, None)
    output = tmp_path / "candidate"
    prepared = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_candidate.py",
            "--root",
            str(clone),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    assert json.loads(prepared.stdout)["ok"] is True


def test_candidate_verification_rejects_source_mutation_after_digest(tmp_path: Path) -> None:
    output, _manifest = _prepare_candidate(tmp_path)
    source = Path("README.md")
    original = source.read_bytes()
    try:
        source.write_bytes(original + b"\npost-audit mutation\n")
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/verify_candidate.py",
                "--root",
                str(output),
                "--source-root",
                ".",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        source.write_bytes(original)

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert any(error["code"] == "source_digest_mismatch" for error in payload["errors"])
