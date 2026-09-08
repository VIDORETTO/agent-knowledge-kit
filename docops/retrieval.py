"""Retrieval adapters used by the factual, skill and router evaluation seams."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping, Protocol

from .mcp_client import McpEofError, McpTimeoutError, first_json_payload, start_mcp_server
from .revisions import package_revisions
from .runtime import discover_rag_python, runtime_environment, runtime_provenance

_TOKEN = re.compile(r"[\wÀ-ÿ][\wÀ-ÿ./:-]*", re.UNICODE)


class RetrievalError(RuntimeError):
    """A reportable failure at a retrieval adapter boundary."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


class RetrievalAdapter(Protocol):
    """Minimal public seam shared by local and MCP retrieval backends."""

    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]: ...

    def metadata(self) -> dict[str, Any]: ...

    def close(self) -> None: ...


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value)}


def _load_source_metadata(package_root: Path | str) -> dict[str, dict[str, Any]]:
    path = Path(package_root).resolve() / "rag" / "sources.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    entries = payload.get("sources") if isinstance(payload, Mapping) else None
    if not isinstance(entries, list):
        return {}
    metadata: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or not entry.get("destination"):
            continue
        destination = str(entry["destination"]).replace("\\", "/").lstrip("./")
        metadata[destination] = dict(entry)
    return metadata


def _citation_fragment(locator: Mapping[str, Any]) -> str | None:
    kind = str(locator.get("kind") or "").strip()
    label = str(locator.get("label") or "").strip().replace("#", "%23").replace("\n", " ")
    if not kind or not label:
        return None
    return f"{kind}={label}"


def _citations_for(source: str, locators: list[Mapping[str, Any]]) -> list[str]:
    citations: list[str] = []
    for locator in locators:
        fragment = _citation_fragment(locator)
        if fragment:
            citation = f"{source}#{fragment}"
            if citation not in citations:
                citations.append(citation)
    return citations


