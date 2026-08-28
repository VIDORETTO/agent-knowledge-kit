"""Copy the distributable tree to a temporary directory and run its checks."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_IGNORED_DIRS = {
    ".git",
    ".venv",
    ".venv-rag",
    "data",
    "models_cache",
    ".pytest_cache",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
}


def _ignore(directory: str, names: list[str]) -> set[str]:
    relative = Path(directory).resolve()
    ignored = {name for name in names if name in _IGNORED_DIRS or name.endswith(".egg-info")}
    if relative.name == "documents":
        ignored.update(name for name in names if name not in {"README.md", "examples", "fixtures"})
    return ignored


def copy_distributable_tree(source: Path, destination: Path) -> None:
    """Copy source code and synthetic fixtures, excluding local state."""

    shutil.copytree(source, destination, ignore=_ignore)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep the temporary clone and print its path")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    temporary = tempfile.mkdtemp(prefix="docops-clean-clone-")
    destination = Path(temporary) / source.name
    copy_distributable_tree(source, destination)
    environment = {**os.environ, "DOCOPS_SKIP_RAG": "1"}
    commands = [
        [args.python, "-m", "docops", "doctor", "--root", str(destination), "--json"],
        [args.python, "scripts/audit_release.py", "--root", str(destination), "--json"],
    ]
    if not args.skip_tests:
        commands.append([args.python, "-m", "pytest", "-q"])
    reports: list[dict[str, object]] = []
    for command in commands:
        completed = subprocess.run(command, cwd=destination, env=environment, check=False, capture_output=True, text=True)
        reports.append({"command": command, "returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]})
        if completed.returncode:
            print(json.dumps({"ok": False, "clone": str(destination), "reports": reports}, indent=2, ensure_ascii=False))
            if not args.keep:
                shutil.rmtree(Path(temporary), ignore_errors=True)
            return completed.returncode
    print(json.dumps({"ok": True, "clone": str(destination), "reports": reports}, indent=2, ensure_ascii=False))
    if not args.keep:
        shutil.rmtree(Path(temporary), ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
