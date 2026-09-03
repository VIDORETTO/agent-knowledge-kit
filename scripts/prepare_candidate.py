"""Build a reproducible, unpublished release-candidate bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops.release_audit import audit_release  # noqa: E402
from scripts.generate_supply_chain import generate as generate_supply_chain  # noqa: E402
from scripts.verify_candidate import verify as verify_candidate  # noqa: E402
from scripts.verify_supply_chain import verify as verify_supply_chain  # noqa: E402

_BUNDLE_FILES = (
    ("README.md", "README.md"),
    ("CHANGELOG.md", "CHANGELOG.md"),
    ("LICENSE", "LICENSE"),
    ("SECURITY.md", "SECURITY.md"),
    ("docs/DEPENDENCIES.md", "docs/DEPENDENCIES.md"),
    ("docs/RELEASE.md", "docs/RELEASE.md"),
    ("docs/SUPPORT-MATRIX.json", "docs/SUPPORT-MATRIX.json"),
    ("docs/REPOSITORY-METADATA.json", "metadata/repository.json"),
    ("community/CODE_OF_CONDUCT.md", "community/CODE_OF_CONDUCT.md"),
    ("community/GOVERNANCE.md", "community/GOVERNANCE.md"),
    ("community/MAINTAINERS.md", "community/MAINTAINERS.md"),
    ("community/SUPPORT.md", "community/SUPPORT.md"),
    (".github/CODEOWNERS", "community/CODEOWNERS"),
    (".github/ISSUE_TEMPLATE/bug_report.yml", "community/issue-templates/bug_report.yml"),
    (".github/ISSUE_TEMPLATE/feature_request.yml", "community/issue-templates/feature_request.yml"),
    (".github/PULL_REQUEST_TEMPLATE.md", "community/PULL_REQUEST_TEMPLATE.md"),
)
_LOCAL_SOURCE_DIRS = {
    ".git",
    ".venv",
    ".venv-rag",
    ".venv-posix",
    ".venv-windows",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".docops",
    "artifacts",
    "build",
    "data",
    "dist",
    "models_cache",
    ".scratch",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode:
        raise RuntimeError("Git could not enumerate the candidate files")
    values = [item for item in completed.stdout.decode("utf-8", errors="replace").split("\0") if item]
    if not values:
        raise RuntimeError("the candidate must contain at least one Git file")
    return sorted(set(values))


def _distributable_files(root: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in _LOCAL_SOURCE_DIRS or part.endswith(".egg-info") for part in relative.parts):
            continue
        files.append(relative.as_posix())
    if not files:
        raise RuntimeError("the clean source tree has no distributable files")
    return files


def _source_files(root: Path) -> tuple[list[str], str]:
    if (root / ".git").exists():
        return _git_files(root), _git_commit(root)
    return _distributable_files(root), "unversioned-clean-clone"


def _git_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    commit = completed.stdout.strip()
    if completed.returncode or not commit:
        raise RuntimeError("the candidate must have a readable Git HEAD")
    return commit


def _assert_output_is_external_or_ignored(root: Path, output: Path) -> None:
    try:
        relative = output.relative_to(root)
    except ValueError:
        return
    if not relative.parts:
        raise RuntimeError("candidate output cannot be the repository root")
    if not (root / ".git").exists():
        raise RuntimeError("candidate output inside a clean clone cannot be checked against Git ignores")
    completed = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--no-index", "--", relative.as_posix()],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("candidate output inside the repository must be ignored")


def _candidate_digest(root: Path, relative_files: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in sorted(relative_files):
        relative = Path(value)
        path = (root / relative).resolve()
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("the candidate contains a missing or symbolic-link file")
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise RuntimeError("a required candidate asset is missing or is a symbolic link")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_candidate_vendor(root: Path, relative_files: Iterable[str], destination: Path) -> None:
    prefix = Path("skills/vendor/knowledge-rag")
    copied = 0
    for value in relative_files:
        relative = Path(value)
        try:
            vendor_relative = relative.relative_to(prefix)
        except ValueError:
            continue
        _copy_file(root / relative, destination / vendor_relative)
        copied += 1
    if not copied:
        raise RuntimeError("the candidate has no reviewed knowledge-rag vendor files")


def _wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
    for line in metadata.splitlines():
        if line.startswith("Version:"):
            return line.partition(":")[2].strip()
    raise RuntimeError("the candidate wheel has no version metadata")


def _build_wheel(root: Path, python: Path, destination: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="docops-candidate-wheel-") as temporary:
        wheel_dir = Path(temporary)
        completed = subprocess.run(
            [str(python), "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheel_dir), str(root)],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        wheels = sorted(wheel_dir.glob("*.whl"))
        if completed.returncode or len(wheels) != 1:
            raise RuntimeError("candidate wheel build failed or produced an unexpected number of wheels")
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheels[0], destination / wheels[0].name)
        return destination / wheels[0].name


def _bundle_files(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and path.relative_to(root).as_posix() != "SHA256SUMS"
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_checksums(root: Path) -> None:
    lines = [f"{_sha256_file(root / relative)}  {relative}" for relative in _bundle_files(root)]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _display_output(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _attestation_status() -> dict[str, Any]:
    cosign = shutil.which("cosign")
    if cosign:
        return {
            "status": "available-human-action",
            "tool": "cosign",
            "automated": False,
            "reason": "signing requires an explicit human key and authorization",
        }
    return {
        "status": "not-configured",
        "tool": None,
        "automated": False,
        "reason": "no signing provider is configured; attach an attestation during the human release step if required",
    }


def build_candidate(
    *,
    root: Path,
    output: Path,
    python: Path,
    model_cache: Path | None = None,
    require_model: bool = False,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    output = output.expanduser().resolve()
    python = python.expanduser().resolve()
    _assert_output_is_external_or_ignored(root, output)
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("candidate output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)

    relative_files, source_commit = _source_files(root)
    source_candidate_digest = _candidate_digest(root, relative_files)
    candidate_audit = audit_release(root, candidate_files=relative_files)
    if not candidate_audit.ok:
        _write_json(output / "candidate-audit.json", candidate_audit.to_dict())
        raise RuntimeError("candidate audit rejected the source tree")

    missing_assets = [source for source, _ in _BUNDLE_FILES if not (root / source).is_file()]
    if missing_assets:
        raise RuntimeError("required repository metadata or community files are missing")
    for source, target in _BUNDLE_FILES:
        _copy_file(root / source, output / target)

    lock_source = root / "requirements.lock"
    lock_destination = output / "provenance" / "requirements.lock"
    _copy_file(lock_source, lock_destination)
    vendor_destination = output / "provenance" / "vendor" / "knowledge-rag"
    _copy_candidate_vendor(root, relative_files, vendor_destination)

    model_destination: Path | None = None
    if model_cache is not None:
        model_source = model_cache.expanduser().resolve()
        if not model_source.is_dir() or model_source.is_symlink():
            raise RuntimeError("the requested model cache is missing or is a symbolic link")
        for path in model_source.rglob("*"):
            if path.is_symlink():
                raise RuntimeError("model snapshots containing symbolic links are not reproducible")
        model_destination = output / "provenance" / "model-cache"
        shutil.copytree(model_source, model_destination)

    wheel_destination = output / "wheel"
    wheel = _build_wheel(root, python, wheel_destination)
    version = _wheel_version(wheel)
    if version == "1.0.0":
        raise RuntimeError("candidate version must be different from the published 1.0.0")

    evidence = generate_supply_chain(
        root=output,
        wheel=wheel,
        output=output / "evidence",
        model_cache=model_destination,
        python=python,
        require_model=require_model,
        lock_path=lock_destination,
        vendor_root=vendor_destination,
    )
    if not evidence.get("ok"):
        raise RuntimeError("candidate supply-chain evidence contains errors")
    supply_verification = verify_supply_chain(root=output, evidence_dir=output / "evidence", wheel_override=wheel)
    if not supply_verification.get("ok"):
        raise RuntimeError("candidate supply-chain evidence failed independent verification")

    _write_json(
        output / "candidate-audit.json",
        {
            **candidate_audit.to_dict(),
            "source_commit": source_commit,
            "source_candidate_digest": source_candidate_digest,
        },
    )
    assets = [relative for relative in _bundle_files(output) if relative != "candidate-manifest.json"]
    manifest = {
        "schema_version": 1,
        "kind": "docops-release-candidate",
        "status": "candidate",
        "version": version,
        "source_commit": source_commit,
        "source_state": (
            "working-tree-candidate; digest covers the exact Git candidate file set"
            if source_commit != "unversioned-clean-clone"
            else "unversioned clean-clone snapshot; digest covers the distributable file set"
        ),
        "source_candidate_digest": source_candidate_digest,
        "source_files": relative_files,
        "candidate_audit": candidate_audit.to_dict(),
        "wheel": {
            "path": _display_output(wheel, output),
            "sha256": _sha256_file(wheel),
            "version": version,
        },
        "evidence": {
            "path": "evidence/supply-chain.json",
            "sha256": _sha256_file(output / "evidence" / "supply-chain.json"),
            "supply_chain_verified": True,
        },
        "gates": {
            "candidate_audit": {"ok": True, "candidate_digest": source_candidate_digest},
            "supply_chain": {"ok": True, "candidate_digest": source_candidate_digest},
            "wheel": {"ok": True, "version": version},
        },
        "assets": assets,
        "attestation": _attestation_status(),
        "repository": {
            "metadata": "metadata/repository.json",
            "ownership": "community/MAINTAINERS.md",
            "protections": "human-review-required",
        },
        "publication": {
            "performed": False,
            "automated": False,
            "human_authorization_required": True,
            "actions": [],
        },
    }
    _write_json(output / "candidate-manifest.json", manifest)
    _write_checksums(output)
    verification = verify_candidate(output)
    if not verification.get("ok"):
        raise RuntimeError("candidate bundle failed independent verification")
    return {
        "schema_version": 1,
        "ok": True,
        "version": version,
        "source_commit": source_commit,
        "source_candidate_digest": source_candidate_digest,
        "candidate_audit": candidate_audit.to_dict(),
        "bundle_verification": verification,
        "output": _display_output(output, root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, help="interpreter used for wheel and resolver evidence")
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument("--require-model", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_candidate(
            root=args.root,
            output=args.output,
            python=args.python or Path(sys.executable),
            model_cache=args.model_cache,
            require_model=args.require_model,
        )
    except (OSError, UnicodeError, ValueError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(
            json.dumps(
                {"schema_version": 1, "ok": False, "errors": [{"code": "candidate_failed", "message": str(exc)}]},
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
