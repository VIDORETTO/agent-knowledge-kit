# seam-scope: implementation-infrastructure (public format extractor fixtures)
from __future__ import annotations

from pathlib import Path

from docops.extractors import ExtractorPolicy
from docops.extractors.pdf import PdfExtractor
from docops.ir import validate_ir_document


def _pdf_page(text: str, *, page_count: int = 1) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Count {page_count} /Kids [{' '.join(f'{3 + index} 0 R' for index in range(page_count))}] >>".encode(),
    ]
    for index in range(page_count):
        content_id = 3 + page_count + index
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 {3 + page_count * 2} 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
    for index in range(page_count):
        value = f"PAGE_{index + 1}_{text}".encode()
        stream = b"BT /F1 12 Tf 20 100 Td (" + value + b") Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Producer (Farol fixture) >>")
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def _policy(**kwargs: object) -> ExtractorPolicy:
    return ExtractorPolicy(
        rights_ref="rights-pdf",
        source_id="source-pdf",
        source_revision_id="revision-pdf",
        required_fidelity="structured-native",
        **kwargs,
    )


def test_textual_pdf_preserves_page_locators(tmp_path: Path) -> None:
    source = tmp_path / "guide.pdf"
    source.write_bytes(_pdf_page("KNOWN", page_count=2))
    result = PdfExtractor().extract(source, _policy(), {})

    assert result.document is not None
    assert result.receipt.fidelity == "structured-native"
    assert [block.locators[0]["page"] for block in result.document.blocks] == [1, 2]
    assert "PAGE_1_KNOWN" in " ".join(block.text or "" for block in result.document.blocks)
    assert validate_ir_document(result.document).ok


def test_scanned_pdf_is_quarantined_without_authorized_ocr(tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")
    result = PdfExtractor().extract(source, _policy(), {})

    assert result.document is None
    assert result.receipt.status == "quarantined"
    assert result.receipt.errors[0]["code"] == "ocr_required"


def test_ocr_requires_opt_in_and_low_confidence_stays_quarantined(tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"scan-bytes")
    calls: list[str] = []

    def ocr(path: Path, _policy: ExtractorPolicy):
        calls.append(path.name)
        return [{"page": 1, "text": "OCR text", "confidence": 0.4}]

    denied = PdfExtractor(ocr=ocr).extract(source, _policy(), {})
    assert calls == []
    assert denied.receipt.status == "quarantined"

    allowed = PdfExtractor(ocr=ocr).extract(
        source,
        _policy(allow_remote=True, authorized_extractors=("ocr",)),
        {},
    )
    assert calls == ["scan.pdf"]
    assert allowed.document is None
    assert allowed.receipt.quarantine_reason == "low_confidence"
