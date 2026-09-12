"""PDF text/page extraction and explicitly authorized OCR handoff."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping

from ..api_types import CapabilityV2
from ..ir import ExtractionReceipt, IRBlock, IRDocument
from ..revisions import content_hash
from .base import ExtractionResult, ExtractorError, ExtractorPolicy


class PdfExtractor:
    name = "pdf"
    version = "2.0"

    def __init__(self, *, ocr: Callable[[Path, ExtractorPolicy], list[Mapping[str, Any]]] | None = None) -> None:
        self.ocr = ocr

    def describe(self) -> CapabilityV2:
        return CapabilityV2(
            name=self.name,
            version=self.version,
            status="available",
            supports=["application/pdf", ".pdf"],
            fidelity=["structured-native", "external-converter", "metadata-only"],
            execution="local",
            permissions=["read-private-staging", "ocr-opt-in"],
            dependencies=[{"name": "pypdf", "optional": True}],
        )

    def extract(
        self,
        artifact: Path | str | Mapping[str, Any],
        policy: ExtractorPolicy,
        budget: Mapping[str, Any],
    ) -> ExtractionResult:
        if not policy.rights_ref:
            raise ExtractorError("rights_required", "rights_ref is required before extraction")
        path, metadata = _artifact_path(artifact)
        if not path.is_file() or path.is_symlink():
            raise ExtractorError("artifact_unavailable", "artifact must be a regular file")
        raw = path.read_bytes()
        if len(raw) > int(budget.get("max_bytes", policy.max_bytes)):
            raise ExtractorError("budget_exceeded", "PDF exceeds extractor byte budget")
        input_hash = hashlib.sha256(raw).hexdigest()
        pages = _extract_pages(path)
        if not pages:
            if not policy.allow_remote or "ocr" not in set(policy.authorized_extractors):
                return _failed_result(path, policy, input_hash, "ocr_required", "ocr_required")
            if self.ocr is None:
                return _failed_result(path, policy, input_hash, "ocr_adapter_missing", "dependency_missing")
            pages = [dict(page) for page in self.ocr(path, policy)]
            if not pages:
                return _failed_result(path, policy, input_hash, "ocr_empty", "ocr_empty")
            confidence = min(float(page.get("confidence", 0.0)) for page in pages)
            if confidence < policy.ocr_confidence_threshold:
                return _failed_result(path, policy, input_hash, "low_confidence", "low_confidence")
            fidelity = "external-converter"
            execution = "remote"
        else:
            fidelity = "structured-native"
            execution = "local"
        blocks: list[IRBlock] = []
        for ordinal, page in enumerate(pages):
            page_number = int(page.get("page", ordinal + 1))
            text = str(page.get("text") or "").strip()
            if not text:
                continue
            confidence = page.get("confidence")
            blocks.append(
                IRBlock(
                    block_id=hashlib.sha256(f"{input_hash}:{page_number}:{text}".encode("utf-8")).hexdigest()[:24],
                    parent_id=None,
                    ordinal=len(blocks),
                    kind="paragraph",
                    text=text,
                    heading_path=[f"Page {page_number}"],
                    locators=[
                        {
                            "kind": "page",
                            "label": f"Page {page_number}",
                            "page": page_number,
                            "bbox": page.get("bbox"),
                            "available": True,
                        }
                    ],
                    confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
                    quality_flags=["ocr"] if execution == "remote" else [],
                    source_fragment_hash=content_hash({"page": page_number, "text": text}),
                )
            )
        if not blocks:
            return _failed_result(path, policy, input_hash, "empty_document", "empty_document")
        if len(blocks) > int(budget.get("max_blocks", policy.max_blocks)):
            raise ExtractorError("budget_exceeded", "extracted block count exceeds budget")
        document = IRDocument(
            document_id=str(metadata.get("document_id") or f"ir-{input_hash[:24]}"),
            source_id=policy.source_id,
            source_revision_id=policy.source_revision_id,
            artifact_id=str(metadata.get("artifact_id") or path.name),
            content_hash=input_hash,
            media_type="application/pdf",
            language=str(metadata.get("language") or "und"),
            extractor={"name": self.name, "version": self.version, "execution": execution},
            fidelity={"level": fidelity, "capabilities": ["page", "text"], "degradations": []},
            rights_ref=policy.rights_ref,
            captured_at=str(metadata.get("captured_at") or "1970-01-01T00:00:00Z"),
            effective_at=None,
            region=None,
            blocks=blocks,
            origin=str(metadata.get("canonical") or path.resolve().as_uri()),
        )
        receipt = ExtractionReceipt(
            artifact_id=document.artifact_id,
            source_id=policy.source_id,
            source_revision_id=policy.source_revision_id,
            extractor=document.extractor,
            fidelity=fidelity,
            status="extracted",
            input_hash=input_hash,
            ir_revision=document.revision_hash(),
        )
        return ExtractionResult(document, receipt)


def _artifact_path(artifact: Path | str | Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    if isinstance(artifact, Mapping):
        raw = artifact.get("path") or artifact.get("local_path")
        if not isinstance(raw, str):
            raise ExtractorError("artifact_invalid", "artifact path is required")
        return Path(raw).expanduser().resolve(), dict(artifact)
    return Path(artifact).expanduser().resolve(), {}


def _extract_pages(path: Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        raise ExtractorError("dependency_missing", "pypdf is required for local PDF extraction")
    try:
        reader = PdfReader(str(path))
        pages = []
        for index, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({"page": index, "text": text})
        return pages
    except Exception:
        # A valid scanned PDF and a parser-degraded PDF both have no textual
        # blocks at this seam.  Keep them quarantined until an authorized OCR
        # adapter proves otherwise; never reinterpret raw bytes as text.
        return []


def _failed_result(
    path: Path, policy: ExtractorPolicy, input_hash: str, code: str, quarantine_reason: str
) -> ExtractionResult:
    status = "quarantined" if quarantine_reason in {"ocr_required", "low_confidence"} else "failed"
    receipt = ExtractionReceipt(
        artifact_id=path.name,
        source_id=policy.source_id,
        source_revision_id=policy.source_revision_id,
        extractor={"name": "pdf", "version": "2.0", "execution": "local"},
        fidelity="metadata-only",
        status=status,
        input_hash=input_hash,
        errors=[{"code": code, "message": code}],
        quarantine_reason=quarantine_reason if status == "quarantined" else None,
    )
    return ExtractionResult(None, receipt, {"code": code})
