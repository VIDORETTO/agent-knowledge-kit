"""Independently verify candidate supply-chain evidence and digests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

EXPECTED_CVES = {
    "CVE-2026-45829",
    "CVE-2026-45830",
    "CVE-2026-45831",
    "CVE-2026-45833",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _published_path(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return (
        not any(
            part in {".git", ".pytest_cache", ".ruff_cache", "__pycache__", ".mypy_cache"} or part.endswith(".egg-info")
            for part in relative.parts
        )
        and path.suffix != ".pyc"
    )


def _tree_evidence(root: Path) -> tuple[str, list[dict[str, str]]]:
    digest = hashlib.sha256()
    files: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.is_symlink() or not path.is_file() or not _published_path(path, root):
            continue
        relative = path.relative_to(root).as_posix()
        file_hash = _sha256_file(path)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
        files.append({"path": relative, "sha256": file_hash})
    return digest.hexdigest(), files


def _tree_digest(root: Path) -> str:
    return _tree_evidence(root)[0]


def _manifest_tree_digest(files: object) -> tuple[str | None, int]:
    if not isinstance(files, list):
        return None, 0
    digest = hashlib.sha256()
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            return None, 0
        relative = item.get("path")
        file_hash = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(file_hash, str) or not _SHA256.fullmatch(file_hash):
            return None, 0
        path = Path(relative)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or relative in seen:
            return None, 0
        seen.add(relative)
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    if [item.get("path") for item in files] != sorted(seen):
        return None, 0
    return digest.hexdigest(), len(files)


def _requirements_digest(path: Path) -> str:
    canonical_lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            canonical_lines.append(line)
    return hashlib.sha256(("\n".join(canonical_lines) + "\n").encode("utf-8")).hexdigest()


def _requirement_names(locks: dict[str, Any]) -> list[str]:
    requirements = locks.get("requirements")
    if not isinstance(requirements, list):
        return []
    names: list[str] = []
    for item in requirements:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            return []
        names.append(re.sub(r"[-_.]+", "-", item["name"]).casefold())
    return names


def _safe_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    candidate = (root / Path(value)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _normalized_field(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value).casefold()
        if not unicodedata.combining(character)
    ).strip()


def _decision_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        key = _normalized_field(cells[0])
        if key in {"decisao", "responsavel", "data", "versao", "justificativa", "reavaliacao"}:
            fields[key] = cells[-1].strip().strip("`")
    return fields


def _human_decision_error(text: str) -> str | None:
    fields = _decision_fields(text)
    decision = _normalized_field(fields.get("decisao", ""))
    if decision not in {"accept", "mitigate", "upgrade", "remove"}:
        return "human_decision_pending"
    placeholders = {"", "nao registrado", "nao registrada", "pending-maintainer-decision"}
    for field in ("responsavel", "data", "versao", "justificativa", "reavaliacao"):
        if _normalized_field(fields.get(field, "")) in placeholders:
            return "human_decision_incomplete"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields["data"]):
        return "human_decision_incomplete"
    if "chromadb==1.5.9" not in fields["versao"].casefold():
        return "human_decision_incomplete"
    return None


def verify(
    *,
    root: Path,
    evidence_dir: Path,
    wheel_override: Path | None = None,
    require_human_decision: bool = False,
) -> dict[str, Any]:
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

    candidate = evidence.get("candidate")
    if candidate is not None:
        if not isinstance(candidate, dict):
            errors.append({"code": "candidate_identity_invalid", "message": "candidate identity evidence is invalid"})
        elif candidate.get("bound") is True:
            if not isinstance(candidate.get("source_commit"), str) or not candidate.get("source_commit"):
                errors.append(
                    {"code": "candidate_commit_missing", "message": "bound candidate evidence has no source commit"}
                )
            if not isinstance(candidate.get("source_candidate_digest"), str) or not _SHA256.fullmatch(
                candidate.get("source_candidate_digest", "")
            ):
                errors.append(
                    {"code": "candidate_digest_invalid", "message": "bound candidate evidence has no SHA-256 digest"}
                )
            manifest_path = root / "candidate-manifest.json"
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    manifest = None
                if isinstance(manifest, dict) and (
                    manifest.get("source_commit") != candidate.get("source_commit")
                    or manifest.get("source_candidate_digest") != candidate.get("source_candidate_digest")
                ):
                    errors.append(
                        {
                            "code": "candidate_identity_mismatch",
                            "message": "supply-chain candidate identity differs from manifest",
                        }
                    )

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
        resolution = locks.get("resolution") if isinstance(locks, dict) else None
        if not isinstance(resolution, dict) or resolution.get("method") != "pip-inspect-lock-closure":
            errors.append(
                {
                    "code": "transitive_resolution_missing",
                    "message": "effective transitive resolution evidence is missing",
                }
            )
        else:
            components = resolution.get("components")
            profile = evidence.get("profile")
            direct_names = _requirement_names(locks)
            expected_optional = [name for name in direct_names if profile == "core" and name == "knowledge-rag"]
            expected_required = [name for name in direct_names if name not in expected_optional]
            missing_direct = resolution.get("missing_direct")
            mismatched_direct = resolution.get("mismatched_direct")
            required_missing = resolution.get("required_missing_direct")
            required_mismatched = resolution.get("required_mismatched_direct")
            if (
                profile not in {"core", "rag"}
                or resolution.get("profile") != profile
                or resolution.get("direct_requirements") != direct_names
                or resolution.get("optional_direct") != expected_optional
                or resolution.get("required_direct") != expected_required
            ):
                errors.append(
                    {
                        "code": "resolution_profile_invalid",
                        "message": "the effective resolution profile does not match the lock and candidate",
                    }
                )
            if (
                not isinstance(components, list)
                or resolution.get("component_digest")
                != hashlib.sha256(_canonical_json(components).encode("utf-8")).hexdigest()
            ):
                errors.append(
                    {"code": "transitive_resolution_mismatch", "message": "effective resolution digest is invalid"}
                )
            if resolution.get("status") not in {"available", "warning"}:
                errors.append(
                    {"code": "transitive_resolution_unavailable", "message": "effective resolution was not observed"}
                )
            expected_required_missing = (
                sorted(name for name in missing_direct if name in expected_required)
                if isinstance(missing_direct, list) and all(isinstance(name, str) for name in missing_direct)
                else None
            )
            expected_required_mismatched = (
                sorted(
                    (
                        item
                        for item in mismatched_direct
                        if isinstance(item, dict) and item.get("name") in expected_required
                    ),
                    key=lambda item: str(item.get("name")),
                )
                if isinstance(mismatched_direct, list)
                else None
            )
            unexpected_missing = (
                [name for name in missing_direct if name not in expected_optional]
                if isinstance(missing_direct, list)
                else ["invalid"]
            )
            if (
                required_missing != expected_required_missing
                or required_mismatched != expected_required_mismatched
                or unexpected_missing
                or mismatched_direct
                or required_missing
                or required_mismatched
            ):
                errors.append(
                    {
                        "code": "direct_resolution_mismatch",
                        "message": "the audited interpreter does not match every direct requirement for its profile",
                    }
                )
            if not isinstance(resolution.get("limitation"), str) or not resolution["limitation"].strip():
                errors.append(
                    {
                        "code": "transitive_resolution_limit_missing",
                        "message": "resolution portability limit is not explicit",
                    }
                )
            if (
                resolution.get("scope") != "active-interpreter-lock-closure"
                or resolution.get("reproducible") is not False
            ):
                errors.append(
                    {
                        "code": "transitive_resolution_claim_invalid",
                        "message": "effective resolution must state its interpreter-bound limitation",
                    }
                )
            if resolution.get("package_count") != len(components):
                errors.append(
                    {
                        "code": "transitive_resolution_count_mismatch",
                        "message": "effective resolution count is invalid",
                    }
                )
            if locks.get("resolver") != resolution:
                errors.append(
                    {
                        "code": "transitive_resolution_copy_mismatch",
                        "message": "resolver and resolution evidence differ",
                    }
                )
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
    if isinstance(vendor, dict) and vendor_path is not None and vendor_path.is_dir():
        _vendor_digest, vendor_files = _tree_evidence(vendor_path)
        if vendor.get("files") != vendor_files or vendor.get("file_count") != len(vendor_files):
            errors.append(
                {
                    "code": "vendor_content_manifest_mismatch",
                    "message": "vendor file list/count does not match the reviewed tree",
                }
            )
        if vendor.get("reviewed_file_count") != len(vendor_files):
            errors.append(
                {
                    "code": "vendor_review_count_mismatch",
                    "message": "vendor reviewed file count does not match the reviewed tree",
                }
            )
    if isinstance(vendor, dict):
        provenance_path = _safe_path(root, vendor.get("provenance_path"))
        upstream_commit = vendor.get("upstream_commit")
        if (
            provenance_path is None
            or provenance_path.parent != vendor_path
            or provenance_path.name != "PROVENANCE.json"
        ):
            errors.append(
                {"code": "vendor_provenance_missing", "message": "vendor provenance path is missing or unsafe"}
            )
        elif not provenance_path.is_file() or provenance_path.is_symlink():
            errors.append({"code": "vendor_provenance_missing", "message": "vendor PROVENANCE.json is missing"})
        elif _sha256_file(provenance_path) != vendor.get("provenance_sha256"):
            errors.append(
                {"code": "vendor_provenance_digest_mismatch", "message": "vendor provenance digest does not match"}
            )
        if not isinstance(vendor.get("upstream_ref"), str) or not vendor["upstream_ref"].strip():
            errors.append({"code": "vendor_ref_missing", "message": "vendor provenance has no immutable ref"})
        if not isinstance(upstream_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", upstream_commit):
            errors.append({"code": "vendor_commit_missing", "message": "vendor provenance has no immutable commit"})
        if not isinstance(vendor.get("license"), str) or not vendor["license"].strip():
            errors.append({"code": "vendor_license_missing", "message": "vendor license provenance is missing"})

    models = evidence.get("models")
    if not isinstance(models, list) or not models:
        errors.append({"code": "model_provenance_missing", "message": "model provenance is missing"})
    else:
        if evidence.get("profile") == "rag" and not any(
            isinstance(model, dict) and model.get("status") == "verified-external-snapshot" for model in models
        ):
            errors.append(
                {
                    "code": "rag_model_provenance_missing",
                    "message": "the RAG profile requires a verified model snapshot",
                }
            )
        for model in models:
            if not isinstance(model, dict) or model.get("status") == "not-bundled":
                continue
            if (
                model.get("status") != "verified-external-snapshot"
                or model.get("included") is not False
                or model.get("path") is not None
                or model.get("digest_algorithm") != "sha256-path-content-v1"
            ):
                errors.append({"code": "model_provenance_invalid", "message": "model provenance is unsafe or invalid"})
                continue
            manifest_digest, file_count = _manifest_tree_digest(model.get("files"))
            if (
                manifest_digest is None
                or manifest_digest != model.get("sha256")
                or model.get("file_count") != file_count
                or file_count < 1
            ):
                errors.append(
                    {
                        "code": "model_content_manifest_mismatch",
                        "message": "external model snapshot manifest/count/digest does not match evidence",
                    }
                )

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
    human_decision = policy.get("human_decision") if isinstance(policy, dict) else None
    if not isinstance(human_decision, dict) or human_decision.get("status") != "required-before-release":
        errors.append(
            {
                "code": "human_decision_policy_missing",
                "message": "Chroma residual requires an explicit pre-release decision",
            }
        )
    else:
        decision_path = _safe_path(root, human_decision.get("artifact"))
        if decision_path is None or not decision_path.is_file():
            errors.append(
                {
                    "code": "human_decision_artifact_missing",
                    "message": "the Chroma decision artifact is missing or unsafe",
                }
            )
        elif require_human_decision:
            try:
                decision_text = decision_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                decision_text = ""
            decision_error = _human_decision_error(decision_text)
            if decision_error:
                errors.append(
                    {
                        "code": decision_error,
                        "message": (
                            "a maintainer must record accept, mitigate, upgrade or remove before release"
                            if decision_error == "human_decision_pending"
                            else "the maintainer decision must include owner, ISO date, audited chromadb version, "
                            "justification and reassessment"
                        ),
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
    parser.add_argument(
        "--require-human-decision",
        action="store_true",
        help="require the maintainer decision artifact to contain a completed decision",
    )
    args = parser.parse_args(argv)
    try:
        result = verify(
            root=args.root,
            evidence_dir=args.evidence,
            wheel_override=args.wheel,
            require_human_decision=args.require_human_decision,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        result = {"schema_version": 1, "ok": False, "errors": [{"code": "verification_failed", "message": str(exc)}]}
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
