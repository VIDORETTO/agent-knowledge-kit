from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from docops.lease import LeaseBusyError, PackageLease
from docops.package_validator import validate_package
from docops.pipeline import PipelineOptions, apply, plan


def test_package_lease_serializes_writers_and_redacts_owner_identity(tmp_path: Path) -> None:
    package = tmp_path / "package"
    first = PackageLease(package)
    first.acquire()
    try:
        second = PackageLease(package)
        with pytest.raises(LeaseBusyError) as caught:
            second.acquire()
        assert caught.value.details["owner"].startswith("owner-")
        assert "pid" not in caught.value.details
        assert str(package) not in json.dumps(caught.value.details)
    finally:
        first.release()


def test_stale_dead_package_lease_can_be_reclaimed_without_killing_processes(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.parent.mkdir(parents=True, exist_ok=True)
    lock = package.parent / ".package.docops.writer.lock"
    lock.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pid": 99999999,
                "started_at": time.time() - 1000,
                "hostname": "fixture",
                "token": "old",
            }
        ),
        encoding="utf-8",
    )

    lease = PackageLease(package, stale_after_seconds=10)
    info = lease.acquire()

    assert info.pid > 0
    assert lock.is_file()
    lease.release()
    assert not lock.exists()


def test_lease_does_not_reclaim_a_stale_lock_when_pid_identity_is_unverifiable(tmp_path: Path, monkeypatch) -> None:
    package = tmp_path / "package"
    package.parent.mkdir(parents=True, exist_ok=True)
    lock = package.parent / ".package.docops.writer.lock"
    lock.write_text(
        json.dumps(
            {"schema_version": 1, "pid": 12345, "started_at": time.time() - 1000, "hostname": "fixture", "token": "old"}
        ),
        encoding="utf-8",
    )

    def deny_pid_probe(_pid: int, _signal: int) -> None:
        raise PermissionError("pid probe denied")

    monkeypatch.setattr("docops.lease.os.kill", deny_pid_probe)
    with pytest.raises(LeaseBusyError):
        PackageLease(package, stale_after_seconds=10).acquire()

    assert lock.is_file()


def test_concurrent_applies_leave_one_complete_generation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\n", encoding="utf-8")
    output = tmp_path / "package"
    options = PipelineOptions(output_dir=output, slug="guide", license="MIT")
    operations = [plan(source, options=options), plan(source, options=options)]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(apply, operations))

    assert sum(result.ok for result in results) == 1
    assert any(result.outcome["code"] in {"writer_busy", "stale_plan"} for result in results if not result.ok)
    assert validate_package(output).ok
