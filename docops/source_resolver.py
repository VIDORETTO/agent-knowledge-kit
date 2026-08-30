"""Resolve local paths, documentation URLs, repositories and product names."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlsplit, urlunsplit


def _normalise_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return result or "documentation"


def canonicalize_url(value: str) -> str:
    """Canonicalize a user URL without fetching it."""

    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"invalid URL: {exc}") from exc
    if parsed.scheme not in {"http", "https"}:
        return value.strip()
    host = (parsed.hostname or "").casefold()
    netloc = host
    if parsed.username is not None or parsed.password is not None:
        # Preserve the signal for the security layer; it will reject userinfo.
        netloc = parsed.netloc
    elif port is not None and not ((parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.casefold(), netloc, path, parsed.query, ""))


@dataclass(frozen=True)
class SourceCandidate:
    """A possible official source for a documentation request."""

    kind: str
    slug: str
    canonical: str
    url: str | None = None
    repo_url: str | None = None
    docs_url: str | None = None
    version: str | None = None
    scope: str | None = None
    language: str | None = None
    license: str | None = None
    official: bool | None = None
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        from .manifest import redact_url

        for key in ("canonical", "url", "repo_url", "docs_url"):
            if isinstance(result.get(key), str):
                result[key] = redact_url(result[key])
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class SourceResolution:
    """Resolution result, including a safe-to-act decision."""

    input: str
    kind: str
    selected: SourceCandidate | None
    candidates: tuple[SourceCandidate, ...] = ()
    requires_decision: bool = False
    decision_reason: str | None = None
    error: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": _redact_source_value(self.input),
            "kind": self.kind,
            "selected": self.selected.to_dict() if self.selected else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "requires_decision": self.requires_decision,
            "decision_reason": self.decision_reason,
            "error": self.error,
        }


def _redact_source_value(value: str) -> str:
    from .manifest import redact_url

    return redact_url(value)


_DEFAULT_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "names": ["fastapi", "fast api"],
        "slug": "fastapi",
        "repo_url": "https://github.com/fastapi/fastapi",
        "docs_url": "https://fastapi.tiangolo.com/",
        "official": True,
        "license": "MIT",
        "confidence": 0.99,
        "evidence": ["official GitHub repository", "official documentation domain"],
    },
    {
        "names": ["pydantic"],
        "slug": "pydantic",
        "repo_url": "https://github.com/pydantic/pydantic",
        "docs_url": "https://docs.pydantic.dev/",
        "official": True,
        "license": "MIT",
        "confidence": 0.97,
        "evidence": ["official GitHub repository", "official documentation domain"],
    },
    {
        "names": ["starlette"],
        "slug": "starlette",
        "repo_url": "https://github.com/encode/starlette",
        "docs_url": "https://www.starlette.io/",
        "official": True,
        "license": "BSD-3-Clause",
        "confidence": 0.97,
        "evidence": ["official GitHub repository", "official documentation domain"],
    },
    {
        "names": ["django"],
        "slug": "django",
        "repo_url": "https://github.com/django/django",
        "docs_url": "https://docs.djangoproject.com/",
        "official": True,
        "license": "BSD-3-Clause",
        "confidence": 0.97,
        "evidence": ["official GitHub repository", "official documentation domain"],
    },
    {
        "names": ["react"],
        "slug": "react",
        "repo_url": "https://github.com/facebook/react",
        "docs_url": "https://react.dev/",
        "official": True,
        "license": "MIT",
        "confidence": 0.96,
        "evidence": ["official GitHub repository", "official documentation domain"],
    },
    {
        "names": ["next.js", "nextjs", "next js"],
        "slug": "nextjs",
        "repo_url": "https://github.com/vercel/next.js",
        "docs_url": "https://nextjs.org/docs",
        "official": True,
        "license": "MIT",
        "confidence": 0.96,
        "evidence": ["official GitHub repository", "official documentation domain"],
    },
)


class SourceResolver:
    """Resolve a source without performing network or subprocess actions."""

    def __init__(
        self,
        catalog: Iterable[Mapping[str, Any]] | None = None,
        *,
        root: Path | str | None = None,
        ambiguity_delta: float = 0.05,
    ) -> None:
        self.root = Path(root or Path.cwd()).resolve()
        self.ambiguity_delta = ambiguity_delta
        self.catalog = tuple(self._candidate_from_mapping(item) for item in (catalog or _DEFAULT_CATALOG))

    @classmethod
    def from_catalog_file(cls, path: Path | str, **kwargs: Any) -> "SourceResolver":
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = loaded.get("sources") if isinstance(loaded, dict) else loaded
        if not isinstance(entries, list):
            raise ValueError("source catalog must contain a list or a sources list")
        return cls(entries, **kwargs)

    @staticmethod
    def _candidate_from_mapping(item: Mapping[str, Any]) -> SourceCandidate:
        names = item.get("names") or [item.get("name") or item.get("slug") or "documentation"]
        if isinstance(names, str):
            names = [names]
        repo_url = item.get("repo_url")
        docs_url = item.get("docs_url") or item.get("url")
        canonical = canonicalize_url(str(repo_url or docs_url or item.get("canonical") or ""))
        kind = "repository" if repo_url else "web"
        return SourceCandidate(
            kind=kind,
            slug=_slug(str(item.get("slug") or names[0])),
            canonical=canonical,
            url=canonicalize_url(str(docs_url)) if docs_url else None,
            repo_url=canonicalize_url(str(repo_url)) if repo_url else None,
            docs_url=canonicalize_url(str(docs_url)) if docs_url else None,
            version=str(item["version"]) if item.get("version") is not None else None,
            scope=str(item["scope"]) if item.get("scope") else None,
            language=str(item["language"]) if item.get("language") else None,
            license=str(item["license"]) if item.get("license") else None,
            official=item.get("official") if isinstance(item.get("official"), bool) else None,
            confidence=float(item.get("confidence", 0.0)),
            evidence=tuple(str(value) for value in (item.get("evidence") or [])),
            aliases=tuple(str(value) for value in names),
        )

    def resolve(
        self,
        value: str,
        *,
        version: str | None = None,
        scope: str | None = None,
        language: str | None = None,
    ) -> SourceResolution:
        raw = value.strip()
        if not raw:
            return SourceResolution(raw, "unknown", None, error={"code": "empty_source", "message": "source is empty"})

        local = self._resolve_local(raw)
        if local:
            return SourceResolution(
                raw,
                "local",
                replace(local, version=version or local.version, scope=scope, language=language),
            )

        try:
            parsed = urlsplit(raw)
            if parsed.scheme in {"http", "https"}:
                _ = parsed.port
        except ValueError as exc:
            return SourceResolution(raw, "unknown", None, error={"code": "invalid_url", "message": str(exc)})
        if parsed.scheme in {"http", "https"}:
            try:
                return self._resolve_url(raw, version=version, scope=scope, language=language)
            except ValueError as exc:
                return SourceResolution(raw, "web", None, error={"code": "invalid_url", "message": str(exc)})
        if parsed.scheme == "file":
            raw_path = unquote(parsed.path)
            if os.name == "nt" and re.match(r"^/[A-Za-z]:/", raw_path):
                raw_path = raw_path[1:]
            if parsed.netloc and parsed.netloc.casefold() != "localhost":
                raw_path = f"//{parsed.netloc}{raw_path}"
            path = Path(raw_path)
            local = self._resolve_local(str(path))
            if local:
                return SourceResolution(
                    raw,
                    "local",
                    replace(local, version=version or local.version, scope=scope, language=language),
                )
            return SourceResolution(raw, "local", None, error={"code": "local_not_found", "message": str(path)})

        candidates = tuple(
            candidate
            for candidate in self.catalog
            if _normalise_name(raw) in {_normalise_name(raw_name) for raw_name in self._names_for(candidate)}
        )
        # The expression above intentionally includes exact canonical slug/name
        # matches. Catalog entries loaded from JSON retain their aliases below.
        if not candidates:
            candidates = tuple(
                candidate for candidate in self.catalog if _normalise_name(raw) == _normalise_name(candidate.slug)
            )
        candidates = tuple(sorted(candidates, key=lambda item: item.confidence, reverse=True))
        if not candidates:
            return SourceResolution(
                raw,
                "name",
                None,
                error={"code": "source_not_found", "message": f"no catalog candidate for {raw!r}"},
            )
        if len(candidates) > 1 and candidates[0].confidence - candidates[1].confidence <= self.ambiguity_delta:
            return SourceResolution(
                raw,
                "name",
                None,
                candidates,
                True,
                "multiple candidates have materially similar confidence",
            )
        selected = replace(
            candidates[0],
            version=version or candidates[0].version,
            scope=scope or candidates[0].scope,
            language=language or candidates[0].language,
        )
        if selected.official is not True:
            return SourceResolution(
                raw,
                "name",
                None,
                (selected,),
                True,
                "candidate is not verified as official",
            )
        return SourceResolution(raw, selected.kind, selected, candidates)

    def _names_for(self, candidate: SourceCandidate) -> tuple[str, ...]:
        return (candidate.slug, *candidate.aliases)

    def _resolve_local(self, raw: str) -> SourceCandidate | None:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = self.root / path
        try:
            resolved = path.resolve()
        except OSError:
            return None
        if not resolved.exists():
            return None
        return SourceCandidate(
            kind="local",
            slug=_slug(resolved.name),
            canonical=resolved.as_uri(),
            version="local",
            official=None,
            confidence=1.0,
            evidence=("existing local path",),
            aliases=(resolved.name,),
        )

    def _resolve_url(
        self,
        raw: str,
        *,
        version: str | None,
        scope: str | None,
        language: str | None,
    ) -> SourceResolution:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").casefold()
        segments = [part for part in parsed.path.split("/") if part]
        if host in {"github.com", "gitlab.com", "bitbucket.org"} and len(segments) >= 2:
            owner, repo = segments[0], segments[1]
            repo = repo.removesuffix(".git")
            ref = version
            selected_scope = scope
            if len(segments) >= 4 and segments[2] in {"tree", "blob", "src"}:
                ref = ref or segments[3]
                selected_scope = selected_scope or "/".join(segments[4:]) or None
            canonical = f"{parsed.scheme.casefold()}://{host}/{owner}/{repo}"
            candidate = SourceCandidate(
                kind="repository",
                slug=_slug(repo),
                canonical=canonical,
                repo_url=canonical,
                version=ref,
                scope=selected_scope,
                language=language,
                official=None,
                confidence=0.9 if host == "github.com" else 0.7,
                evidence=("repository URL supplied by user",),
                aliases=(repo,),
            )
            return SourceResolution(raw, "repository", candidate)

        candidate = SourceCandidate(
            kind="web",
            slug=_slug(parsed.hostname or "documentation"),
            canonical=canonicalize_url(raw),
            url=canonicalize_url(raw),
            version=version,
            scope=scope,
            language=language,
            official=None,
            confidence=0.5,
            evidence=("URL supplied by user; ownership not independently verified",),
            aliases=(parsed.hostname or "documentation",),
        )
        return SourceResolution(raw, "web", candidate)
