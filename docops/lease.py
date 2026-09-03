"""Recoverable local writer lease for one generated package."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LeaseBusyError(RuntimeError):
    """Raised when another live operation owns the package lease."""

    def __init__(self, details: dict[str, Any]) -> None:
        self.details = details
        super().__init__(details.get("message", "package writer lease is busy"))


@dataclass(frozen=True)
class LeaseInfo:
    path: Path
    token: str
    pid: int
    started_at: float
    hostname: str

    @property
    def age_seconds(self) -> float:
        return max(0.0, time.time() - self.started_at)

    @property
    def owner_id(self) -> str:
        raw = f"{self.hostname}:{self.pid}".encode("utf-8", errors="replace")
        return f"owner-{hashlib.sha256(raw).hexdigest()[:12]}"

    def diagnostic(self, *, action: str = "retry later") -> dict[str, Any]:
        return {
            "owner": self.owner_id,
            "age_seconds": round(self.age_seconds, 3),
            "action": action,
            "message": "another operation owns the package writer lease",
        }


class PackageLease:
    """Exclusive file lease that never terminates an unrelated process."""

    def __init__(
        self,
        package_root: Path | str,
        *,
        policy: str = "fail",
        wait_seconds: float = 0.0,
        stale_after_seconds: float = 300.0,
    ) -> None:
        if policy not in {"fail", "wait"}:
            raise ValueError("lease policy must be fail or wait")
        if wait_seconds < 0 or stale_after_seconds <= 0:
            raise ValueError("lease timeouts must be non-negative and stale_after_seconds must be positive")
        root = Path(os.path.abspath(os.fspath(Path(package_root).expanduser())))
        self.path = root.parent / f".{root.name}.docops.writer.lock"
        self.policy = policy
        self.wait_seconds = wait_seconds
        self.stale_after_seconds = stale_after_seconds
        self._owned: LeaseInfo | None = None

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except PermissionError:
            # The process may exist even when this account cannot inspect it;
            # an unverifiable owner is never safe to reclaim.
            return True
        except (OSError, ProcessLookupError):
            return False
        return True

    def _read_existing(self) -> LeaseInfo | None:
        if self.path.is_symlink():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return None
            pid = int(raw.get("pid", 0))
            started_at = float(raw.get("started_at", 0.0))
            token = str(raw.get("token", ""))
            hostname = str(raw.get("hostname", "unknown"))
            if pid <= 0 or started_at <= 0 or not token:
                return None
            return LeaseInfo(self.path, token, pid, started_at, hostname)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _try_reclaim_stale(self, existing: LeaseInfo | None) -> bool:
        if self.path.is_symlink():
            return False
        if existing is None:
            # A malformed lock is not proof of orphaning.  Keep a recent one
            # and report it as busy; only an old malformed file is eligible
            # for recovery, so a crashed writer cannot be mistaken for a
            # concurrent writer during the safety window.
            try:
                age = max(0.0, time.time() - self.path.stat().st_mtime)
                if age < self.stale_after_seconds:
                    return False
                self.path.unlink()
                return True
            except FileNotFoundError:
                return True
            except OSError:
                return False
        if existing.age_seconds < self.stale_after_seconds or self._pid_alive(existing.pid):
            return False
        try:
            self.path.unlink()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        return True

    def acquire(self) -> LeaseInfo:
        deadline = time.monotonic() + self.wait_seconds
        while True:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            token = uuid.uuid4().hex
            payload = {
                "schema_version": 1,
                "pid": os.getpid(),
                "started_at": time.time(),
                "hostname": socket.gethostname(),
                "token": token,
            }
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                self._owned = LeaseInfo(self.path, token, os.getpid(), payload["started_at"], payload["hostname"])
                return self._owned
            except FileExistsError:
                if self.path.is_symlink():
                    details = {
                        "owner": "unknown",
                        "age_seconds": 0.0,
                        "action": "remove the symbolic link after verifying its target",
                        "message": "package writer lock path is a symbolic link",
                    }
                    if self.policy == "wait" and time.monotonic() < deadline:
                        time.sleep(0.05)
                        continue
                    raise LeaseBusyError(details)
                existing = self._read_existing()
                if existing is not None and existing.token == token:
                    continue
                if existing is not None and existing.pid == os.getpid() and existing.hostname == socket.gethostname():
                    details = existing.diagnostic(action="finish the existing operation before retrying")
                else:
                    details = (existing or LeaseInfo(self.path, "", 0, time.time(), "unknown")).diagnostic(
                        action="inspect or remove the lock only after its stale window"
                    )
                if self._try_reclaim_stale(existing):
                    continue
                if self.policy == "wait" and time.monotonic() < deadline:
                    time.sleep(0.05)
                    continue
                raise LeaseBusyError(details)

    def release(self) -> None:
        owned = self._owned
        if owned is None:
            return
        try:
            current = self._read_existing()
            if current is not None and current.token == owned.token:
                self.path.unlink(missing_ok=True)
        except OSError:
            return
        finally:
            self._owned = None

    def __enter__(self) -> LeaseInfo:
        return self.acquire()

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.release()
