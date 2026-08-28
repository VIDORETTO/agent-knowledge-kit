"""Normalize supported documentation formats without executing their content."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .web_acquirer import normalize_html

SUPPORTED_SUFFIXES = {
    ".md", ".markdown", ".rst", ".adoc", ".txt", ".html", ".htm", ".pdf",
    ".docx", ".py", ".c", ".h", ".cpp", ".js", ".jsx", ".ts", ".tsx",
    ".json", ".yaml", ".yml", ".xml", ".csv", ".ipynb", ".xlsx", ".pptx",
}

_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above)\s+instructions?\b", re.I),
    re.compile(r"\b(reveal|show|print|leak)\s+(?:the\s+)?(?:secret|credential|api\s*key|password)", re.I),
    re.compile(r"\bsystem\s+message\b", re.I),
    re.compile(r"\bdo\s+not\s+(?:tell|mention|disclose)", re.I),
)


@dataclass
class NormalizationResult:
    status: str
    content: str
    origin: str
    format: str
    title: str | None = None
    warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    error: str | None = None
    untrusted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "content": self.content,
            "origin": self.origin,
            "format": self.format,
            "title": self.title,
            "warnings": self.warnings,
            "error_code": self.error_code,
            "error": self.error,
            "untrusted": self.untrusted,
        }


def _title_from_markdown(content: str, fallback: str) -> str:
    for line in content.splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return fallback


def _untrusted_warnings(content: str) -> tuple[bool, list[str]]:
    if any(pattern.search(content) for pattern in _INJECTION_PATTERNS):
        return True, ["possible prompt injection detected; content is untrusted and was not executed"]
    return False, []


def _openapi_markdown(document: dict[str, Any]) -> str:
    info = document.get("info") if isinstance(document.get("info"), dict) else {}
    title = str(info.get("title") or "OpenAPI document")
    version = info.get("version")
    lines = [f"# {title}"]
    if version:
        lines.append(f"\nVersion: `{version}`")
    if document.get("openapi"):
        lines.append(f"\nOpenAPI: `{document['openapi']}`")
    elif document.get("swagger"):
        lines.append(f"\nSwagger: `{document['swagger']}`")
    servers = document.get("servers")
    if isinstance(servers, list) and servers:
        lines.append("\n## Servers")
        for server in servers:
            if isinstance(server, dict) and server.get("url"):
                lines.append(f"- `{server['url']}`")
    paths = document.get("paths")
    if isinstance(paths, dict):
        lines.append("\n## Endpoints")
        for path, operations in paths.items():
            if not isinstance(operations, dict):
                continue
            for method, operation in operations.items():
                if method.casefold() not in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
                    continue
                operation = operation if isinstance(operation, dict) else {}
                lines.append(f"\n### {method.upper()} `{path}`")
                if operation.get("summary"):
                    lines.append(str(operation["summary"]))
                if operation.get("description"):
                    lines.append(str(operation["description"]))
                responses = operation.get("responses")
                if isinstance(responses, dict):
                    lines.append("\nResponses:")
                    for code, response in responses.items():
                        description = response.get("description", "") if isinstance(response, dict) else ""
                        lines.append(f"- `{code}`: {description}")
    return "\n".join(lines).strip() + "\n"


def _load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to normalize YAML/OpenAPI files") from exc
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        raise ValueError(f"invalid YAML: {exc}") from exc


def _extract_pdf(path: Path) -> str:
    text_parts: list[str] = []
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        reader = PdfReader(str(path))
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    except ImportError:
        try:
            import fitz  # type: ignore[import-not-found]

            document = fitz.open(str(path))
            text_parts = [page.get_text() or "" for page in document]
        except ImportError as exc:
            raise RuntimeError("pypdf or PyMuPDF is required to normalize PDFs") from exc
        except Exception:
            text_parts = []
    except Exception:
        # A scanned or malformed PDF is never silently treated as text.
        text_parts = []
    return "\n\n".join(part.strip() for part in text_parts if part and part.strip()).strip()


def normalize_file(path: Path | str, *, source_url: str | None = None) -> NormalizationResult:
    """Normalize one file and return an explicit status for unsupported inputs."""

    file_path = Path(path).expanduser().resolve()
    origin = source_url or file_path.as_uri()
    suffix = file_path.suffix.casefold()
    if not file_path.is_file():
        return NormalizationResult("error", "", origin, suffix.lstrip("."), error_code="not_found", error="file does not exist")
    if suffix not in SUPPORTED_SUFFIXES:
        return NormalizationResult("ignored", "", origin, suffix.lstrip("."), error_code="unsupported_format", error="format is not supported")

    warnings: list[str] = []
    title: str | None = None
    fmt = suffix.lstrip(".")
    try:
        if suffix in {".html", ".htm"}:
            document = normalize_html(file_path.read_bytes(), source_url or origin)
            content = document.content
            title = document.title or _title_from_markdown(content, file_path.stem)
            fmt = "html"
        elif suffix == ".pdf":
            content = _extract_pdf(file_path)
            fmt = "pdf"
            if not content:
                return NormalizationResult("ocr_required", "", origin, fmt, error_code="ocr_required", error="no extractable text; run OCR before ingestion")
            title = file_path.stem
        elif suffix == ".docx":
            try:
                from docx import Document  # type: ignore[import-not-found]
            except ImportError:
                return NormalizationResult("dependency_missing", "", origin, "docx", error_code="dependency_missing", error="python-docx is required")
            document = Document(str(file_path))
            content = "\n\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
            title = _title_from_markdown(content, file_path.stem)
        elif suffix == ".json":
            raw = file_path.read_text(encoding="utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                content = raw
                warnings.append("invalid JSON preserved as text")
            else:
                if isinstance(parsed, dict) and ("openapi" in parsed or "swagger" in parsed) and isinstance(parsed.get("paths"), dict):
                    content = _openapi_markdown(parsed)
                    fmt = "openapi"
                    title = _title_from_markdown(content, file_path.stem)
                else:
                    content = json.dumps(parsed, ensure_ascii=False, indent=2)
                    title = file_path.stem
        elif suffix in {".yaml", ".yml"}:
            try:
                parsed = _load_yaml(file_path)
            except RuntimeError as exc:
                return NormalizationResult("dependency_missing", "", origin, "yaml", error_code="dependency_missing", error=str(exc))
            except ValueError as exc:
                return NormalizationResult("error", "", origin, "yaml", error_code="invalid_document", error=str(exc))
            if isinstance(parsed, dict) and ("openapi" in parsed or "swagger" in parsed) and isinstance(parsed.get("paths"), dict):
                content = _openapi_markdown(parsed)
                fmt = "openapi"
                title = _title_from_markdown(content, file_path.stem)
            else:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                title = file_path.stem
        else:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            title = _title_from_markdown(content, file_path.stem)
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        return NormalizationResult("error", "", origin, fmt, error_code="read_failed", error=str(exc))

    content = content.strip()
    if not content:
        return NormalizationResult("error", "", origin, fmt, title=title, error_code="empty_document", error="document has no text")
    untrusted, injection_warnings = _untrusted_warnings(content)
    warnings.extend(injection_warnings)
    return NormalizationResult("accepted", content, origin, fmt, title=title, warnings=warnings, untrusted=untrusted)
