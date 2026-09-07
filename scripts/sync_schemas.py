"""Check and reproduce the schema tree distributed inside the DOCOPS wheel."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable


def _finding(code: str, path: Path, message: str) -> dict[str, str]:
    return {"code": code, "path": path.as_posix(), "message": message}


def _schema_files(root: Path) -> dict[str, Path]:
    if not root.is_dir() or root.is_symlink():
        return {}
    return {path.name: path for path in sorted(root.glob("*.schema.json")) if path.is_file() and not path.is_symlink()}


def check_schema_distribution(canonical_root: Path | str, bundled_root: Path | str) -> dict[str, object]:
    """Compare distributed schema bytes with the canonical checkout tree."""

    canonical = Path(canonical_root).expanduser().resolve()
    bundled = Path(bundled_root).expanduser().resolve()
    findings: list[dict[str, str]] = []
    if not canonical.is_dir() or canonical.is_symlink():
        findings.append(_finding("schema_canonical_missing", canonical, "canonical schema directory is unavailable"))
    if not bundled.is_dir() or bundled.is_symlink():
        findings.append(_finding("schema_bundle_missing", bundled, "bundled schema directory is unavailable"))
    canonical_files = _schema_files(canonical)
    bundled_files = _schema_files(bundled)
    for name in sorted(set(canonical_files) - set(bundled_files)):
        findings.append(_finding("schema_bundle_missing", bundled / name, "schema is not distributed"))
    for name in sorted(set(bundled_files) - set(canonical_files)):
        findings.append(_finding("schema_bundle_extra", bundled_files[name], "bundled schema has no canonical source"))
    for name in sorted(set(canonical_files) & set(bundled_files)):
        try:
            canonical_bytes = canonical_files[name].read_bytes()
            bundled_bytes = bundled_files[name].read_bytes()
        except OSError as exc:
            findings.append(_finding("schema_unreadable", canonical_files[name], str(exc)))
            continue
        if canonical_bytes != bundled_bytes:
            findings.append(
                _finding(
                    "schema_content_drift",
                    bundled_files[name],
                    f"bundled bytes differ from canonical {canonical_files[name].as_posix()}",
                )
            )
    return {
        "schema_version": 1,
        "ok": not findings,
        "canonical_root": canonical.as_posix(),
        "bundled_root": bundled.as_posix(),
        "schema_count": len(canonical_files),
        "findings": findings,
    }


def sync_schema_distribution(canonical_root: Path | str, bundled_root: Path | str) -> dict[str, object]:
    """Copy canonical schemas to the bundled tree, then verify exact bytes."""

    canonical = Path(canonical_root).expanduser().resolve()
    bundled = Path(bundled_root).expanduser().resolve()
    if not canonical.is_dir() or canonical.is_symlink():
        return check_schema_distribution(canonical, bundled)
    bundled.mkdir(parents=True, exist_ok=True)
    canonical_files = _schema_files(canonical)
    for name in set(_schema_files(bundled)) - set(canonical_files):
        extra = bundled / name
        if extra.is_file() and not extra.is_symlink():
            extra.unlink()
    for name, source in canonical_files.items():
        target = bundled / name
        if target.is_symlink():
            target.unlink()
        shutil.copyfile(source, target)
    return check_schema_distribution(canonical, bundled)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=Path(__file__).resolve().parents[1] / "schemas")
    parser.add_argument("--bundled", type=Path, default=Path(__file__).resolve().parents[1] / "docops" / "schemas")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="copy canonical schemas before checking")
    mode.add_argument("--check", action="store_true", help="check without writing (the default)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = (
        sync_schema_distribution(args.canonical, args.bundled)
        if args.write
        else check_schema_distribution(args.canonical, args.bundled)
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