def _rank(
    documents: Mapping[str, str],
    query: str,
    max_results: int,
    metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    ranked: list[dict[str, Any]] = []
    for path, content in documents.items():
        content_tokens = _tokens(content)
        path_tokens = _tokens(path)
        overlap = len(query_tokens & content_tokens) / len(query_tokens) if query_tokens else 0.0
        path_overlap = len(query_tokens & path_tokens) / len(query_tokens) if query_tokens else 0.0
        phrase = 1.0 if query and query.casefold() in content.casefold() else 0.0
        source_metadata = dict((metadata or {}).get(path, {}))
        locators = source_metadata.get("locators")
        if not isinstance(locators, list):
            locators = []
        hit: dict[str, Any] = {
            "source": path,
            "content": content,
            "score": overlap + path_overlap * 0.5 + phrase * 0.5,
            "locators": [dict(locator) for locator in locators if isinstance(locator, Mapping)],
        }
        hit["citations"] = _citations_for(path, hit["locators"])
        for key in (
            "source_id",
            "observed_revision",
            "canonical",
            "destination",
            "format",
            "title",
            "quality_status",
            "quality_reason",
        ):
            if key in source_metadata:
                hit[key] = source_metadata[key]
        ranked.append(hit)
    ranked.sort(key=lambda item: (-float(item["score"]), str(item["source"])))
    return ranked[:max_results]


class InMemoryRetrievalAdapter:
    """A deterministic adapter for tests without mocking DOCOPS internals."""

    def __init__(
        self,
        documents: Mapping[str, str],
        *,
        profile: str = "memory-v1",
        document_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.documents = {str(path).replace("\\", "/"): str(content) for path, content in documents.items()}
        self.profile = profile
        self.document_metadata = {
            str(path).replace("\\", "/").lstrip("./"): dict(value)
            for path, value in (document_metadata or {}).items()
            if isinstance(value, Mapping)
        }

    @classmethod
    def from_package(cls, package_root: Path | str) -> "InMemoryRetrievalAdapter":
        root = Path(package_root).resolve() / "rag" / "documents"
        documents = {
            path.relative_to(root).as_posix(): path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()
        }
        return cls(documents, document_metadata=_load_source_metadata(package_root))

    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]:
        return _rank(self.documents, query, max_results, self.document_metadata)

    def metadata(self) -> dict[str, Any]:
        return {
            "backend": "memory",
            "adapter": "memory",
            "mode": "gate",
            "profile": self.profile,
            "corpus": {
                "corpus_documents": len(self.documents),
                "operator_chunks": None,
                "backend_total_documents": None,
                "backend_total_chunks": None,
            },
        }

    def close(self) -> None:
        return


class LexicalDiagnosticAdapter(InMemoryRetrievalAdapter):
    """The fast token-overlap scorer retained as a named diagnostic."""

    def __init__(self, package_root: Path | str) -> None:
        loaded = InMemoryRetrievalAdapter.from_package(package_root)
        super().__init__(
            loaded.documents,
            profile="token-overlap-v1",
            document_metadata=loaded.document_metadata,
        )

    def metadata(self) -> dict[str, Any]:
        value = super().metadata()
        value.update({"backend": "lexical", "adapter": "lexical-diagnostic", "mode": "diagnostic"})
        return value


class SkillRetrievalAdapter(InMemoryRetrievalAdapter):
    """Search the generated skill artifacts for conceptual cases."""

    def __init__(self, package_root: Path | str) -> None:
        root = Path(package_root).resolve() / "skill"
        documents = {
            path.relative_to(root).as_posix(): path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(root.rglob("*.md"))
            if path.is_file() and not path.is_symlink()
        }
        super().__init__(documents, profile="skill-markdown-v1")

    def metadata(self) -> dict[str, Any]:
        value = super().metadata()
        value.update({"backend": "skill", "adapter": "skill-conceptual", "mode": "gate"})
        return value


def route_query(query: str) -> str:
    """Classify a query using the documented skill/RAG routing policy."""

    persistent = re.compile(
        r"\b(add|approve|change|delete|index|ingest|modify|publish|reconcile|register|remove|revoke|rollback|update)\b",
        re.I,
    )
    literal = re.compile(
        r"\b(default|defaults|signature|endpoint|version|changelog|exact|literal|parameter|config(?:uration)?)\b", re.I
    )
    conceptual = re.compile(r"\b(how|why|pattern|concept|conceptual|guide|best practice|trade-?off|design)\b", re.I)
    if persistent.search(query):
        return "lifecycle"
    has_literal = bool(literal.search(query))
    has_conceptual = bool(conceptual.search(query))
    if has_literal and has_conceptual:
        return "both"
    if has_literal:
        return "rag"
    return "skill"


def _safe_source_reference(raw_source: str, documents_root: Path) -> str:
    normalized = raw_source.strip().replace("\\", "/")
    if not normalized or "://" in normalized:
        return "<external-source>" if normalized else "<unknown-source>"
    source_path = Path(raw_source)
    is_absolute = source_path.is_absolute() or bool(re.match(r"^[A-Za-z]:/", normalized))
    if is_absolute:
        try:
            return source_path.resolve().relative_to(documents_root.resolve()).as_posix()
        except (ValueError, OSError):
            marker = "/rag/documents/"
            if marker in normalized:
                candidate = normalized.split(marker, 1)[1]
                parts = tuple(part for part in candidate.split("/") if part not in {"", "."})
                if parts and ".." not in parts:
                    return "/".join(parts)
            return "<external-source>"
    for prefix in ("./", "documents/", "rag/documents/"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    parts = tuple(part for part in normalized.split("/") if part not in {"", "."})
    if not parts or ".." in parts:
        return "<external-source>"
    return "/".join(parts)


class McpRetrievalAdapter:
    """Adapter over the actual package-local knowledge-rag MCP server."""

    def __init__(
        self,
        package_root: Path | str,
        *,
        python: Path | str | None = None,
        runtime_root: Path | str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.package_root = Path(package_root).resolve()
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else self.package_root
        self.python = Path(python) if python else None
        self.timeout_seconds = timeout_seconds
        self.client: Any = None
        self.server_info: dict[str, Any] = {}
        self.source_metadata = _load_source_metadata(self.package_root)
        self.pinned_composition: str | None = None
        self._reader_workspace: tempfile.TemporaryDirectory[str] | None = None

    def _prepare_reader_workspace(self) -> Path:
        """Create an isolated backend snapshot for a query-only session.

        Chroma can update SQLite bookkeeping files while opening or querying a
        persistent collection, even when the MCP capability is read-only. The
        package itself is immutable evidence, so the reader process must use a
        disposable copy of the RAG artifacts. The adapter still pins and
        rechecks the original package generation around every query.
        """

        if self._reader_workspace is not None:
            return Path(self._reader_workspace.name)
        workspace = tempfile.TemporaryDirectory(prefix="docops-mcp-reader-")
        snapshot = Path(workspace.name)
        try:
            config = self.package_root / "config.yaml"
            rag = self.package_root / "rag"
            if not config.is_file() or config.is_symlink():
                raise RetrievalError("rag_config_missing", "indexed MCP packages require a regular config.yaml")
            if not rag.is_dir() or rag.is_symlink():
                raise RetrievalError("rag_snapshot_missing", "indexed MCP packages require a regular rag directory")
            if any(path.is_symlink() for path in rag.rglob("*")):
                raise RetrievalError("rag_snapshot_unsafe", "MCP reader snapshots reject symbolic links")
            shutil.copy2(config, snapshot / "config.yaml")
            shutil.copytree(rag, snapshot / "rag", symlinks=False)
        except (OSError, shutil.Error) as exc:
            workspace.cleanup()
            raise RetrievalError("rag_snapshot_failed", "could not create an isolated MCP reader snapshot") from exc
        except RetrievalError:
            workspace.cleanup()
            raise
        self._reader_workspace = workspace
        return snapshot

    def _cleanup_reader_workspace(self) -> None:
        workspace = self._reader_workspace
        self._reader_workspace = None
        if workspace is not None:
            workspace.cleanup()

    def _ensure_client(self) -> Any:
        if self.client is not None:
            return self.client
        index = self._index()
        if index.get("mode") != "indexed":
            raise RetrievalError("rag_not_indexed", "MCP evaluation requires an indexed package")
        try:
            self.pinned_composition = str(package_revisions(self.package_root)["composition_hash"])
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise RetrievalError("generation_unavailable", "package generation could not be pinned") from exc
        executable = self.python or discover_rag_python(self.runtime_root).path
        if not executable.is_file():
            raise RetrievalError("rag_python_missing", "knowledge-rag Python executable is unavailable")
        vendor = self.runtime_root / "skills" / "vendor" / "knowledge-rag"
        reader_root = self._prepare_reader_workspace()
        environment = runtime_environment(reader_root, vendor_root=vendor, read_only=True)
        try:
            self.client = start_mcp_server(
                executable,
                reader_root,
                env=environment,
            )
        except (McpTimeoutError, McpEofError) as exc:
            self._cleanup_reader_workspace()
            details = {"exit_code": exc.exit_code} if isinstance(exc, McpEofError) and exc.exit_code is not None else {}
            raise RetrievalError(exc.code, "retrieval backend did not respond", details=details) from exc
        except (OSError, RuntimeError, TimeoutError) as exc:
            self._cleanup_reader_workspace()
            raise RetrievalError("mcp_start_failed", "could not start the retrieval backend") from exc
        self.server_info = dict(getattr(self.client, "server_info", {}) or {})
        expected_version = runtime_provenance(self.runtime_root, python=executable, environ=environment).get(
            "expected_version"
        )
        actual_version = self.server_info.get("version")
        if expected_version and actual_version != expected_version:
            self.close()
            raise RetrievalError(
                "rag_version_mismatch",
                "retrieval backend version does not match the selected runtime",
                details={"expected_version": expected_version, "actual_version": actual_version},
            )
        return self.client

    def _assert_pinned_generation(self) -> None:
        if self.pinned_composition is None:
            return
        try:
            current = str(package_revisions(self.package_root)["composition_hash"])
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise RetrievalError("generation_unavailable", "package generation could not be revalidated") from exc
        if current != self.pinned_composition:
            raise RetrievalError("generation_changed", "package generation changed during a pinned reader session")

    def _revoked_destinations(self) -> set[str]:
        path = self.package_root / ".docops" / "revocations.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return set()
        records = payload.get("sources") if isinstance(payload, dict) else []
        blocked: set[str] = set()
        if isinstance(records, list):
            for record in records:
                if isinstance(record, Mapping) and isinstance(record.get("destinations"), list):
                    blocked.update(str(item).replace("\\", "/").lstrip("./") for item in record["destinations"])
        return blocked

    def _index(self) -> dict[str, Any]:
        try:
            value = json.loads((self.package_root / "rag" / "index.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RetrievalError("rag_index_unreadable", "could not read package RAG metadata") from exc
        return value if isinstance(value, dict) else {}

    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]:
        client = self._ensure_client()
        self._assert_pinned_generation()
        try:
            response = client.call(
                "tools/call",
                name="search_knowledge",
                arguments={"query": query, "max_results": max_results},
                timeout=self.timeout_seconds,
            )
        except (McpTimeoutError, McpEofError) as exc:
            details = {"exit_code": exc.exit_code} if isinstance(exc, McpEofError) and exc.exit_code is not None else {}
            raise RetrievalError(exc.code, "retrieval backend did not return a response", details=details) from exc
        except (OSError, RuntimeError, TimeoutError) as exc:
            raise RetrievalError("mcp_search_failed", "retrieval backend did not return a response") from exc
        if response.get("error"):
            raise RetrievalError("mcp_search_failed", "retrieval backend returned an error")
        payload = first_json_payload(response)
        if not payload or not isinstance(payload.get("results"), list):
            raise RetrievalError("mcp_invalid_response", "retrieval backend returned no structured results")
        hits: list[dict[str, Any]] = []
        documents_root = self.package_root / "rag" / "documents"
        for item in payload["results"][:max_results]:
            if not isinstance(item, Mapping):
                continue
            raw_source = str(item.get("source") or item.get("path") or "")
            source = _safe_source_reference(raw_source, documents_root)
            if source in self._revoked_destinations():
                continue
            source_metadata = dict(self.source_metadata.get(source, {}))
            raw_locators = item.get("locators")
            locators = raw_locators if isinstance(raw_locators, list) else source_metadata.get("locators", [])
            if not isinstance(locators, list):
                locators = []
            hit: dict[str, Any] = {
                "source": source,
                "content": str(item.get("content") or ""),
                "score": item.get("score", 0.0),
                "locators": [dict(locator) for locator in locators if isinstance(locator, Mapping)],
            }
            hit["citations"] = _citations_for(source, hit["locators"])
            for key in ("format", "title", "quality_status", "quality_reason"):
                if key in source_metadata:
                    hit[key] = source_metadata[key]
            hits.append(hit)
        return hits

    def metadata(self) -> dict[str, Any]:
        index = self._index()
        return {
            "backend": "knowledge-rag",
            "adapter": "mcp",
            "mode": "gate",
            "profile": index.get("profile") or index.get("embedding_profile") or "unknown",
            "version": self.server_info.get("version") or runtime_provenance(self.runtime_root).get("backend_version"),
            "corpus": {
                "corpus_documents": index.get("corpus_documents", index.get("documents", 0)),
                "operator_chunks": index.get("operator_chunks", index.get("chunks", 0)),
                "backend_total_documents": index.get("backend_total_documents"),
                "backend_total_chunks": index.get("backend_total_chunks"),
            },
        }

    def close(self) -> None:
        try:
            if self.client is not None:
                self.client.close()
        finally:
            self.client = None
            self.pinned_composition = None
            self._cleanup_reader_workspace()


def adapter_for_package(
    package_root: Path | str,
    adapter: str | RetrievalAdapter | None,
    *,
    runtime_root: Path | str | None = None,
) -> RetrievalAdapter:
    """Resolve the named evaluation backend without hiding its provenance."""

    if adapter is None or adapter == "lexical":
        return LexicalDiagnosticAdapter(package_root)
    if adapter == "memory":
        return InMemoryRetrievalAdapter.from_package(package_root)
    if adapter == "mcp":
        return McpRetrievalAdapter(package_root, runtime_root=runtime_root)
    if hasattr(adapter, "search") and hasattr(adapter, "metadata"):
        return adapter
    raise ValueError("adapter must be lexical, memory, mcp or a RetrievalAdapter")
