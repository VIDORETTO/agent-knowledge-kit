"""Create a portable project environment.

Examples:
    python scripts/bootstrap.py                 # project + format helpers
    python scripts/bootstrap.py --rag           # also install knowledge-rag
    python scripts/bootstrap.py --dev --rag     # install test/lint tools too
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import venv
from pathlib import Path


def venv_python(root: Path) -> Path:
    relative = (Path("Scripts") / "python.exe") if sys.platform == "win32" else (Path("bin") / "python")
    return root / ".venv" / relative


def install_command(python: Path, root: Path, *, rag: bool, formats: bool, dev: bool) -> list[str]:
    command = [str(python), "-m", "pip", "install", "--editable", str(root)]
    if rag:
        # requirements.txt already contains the optional format helpers. Keep
        # the requirements file as one argument; passing it again as a
        # positional package makes pip treat the filename as a distribution.
        command.extend(["--requirement", str(root / "requirements.txt")])
    elif formats:
        command.extend(["PyYAML==6.0.3", "pypdf==6.16.2", "python-docx==1.2.0"])
    if dev:
        command.extend(["pytest==8.4.1", "ruff==0.12.7"])
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--rag", action="store_true", help="install the pinned knowledge-rag integration")
    formats_group = parser.add_mutually_exclusive_group()
    formats_group.add_argument("--formats", dest="formats", action="store_true", help="install optional document format helpers (default)")
    formats_group.add_argument("--no-formats", dest="formats", action="store_false", help="skip optional document format helpers")
    parser.set_defaults(formats=True)
    parser.add_argument("--dev", action="store_true", help="install pytest and ruff")
    parser.add_argument("--no-install", action="store_true", help="create the venv but do not run pip")
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if not (root / "pyproject.toml").is_file():
        print(json.dumps({"ok": False, "error": {"code": "project_metadata_missing", "message": str(root / "pyproject.toml")}}))
        return 1
    python = venv_python(root)
    if not python.exists():
        venv.EnvBuilder(with_pip=True, clear=False).create(root / ".venv")
    command = install_command(python, root, rag=args.rag, formats=args.formats, dev=args.dev)
    if not args.no_install:
        completed = subprocess.run(command, cwd=root, check=False)
        if completed.returncode:
            return completed.returncode
    print(json.dumps({"ok": True, "python": str(python), "rag": args.rag, "formats": args.formats, "dev": args.dev}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
