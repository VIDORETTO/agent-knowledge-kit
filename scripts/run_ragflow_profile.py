"""Run the opt-in RAGFlow contract gate with fail-closed external checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any

EXPECTED_SDK_VERSION = "0.27.2"
IMAGE_DIGEST_PATTERN = re.compile(r".+@sha256:[0-9a-f]{64}")
REQUIRED_ENVIRONMENT = (
    "DOCOPS_RAGFLOW_ENDPOINT",
    "DOCOPS_RAGFLOW_TOKEN",
    "DOCOPS_RAGFLOW_IMAGE_DIGEST",
    "DOCOPS_RAGFLOW_SDK_VERSION",
)


def _redact(value: str, secrets: tuple[str, ...]) -> str:
    redacted = value
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted[-4000:]


def _report(payload: dict[str, Any], *, exit_code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", default="tests/spikes/test_ragflow_contract.py")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable report line")
    args = parser.parse_args(argv)

    values = {name: os.environ.get(name, "").strip() for name in REQUIRED_ENVIRONMENT}
    missing = [name for name, value in values.items() if not value]
    if missing:
        return _report(
            {
                "schema_version": 1,
                "ok": False,
                "status": "blocked",
                "reason": "missing_external_inputs",
                "missing": missing,
                "sdk_version": EXPECTED_SDK_VERSION,
            },
            exit_code=1,
        )
    if values["DOCOPS_RAGFLOW_SDK_VERSION"] != EXPECTED_SDK_VERSION:
        return _report(
            {
                "schema_version": 1,
                "ok": False,
                "status": "blocked",
                "reason": "sdk_version_mismatch",
                "expected_sdk_version": EXPECTED_SDK_VERSION,
            },
            exit_code=1,
        )
    if not IMAGE_DIGEST_PATTERN.fullmatch(values["DOCOPS_RAGFLOW_IMAGE_DIGEST"]):
        return _report(
            {
                "schema_version": 1,
                "ok": False,
                "status": "blocked",
                "reason": "image_digest_unpinned",
                "expected": "repository@sha256:<64 hex>",
            },
            exit_code=1,
        )
    try:
        import ragflow_sdk  # type: ignore[import-not-found]
    except ImportError:
        return _report(
            {
                "schema_version": 1,
                "ok": False,
                "status": "blocked",
                "reason": "sdk_missing",
                "expected_sdk_version": EXPECTED_SDK_VERSION,
            },
            exit_code=1,
        )
    observed_version = str(getattr(ragflow_sdk, "__version__", ""))
    if observed_version != EXPECTED_SDK_VERSION:
        return _report(
            {
                "schema_version": 1,
                "ok": False,
                "status": "blocked",
                "reason": "installed_sdk_version_mismatch",
                "expected_sdk_version": EXPECTED_SDK_VERSION,
                "observed_sdk_version": observed_version or None,
            },
            exit_code=1,
        )

    environment = dict(os.environ)
    environment["DOCOPS_RAGFLOW_INTEGRATION"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", args.test],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    secrets = tuple(values[name] for name in REQUIRED_ENVIRONMENT)
    payload = {
        "schema_version": 1,
        "ok": completed.returncode == 0,
        "status": "passed" if completed.returncode == 0 else "failed",
        "reason": None if completed.returncode == 0 else "contract_test_failed",
        "sdk_version": observed_version,
        "stdout_tail": _redact(completed.stdout, secrets),
        "stderr_tail": _redact(completed.stderr, secrets),
    }
    return _report(payload, exit_code=completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
