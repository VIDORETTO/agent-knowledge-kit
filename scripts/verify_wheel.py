"""Build a wheel in isolation and smoke-test the installed package."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docops import __version__  # noqa: E402

_REPRODUCIBLE_SOURCE_DATE_EPOCH = "0"


def command_failure_details(completed: subprocess.CompletedProcess[str]) -> str:
    """Keep structured CLI errors visible even when a report is very large."""

    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        return f"stdout={completed.stdout[-2000:]} stderr={completed.stderr[-2000:]}"
    if not isinstance(payload, dict):
        return f"stdout={completed.stdout[-2000:]} stderr={completed.stderr[-2000:]}"
    diagnostic = {
        "errors": payload.get("errors", []),
        "outcome": payload.get("outcome"),
    }
    if completed.stderr:
        diagnostic["stderr_tail"] = completed.stderr[-2000:]
    return json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--core", action="store_true", help="exercise the installed wheel without the optional RAG backend"
    )
    mode.add_argument(
        "--require-rag", action="store_true", help="require the installed wheel to complete the real RAG/MCP path"
    )
    args = parser.parse_args(argv)
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
            env={**os.environ, "SOURCE_DATE_EPOCH": _REPRODUCIBLE_SOURCE_DATE_EPOCH},
        )
        wheels = sorted(wheel_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected exactly one wheel, found {len(wheels)}")
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            required = {
                "docops/__init__.py",
                "docops/templates/router.md",
                "docops/schemas/manifest.schema.json",
                "docops/schemas/evaluation.schema.json",
            }
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
        # The checkout carries the reviewed, pinned backend source while the
        # operator wheel intentionally does not vendor it.  Copy that exact
        # backend fixture into the isolated target so this gate exercises the
        # wheel with an explicit installed-package runtime rather than an
        # arbitrary globally installed implementation.  The fixture is copied
        # instead of rebuilt because its upstream packaging metadata includes
        # duplicate data entries on some hatchling versions.
        reviewed_backend = root / "skills" / "vendor" / "knowledge-rag"
        if reviewed_backend.is_dir() and not args.core:
            shutil.copytree(reviewed_backend / "mcp_server", target_dir / "mcp_server")
        environment = dict(os.environ)
        inherited_pythonpath = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(value for value in (str(target_dir), inherited_pythonpath) if value)
        # The wheel gate must exercise the same interpreter for the installed
        # operator and the optional MCP backend.  The environment variable is
        # intentionally scoped to this temporary subprocess environment.
        environment["DOCOPS_RAG_PYTHON"] = str(sys.executable)
        if args.core:
            environment["DOCOPS_SKIP_RAG"] = "1"
        subprocess.run(
            [sys.executable, "-c", f"import docops; assert docops.__version__ == {__version__!r}; "],
            check=True,
            cwd=workspace,
            env=environment,
        )
        source = workspace / "source"
        source.mkdir()
        (source / "guide.md").write_text("# Guide\nRetry policy and exact defaults.\n", encoding="utf-8")
        package = workspace / "package"
        cases = workspace / "cases.json"
        cases.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "reviewed": True,
                    "cases": [{"query": "retry policy", "expected_filepath": "guide.md", "reviewed": True}],
                }
            ),
            encoding="utf-8",
        )
        if args.core:
            rag_available = False
        else:
            rag_probe = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import mcp_server.server",
                ],
                check=False,
                cwd=workspace,
                env=environment,
                capture_output=True,
                text=True,
            )
            rag_available = rag_probe.returncode == 0
        require_rag = args.require_rag or environment.get("DOCOPS_REQUIRE_WHEEL_RAG", "").strip().casefold() in {
            "1",
            "true",
            "yes",
        }
        if require_rag and not rag_available:
            raise RuntimeError("wheel RAG gate requested but knowledge-rag is not installed in the test interpreter")
        adapter = "mcp" if rag_available else "memory"
        run_command = [
            sys.executable,
            "-m",
            "docops",
            "run",
            str(source),
            "--output",
            str(package),
            "--slug",
            "wheel",
            "--license",
            "MIT",
            "--runtime-root",
            str(workspace),
        ]
        if rag_available:
            run_command.append("--index-rag")
        commands = [
            run_command,
            [sys.executable, "-m", "docops", "validate", str(package), "--json"],
            [
                sys.executable,
                "-m",
                "docops",
                "evaluate",
                "--package",
                str(package),
                "--cases",
                str(cases),
                "--adapter",
                adapter,
                "--runtime-root",
                str(workspace),
                "--json",
            ],
        ]
        evaluation: dict[str, object] | None = None
        for command in commands:
            completed = subprocess.run(
                command, check=False, cwd=workspace, env=environment, capture_output=True, text=True
            )
            if completed.returncode:
                raise RuntimeError(f"wheel end-to-end command failed: {command}: {command_failure_details(completed)}")
            if command[3] == "evaluate":
                try:
                    parsed = json.loads(completed.stdout)
                except json.JSONDecodeError as exc:
                    raise RuntimeError("wheel evaluation did not emit JSON") from exc
                if not isinstance(parsed, dict):
                    raise RuntimeError("wheel evaluation emitted an invalid JSON object")
                evaluation = parsed
        if evaluation is None or evaluation.get("ok") is not True:
            raise RuntimeError("wheel evaluation did not produce a successful result")
        metadata = evaluation.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("adapter") != adapter:
            raise RuntimeError(f"wheel evaluation did not report the adapter that was executed: {evaluation!r}")
        if rag_available and (metadata.get("backend") != "knowledge-rag" or not metadata.get("profile")):
            raise RuntimeError("wheel RAG evaluation did not report backend provenance and profile")
        manifest_text = (package / "manifest.json").read_text(encoding="utf-8")
        if str(workspace) in manifest_text or str(PROJECT_ROOT) in manifest_text:
            raise RuntimeError("wheel package leaked a machine-local path into its manifest")
        if rag_available:
            manifest = json.loads(manifest_text)
            runtime = manifest.get("provenance", {}).get("runtime", {}) if isinstance(manifest, dict) else {}
            if runtime.get("backend_source") != "installed-package":
                raise RuntimeError("wheel RAG gate did not record installed-package runtime provenance")
    print(
        json.dumps({"ok": True, "wheel": wheel.name, "version": __version__, "adapter": adapter, "rag": rag_available})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
