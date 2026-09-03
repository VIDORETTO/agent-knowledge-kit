"""Generate deterministic supply-chain evidence for a release candidate.

The command is deliberately offline: it hashes the candidate wheel, the
reviewed vendor tree, selected model snapshots and lock inputs, then emits a
small SPDX document plus checksums.  It does not publish or modify a package
registry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

CHROMA_RESIDUAL_CVES = frozenset(
    {
        "CVE-2026-45829",
        "CVE-2026-45830",
        "CVE-2026-45831",
        "CVE-2026-45833",
    }
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _tree_digest(root: Path) -> tuple[str, int, list[dict[str, str]]]:
    digest = hashlib.sha256()
    files: list[dict[str, str]] = []
    if not root.is_dir() or root.is_symlink():
        return _sha256_bytes(b"missing-tree"), 0, files
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        file_hash = _sha256_file(path)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
        files.append({"path": relative, "sha256": file_hash})
    return digest.hexdigest(), len(files), files


def _locked_requirements(path: Path) -> tuple[list[dict[str, str]], str, list[dict[str, str]]]:
    requirements: list[dict[str, str]] = []
    canonical_lines: list[str] = []
    line_hashes: list[dict[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        canonical_lines.append(line)
        line_hashes.append({"line": line, "sha256": _sha256_bytes(line.encode("utf-8"))})
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*([=!<>~].*)?$", line)
        if match:
            requirements.append({"name": match.group(1).lower(), "specifier": (match.group(2) or "").strip()})
        else:
            requirements.append({"name": line, "specifier": ""})
    return requirements, _sha256_bytes(("\n".join(canonical_lines) + "\n").encode("utf-8")), line_hashes


def _pip_inspect(python: Path, root: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(python), "-m", "pip", "inspect", "--local"],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "unavailable", "reason": str(exc).replace(str(root), "<candidate-root>")}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "unavailable", "reason": "pip inspect did not return JSON"}
    installed = payload.get("installed") if isinstance(payload, dict) else None
    if not isinstance(installed, list):
        return {"status": "unavailable", "reason": "pip inspect returned an unexpected shape"}
    components = []
    for item in installed:
        if not isinstance(item, dict) or not isinstance(item.get("metadata"), dict):
            continue
        metadata = item["metadata"]
        name = metadata.get("name")
        version = metadata.get("version")
        if isinstance(name, str) and isinstance(version, str):
            components.append({"name": name.casefold(), "version": version, "requested": bool(item.get("requested"))})
    components.sort(key=lambda item: (item["name"], item["version"]))
    return {
        "status": "available" if completed.returncode == 0 else "warning",
        "package_count": len(components),
        "components": components,
    }


def _wheel_evidence(wheel: Path, root: Path) -> dict[str, Any]:
    version = None
    match = re.search(r"-(\d+\.\d+\.\d+(?:[A-Za-z0-9.+]*)?)-py[^-]+-[^-]+-[^-]+\.whl$", wheel.name)
    if match:
        version = match.group(1)
    return {
        "path": _display_path(wheel, root),
        "filename": wheel.name,
        "version": version,
        "sha256": _sha256_file(wheel),
    }


def _model_evidence(model_cache: Path | None, root: Path) -> list[dict[str, Any]]:
    if model_cache is None or not model_cache.is_dir():
        return [
            {
                "role": "embedding",
                "status": "not-bundled",
                "origin": "runtime-selected external model cache",
                "path": None,
                "sha256": None,
                "files": [],
            }
        ]
    tree_hash, file_count, files = _tree_digest(model_cache)
    return [
        {
            "role": "embedding",
            "status": "verified-snapshot",
            "origin": "runtime-selected external model cache",
            "path": _display_path(model_cache, root),
            "sha256": tree_hash,
            "file_count": file_count,
            "files": files,
        }
    ]


def _spdx_components(
    requirements: Iterable[dict[str, str]],
    environment: dict[str, Any],
) -> list[dict[str, Any]]:
    components: dict[tuple[str, str], dict[str, Any]] = {}
    for item in requirements:
        name = item["name"]
        specifier = item["specifier"]
        version = specifier.lstrip("=<>!~ ") or "unresolved"
        key = (name, version)
        components[key] = {
            "name": name,
            "version": version,
            "type": "library",
            "purl": f"pkg:pypi/{name}@{version}" if version != "unresolved" else f"pkg:pypi/{name}",
        }
    for item in environment.get("components", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        version = item.get("version")
        if isinstance(name, str) and isinstance(version, str):
            components.setdefault(
                (name, version),
                {"name": name, "version": version, "type": "library", "purl": f"pkg:pypi/{name}@{version}"},
            )
    return [components[key] for key in sorted(components)]


def generate(
    *,
    root: Path,
    wheel: Path,
    output: Path,
    model_cache: Path | None = None,
    python: Path | None = None,
    require_model: bool = False,
    lock_path: Path | None = None,
    vendor_root: Path | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    wheel = wheel.expanduser().resolve()
    output = output.expanduser().resolve()
    lock_path = (lock_path or root / "requirements.lock").expanduser().resolve()
    vendor_root = (vendor_root or root / "skills" / "vendor" / "knowledge-rag").expanduser().resolve()
    errors: list[dict[str, str]] = []
    if not wheel.is_file():
        errors.append({"code": "wheel_missing", "message": "candidate wheel does not exist"})
    if not lock_path.is_file():
        errors.append({"code": "lock_missing", "message": "requirements.lock does not exist"})
    if not vendor_root.is_dir():
        errors.append({"code": "vendor_missing", "message": "reviewed knowledge-rag vendor tree does not exist"})

    requirements: list[dict[str, str]] = []
    lock_hash = None
    line_hashes: list[dict[str, str]] = []
    if lock_path.is_file():
        requirements, lock_hash, line_hashes = _locked_requirements(lock_path)
    vendor_hash, vendor_file_count, vendor_files = _tree_digest(vendor_root)
    vendor_version = "4.8.5"
    vendor_init = vendor_root / "mcp_server" / "__init__.py"
    if vendor_init.is_file():
        match = re.search(r"__version__\s*=\s*[\"']([^\"']+)", vendor_init.read_text(encoding="utf-8"))
        if match:
            vendor_version = match.group(1)
    models = _model_evidence(model_cache, root)
    if require_model and not any(item.get("status") == "verified-snapshot" for item in models):
        errors.append(
            {"code": "model_missing", "message": "the requested RAG candidate has no verified model snapshot"}
        )
    interpreter = (python or Path(sys.executable)).expanduser().resolve()
    environment = _pip_inspect(interpreter, root)
    wheel_evidence = (
        _wheel_evidence(wheel, root) if wheel.is_file() else {"path": _display_path(wheel, root), "sha256": None}
    )
    components = _spdx_components(requirements, environment)
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": wheel_evidence.get("filename", "candidate"),
        "dataLicense": "CC0-1.0",
        "documentNamespace": "https://example.invalid/docops/supply-chain",
        "creationInfo": {"createdBy": ["Tool: docops supply-chain evidence"]},
        "packages": [
            {
                "SPDXID": f"SPDXRef-Package-{index}",
                "name": item["name"],
                "versionInfo": item["version"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "externalRefs": [{"referenceType": "purl", "referenceLocator": item["purl"]}],
            }
            for index, item in enumerate(components, 1)
        ],
    }
    evidence = {
        "schema_version": 1,
        "kind": "docops-supply-chain-evidence",
        "wheel": wheel_evidence,
        "locks": {
            "requirements_path": _display_path(lock_path, root),
            "requirements_sha256": lock_hash,
            "requirements": requirements,
            "line_hashes": line_hashes,
            "resolver": environment,
        },
        "vendor": {
            "name": "knowledge-rag",
            "version": vendor_version,
            "origin": "reviewed vendored copy; upstream provenance must be reviewed before refresh",
            "upstream": "https://github.com/lyonzin/knowledge-rag",
            "path": _display_path(vendor_root, root),
            "sha256": vendor_hash,
            "file_count": vendor_file_count,
            "files": vendor_files,
        },
        "models": models,
        "sbom": {"path": "sbom.json", "format": "SPDX-2.3", "components": components},
        "vulnerability_policy": {
            "status": "residual-risk",
            "allowed_package": "chromadb",
            "residual_cves": sorted(CHROMA_RESIDUAL_CVES),
            "threat_model": {
                "chromadb_client": "PersistentClient",
                "chromadb_http_api": False,
                "trust_remote_code": False,
                "remote_model_repositories": False,
            },
        },
        "evidence_files": ["supply-chain.json", "sbom.json", "locks.json", "SHA256SUMS"],
        "errors": errors,
        "ok": not errors,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "sbom.json").write_text(
        json.dumps(sbom, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "locks.json").write_text(
        json.dumps(evidence["locks"], indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "supply-chain.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksum_lines = []
    for filename in ("locks.json", "sbom.json", "supply-chain.json"):
        checksum_lines.append(f"{_sha256_file(output / filename)}  {filename}")
    (output / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--require-model", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = generate(
            root=args.root,
            wheel=args.wheel,
            output=args.output,
            model_cache=args.model_cache,
            python=args.python,
            require_model=args.require_model,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(
            json.dumps(
                {"schema_version": 1, "ok": False, "errors": [{"code": "evidence_failed", "message": str(exc)}]},
                ensure_ascii=False,
            )
        )
        return 1
    print(
        json.dumps(
            {"schema_version": 1, "ok": report["ok"], "output": "supply-chain.json", "errors": report["errors"]},
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
