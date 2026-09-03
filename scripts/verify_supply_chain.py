"""Independently verify candidate supply-chain evidence and digests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_CVES = {
    "CVE-2026-45829",
    "CVE-2026-45830",
    "CVE-2026-45831",
    "CVE-2026-45833",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.is_symlink() or not path.is_file():
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _requirements_digest(path: Path) -> str:
    canonical_lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            canonical_lines.append(line)
    return hashlib.sha256(("\n".join(canonical_lines) + "\n").encode("utf-8")).hexdigest()


def _safe_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    candidate = (root / Path(value)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def verify(*, root: Path, evidence_dir: Path, wheel_override: Path | None = None) -> dict[str, Any]:
    root = root.expanduser().resolve()
    evidence_dir = evidence_dir.expanduser().resolve()
    errors: list[dict[str, str]] = []
    evidence_path = evidence_dir / "supply-chain.json"
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "schema_version": 1,
            "ok": False,
            "errors": [{"code": "evidence_unreadable", "message": "supply-chain.json is unreadable"}],
        }
    if not isinstance(evidence, dict):
        return {
            "schema_version": 1,
            "ok": False,
            "errors": [{"code": "evidence_invalid", "message": "supply-chain.json must be an object"}],
        }

    checksums_path = evidence_dir / "SHA256SUMS"
    try:
        checksum_lines = checksums_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        errors.append({"code": "checksums_missing", "message": "SHA256SUMS is missing"})
        checksum_lines = []
    for line in checksum_lines:
        expected, separator, filename = line.partition("  ")
        target = evidence_dir / filename if separator else None
        if not separator or not target or target.parent != evidence_dir or not target.is_file():
            errors.append({"code": "checksum_invalid", "message": "SHA256SUMS contains an invalid entry"})
            continue
        if _sha256_file(target) != expected:
            errors.append({"code": "digest_mismatch", "message": f"digest mismatch for {filename}"})

    locks_path = evidence_dir / "locks.json"
    try:
        locks = json.loads(locks_path.read_text(encoding="utf-8"))
        if locks != evidence.get("locks"):
            errors.append({"code": "lock_evidence_mismatch", "message": "locks.json differs from supply-chain.json"})
        lock_path = _safe_path(root, locks.get("requirements_path") if isinstance(locks, dict) else None)
        if lock_path is None or not lock_path.is_file():
            errors.append({"code": "lock_source_missing", "message": "the lock input in evidence is missing or unsafe"})
        elif _requirements_digest(lock_path) != locks.get("requirements_sha256"):
            errors.append(
                {"code": "lock_digest_mismatch", "message": "the requirements lock digest does not match evidence"}
            )
        for item in locks.get("line_hashes", []) if isinstance(locks, dict) else []:
            if not isinstance(item, dict):
                continue
            line = item.get("line")
            if isinstance(line, str) and item.get("sha256") != hashlib.sha256(line.encode("utf-8")).hexdigest():
                errors.append({"code": "lock_hash_mismatch", "message": "a lock input hash does not match"})
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append({"code": "locks_missing", "message": "locks.json is missing or invalid"})

    wheel = evidence.get("wheel")
    wheel_path = _safe_path(root, wheel.get("path") if isinstance(wheel, dict) else None)
    if wheel_override is not None:
        override = wheel_override.expanduser().resolve()
        try:
            override.relative_to(root)
        except ValueError:
            wheel_path = None
            errors.append(
                {"code": "wheel_path_escape", "message": "the explicit wheel path must stay inside the evidence root"}
            )
        else:
            wheel_path = override
    if wheel_path is None or not wheel_path.is_file():
        errors.append({"code": "wheel_missing", "message": "wheel path in evidence is missing or unsafe"})
    elif _sha256_file(wheel_path) != wheel.get("sha256"):
        errors.append({"code": "digest_mismatch", "message": "wheel digest does not match evidence"})

    vendor = evidence.get("vendor")
    vendor_path = _safe_path(root, vendor.get("path") if isinstance(vendor, dict) else None)
    if vendor_path is None or not vendor_path.is_dir():
        errors.append({"code": "vendor_missing", "message": "vendor path in evidence is missing or unsafe"})
    elif _tree_digest(vendor_path) != vendor.get("sha256"):
        errors.append({"code": "digest_mismatch", "message": "vendor digest does not match evidence"})

    models = evidence.get("models")
    if not isinstance(models, list) or not models:
        errors.append({"code": "model_provenance_missing", "message": "model provenance is missing"})
    else:
        for model in models:
            if not isinstance(model, dict) or model.get("status") != "verified-snapshot":
                continue
            model_path = _safe_path(root, model.get("path"))
            if model_path is None or not model_path.is_dir():
                errors.append({"code": "model_missing", "message": "verified model snapshot is missing or unsafe"})
            elif _tree_digest(model_path) != model.get("sha256"):
                errors.append({"code": "digest_mismatch", "message": "model digest does not match evidence"})

    policy = evidence.get("vulnerability_policy")
    residual = policy.get("residual_cves") if isinstance(policy, dict) else None
    if set(residual or ()) != EXPECTED_CVES:
        errors.append(
            {
                "code": "vulnerability_policy_invalid",
                "message": "the four documented Chroma residual CVEs must remain explicit",
            }
        )
    threat_model = policy.get("threat_model") if isinstance(policy, dict) else None
    expected_threat_model = {
        "chromadb_client": "PersistentClient",
        "chromadb_http_api": False,
        "trust_remote_code": False,
        "remote_model_repositories": False,
    }
    if threat_model != expected_threat_model:
        errors.append(
            {
                "code": "threat_model_invalid",
                "message": "the Chroma exception is limited to the approved local threat model",
            }
        )
    sbom_path = evidence_dir / "sbom.json"
    try:
        sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
        if not isinstance(sbom, dict) or sbom.get("spdxVersion") != "SPDX-2.3":
            raise ValueError
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        errors.append({"code": "sbom_invalid", "message": "sbom.json is missing or is not SPDX-2.3"})
    return {"schema_version": 1, "ok": not errors, "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument(
        "--wheel", type=Path, help="override the wheel path when evidence was generated from an external source"
    )
    args = parser.parse_args(argv)
    try:
        result = verify(root=args.root, evidence_dir=args.evidence, wheel_override=args.wheel)
    except (OSError, UnicodeError, ValueError) as exc:
        result = {"schema_version": 1, "ok": False, "errors": [{"code": "verification_failed", "message": str(exc)}]}
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
