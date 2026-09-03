"""Independently verify a local, unpublished DOCOPS candidate bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_supply_chain import verify as verify_supply_chain  # noqa: E402

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.+-]*)?$")
_REQUIRED_ASSETS = {
    "README.md",
    "community/CODE_OF_CONDUCT.md",
    "community/GOVERNANCE.md",
    "community/MAINTAINERS.md",
    "community/SUPPORT.md",
    "evidence/SHA256SUMS",
    "evidence/locks.json",
    "evidence/sbom.json",
    "evidence/supply-chain.json",
    "metadata/repository.json",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(value: Any) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path


def _wheel_version(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
            metadata = archive.read(metadata_name).decode("utf-8")
    except (OSError, UnicodeError, StopIteration, zipfile.BadZipFile):
        return None
    match = re.search(r"^Version:\s*(\S+)\s*$", metadata, re.MULTILINE)
    return match.group(1) if match else None


def _checksum_errors(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    checksum_path = root / "SHA256SUMS"
    try:
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return [{"code": "checksums_missing", "message": "SHA256SUMS is missing or unreadable"}]
    listed: set[str] = set()
    for line in lines:
        expected, separator, filename = line.partition("  ")
        relative = _safe_relative(filename) if separator else None
        if not separator or not _SHA256.fullmatch(expected) or relative is None:
            errors.append({"code": "checksum_invalid", "message": "SHA256SUMS contains an invalid entry"})
            continue
        relative_name = relative.as_posix()
        listed.add(relative_name)
        target = root / relative
        if not target.is_file() or target.is_symlink():
            errors.append(
                {"code": "checksum_target_missing", "message": f"checksum target is missing: {relative_name}"}
            )
        elif _sha256_file(target) != expected:
            errors.append({"code": "digest_mismatch", "message": f"digest mismatch for {relative_name}"})
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and path.relative_to(root).as_posix() != "SHA256SUMS"
    }
    if listed != actual:
        errors.append(
            {"code": "checksum_incomplete", "message": "SHA256SUMS must cover every bundle file except itself"}
        )
    return errors


def verify(root: Path | str) -> dict[str, Any]:
    """Verify every public claim needed before a human may publish a bundle."""

    bundle_root = Path(root).expanduser().resolve()
    errors: list[dict[str, str]] = []
    manifest_path = bundle_root / "candidate-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "schema_version": 1,
            "ok": False,
            "errors": [{"code": "manifest_unreadable", "message": "candidate-manifest.json is unreadable"}],
        }
    if not isinstance(manifest, dict):
        return {
            "schema_version": 1,
            "ok": False,
            "errors": [{"code": "manifest_invalid", "message": "candidate manifest must be an object"}],
        }

    version = manifest.get("version")
    if not isinstance(version, str) or not _VERSION.fullmatch(version) or version == "1.0.0":
        errors.append(
            {"code": "version_invalid", "message": "candidate version must be a valid version different from 1.0.0"}
        )
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or not source_commit:
        errors.append({"code": "source_commit_missing", "message": "candidate source commit is missing"})
    source_digest = manifest.get("source_candidate_digest")
    if not isinstance(source_digest, str) or not _SHA256.fullmatch(source_digest):
        errors.append({"code": "source_digest_invalid", "message": "candidate source digest must be SHA-256"})
    candidate_audit = manifest.get("candidate_audit")
    if not isinstance(candidate_audit, dict) or candidate_audit.get("ok") is not True:
        errors.append({"code": "candidate_audit_failed", "message": "candidate audit is not green"})
    publication = manifest.get("publication")
    if not isinstance(publication, dict) or publication.get("performed") is not False:
        errors.append(
            {
                "code": "publication_not_blocked",
                "message": "candidate metadata must prove that publication was not performed",
            }
        )

    assets_value = manifest.get("assets")
    assets = (
        assets_value if isinstance(assets_value, list) and all(isinstance(item, str) for item in assets_value) else []
    )
    if not assets:
        errors.append({"code": "assets_missing", "message": "candidate assets are missing"})
    safe_assets: set[str] = set()
    for value in assets:
        relative = _safe_relative(value)
        if relative is None:
            errors.append({"code": "asset_path_invalid", "message": "candidate asset path is unsafe"})
            continue
        name = relative.as_posix()
        if name in safe_assets:
            errors.append({"code": "asset_duplicate", "message": f"candidate asset is listed twice: {name}"})
        safe_assets.add(name)
        target = bundle_root / relative
        if not target.is_file() or target.is_symlink():
            errors.append({"code": "asset_missing", "message": f"candidate asset is missing: {name}"})
    missing_assets = sorted(_REQUIRED_ASSETS - safe_assets)
    errors.extend(
        {"code": "asset_required", "message": f"required candidate asset is missing: {name}"} for name in missing_assets
    )

    wheel_value = manifest.get("wheel")
    wheel_name = wheel_value.get("path") if isinstance(wheel_value, dict) else None
    wheel_relative = _safe_relative(wheel_name)
    wheel_path = bundle_root / wheel_relative if wheel_relative is not None else None
    wheel_version = _wheel_version(wheel_path) if wheel_path is not None and wheel_path.is_file() else None
    if wheel_path is None or not wheel_path.is_file() or wheel_path.suffix != ".whl":
        errors.append({"code": "wheel_missing", "message": "candidate wheel is missing or unsafe"})
    elif wheel_version != version:
        errors.append({"code": "wheel_version_mismatch", "message": "wheel metadata does not match candidate version"})
    if isinstance(wheel_value, dict) and wheel_path is not None and wheel_path.is_file():
        if wheel_value.get("sha256") != _sha256_file(wheel_path):
            errors.append(
                {"code": "wheel_digest_mismatch", "message": "candidate wheel digest does not match manifest"}
            )

    evidence_dir = bundle_root / "evidence"
    supply_result = verify_supply_chain(root=bundle_root, evidence_dir=evidence_dir, wheel_override=wheel_path)
    if not supply_result.get("ok"):
        errors.append({"code": "supply_chain_failed", "message": "independent supply-chain verification failed"})
    errors.extend(_checksum_errors(bundle_root))
    return {
        "schema_version": 1,
        "ok": not errors,
        "version": version,
        "source_commit": source_commit,
        "source_candidate_digest": source_digest,
        "supply_chain": supply_result,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.root)
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        result = {"schema_version": 1, "ok": False, "errors": [{"code": "verification_failed", "message": str(exc)}]}
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
