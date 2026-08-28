"""Canonical source state and resumable phase checkpoints."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .source_resolver import canonicalize_url
from .storage import write_json_atomic


def content_identity(canonical: str, version: str | None, content_hash: str) -> str:
    """Return a stable identity for one versioned source representation."""

    value = "\0".join((canonicalize_url(canonical), version or "", content_hash.lower()))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _logical_key(canonical: str, version: str | None) -> str:
    return "\0".join((canonicalize_url(canonical), version or ""))


@dataclass(frozen=True)
class SourceRecord:
    canonical: str
    version: str | None
    content_hash: str
    destination: str

    @property
    def logical_key(self) -> str:
        return _logical_key(self.canonical, self.version)

    @property
    def identity(self) -> str:
        return content_identity(self.canonical, self.version, self.content_hash)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical": canonicalize_url(self.canonical),
            "version": self.version,
            "content_hash": self.content_hash.lower(),
            "destination": self.destination.replace("\\", "/"),
            "identity": self.identity,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SourceRecord":
        return cls(
            canonical=str(raw["canonical"]),
            version=str(raw["version"]) if raw.get("version") is not None else None,
            content_hash=str(raw["content_hash"]),
            destination=str(raw["destination"]).replace("\\", "/"),
        )


@dataclass(frozen=True)
class StateDiff:
    added: list[SourceRecord]
    updated: list[tuple[SourceRecord, SourceRecord]]
    removed: list[SourceRecord]

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.updated or self.removed)


class StateStore:
    """Persist one logical record per canonical source/version pair."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._records: dict[str, SourceRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ValueError(f"unsupported state schema in {self.path}")
        records = raw.get("records", [])
        if not isinstance(records, list):
            raise ValueError(f"state records must be a list in {self.path}")
        for item in records:
            if isinstance(item, dict):
                record = SourceRecord.from_dict(item)
                self._records[record.logical_key] = record

    def records(self) -> list[SourceRecord]:
        return sorted(self._records.values(), key=lambda record: record.logical_key)

    @staticmethod
    def _deduplicate(records: Iterable[SourceRecord]) -> dict[str, SourceRecord]:
        result: dict[str, SourceRecord] = {}
        for record in records:
            key = record.logical_key
            previous = result.get(key)
            if previous is None or record.destination < previous.destination:
                result[key] = record
        return result

    def plan(self, current: Iterable[SourceRecord]) -> StateDiff:
        desired = self._deduplicate(current)
        added = [desired[key] for key in sorted(desired.keys() - self._records.keys())]
        updated = [
            (self._records[key], desired[key])
            for key in sorted(desired.keys() & self._records.keys())
            if self._records[key].identity != desired[key].identity
            or self._records[key].destination != desired[key].destination
        ]
        removed = [self._records[key] for key in sorted(self._records.keys() - desired.keys())]
        return StateDiff(added, updated, removed)

    def commit(self, current: Iterable[SourceRecord]) -> None:
        self._records = self._deduplicate(current)
        self._save()

    def commit_record(self, record: SourceRecord) -> None:
        self._records[record.logical_key] = record
        self._save()

    def remove_record(self, record: SourceRecord) -> None:
        self._records.pop(record.logical_key, None)
        self._save()

    def _save(self) -> None:
        write_json_atomic(
            self.path,
            {"schema_version": 1, "records": [record.to_dict() for record in self.records()]},
        )


class CheckpointStore:
    """Atomic phase checkpoints that survive a process interruption."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "phases": {}}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ValueError(f"unsupported checkpoint schema in {self.path}")
        if not isinstance(raw.get("phases"), dict):
            raise ValueError(f"checkpoint phases must be an object in {self.path}")
        return raw

    def save(self, phase: str, payload: dict[str, Any]) -> None:
        state = self._read()
        state["phases"][phase] = payload
        write_json_atomic(self.path, state)

    def load(self, phase: str) -> dict[str, Any] | None:
        value = self._read()["phases"].get(phase)
        return dict(value) if isinstance(value, dict) else None

    def all(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in self._read()["phases"].items() if isinstance(value, dict)}
