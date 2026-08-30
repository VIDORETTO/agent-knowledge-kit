"""Build a wheel in isolation and smoke-test the installed package."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops import __version__  # noqa: E402


def main() -> int:
    root = PROJECT_ROOT
    with tempfile.TemporaryDirectory(prefix="docops-wheel-") as temporary:
        workspace = Path(temporary)
        wheel_dir = workspace / "wheel"
        target_dir = workspace / "installed"
        wheel_dir.mkdir()
        subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheel_dir), str(root)],
            check=True,
            cwd=root,
        )
        wheels = sorted(wheel_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected exactly one wheel, found {len(wheels)}")
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            required = {"docops/__init__.py", "docops/templates/router.md"}
            missing = sorted(required - names)
            if missing:
                raise RuntimeError(f"wheel is missing package files: {missing}")
            metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
            metadata = archive.read(metadata_name).decode("utf-8")
            if f"Version: {__version__}" not in metadata:
                raise RuntimeError(f"wheel metadata does not declare version {__version__}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target_dir), str(wheel)],
            check=True,
            cwd=root,
            capture_output=True,
            text=True,
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(target_dir)
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import docops; from docops.pipeline import _router_artifact; "
                f"assert docops.__version__ == {__version__!r}; "
                "assert 'search_knowledge' in _router_artifact('smoke')",
            ],
            check=True,
            cwd=workspace,
            env=environment,
        )
    print(json.dumps({"ok": True, "wheel": wheel.name, "version": __version__}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
