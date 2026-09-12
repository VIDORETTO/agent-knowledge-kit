"""Opt-in contract spike for the pinned RAGFlow v0.27.2 runtime.

The core suite never starts Docker or contacts a remote service.  Set
``DOCOPS_RAGFLOW_INTEGRATION=1`` together with an endpoint, token, image digest
and SDK version to run this test against an operator-provisioned instance.
Missing external resources are reported as an explicit ``not_run`` skip.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _required_environment() -> tuple[str, str, str, str]:
    if os.environ.get("DOCOPS_RAGFLOW_INTEGRATION") != "1":
        pytest.skip("not_run: RAGFlow integration is opt-in")

    endpoint = os.environ.get("DOCOPS_RAGFLOW_ENDPOINT", "").strip()
    token = os.environ.get("DOCOPS_RAGFLOW_TOKEN", "").strip()
    image_digest = os.environ.get("DOCOPS_RAGFLOW_IMAGE_DIGEST", "").strip()
    sdk_version = os.environ.get("DOCOPS_RAGFLOW_SDK_VERSION", "").strip()
    missing = [
        name
        for name, value in (
            ("DOCOPS_RAGFLOW_ENDPOINT", endpoint),
            ("DOCOPS_RAGFLOW_TOKEN", token),
            ("DOCOPS_RAGFLOW_IMAGE_DIGEST", image_digest),
            ("DOCOPS_RAGFLOW_SDK_VERSION", sdk_version),
        )
        if not value
    ]
    if missing:
        pytest.skip(f"not_run: missing external RAGFlow inputs {', '.join(missing)}")
    if not re.fullmatch(r".+@sha256:[0-9a-f]{64}", image_digest):
        pytest.fail("RAGFlow image must be pinned by repository and sha256 digest")
    return endpoint, token, image_digest, sdk_version


def _fixture_pdf(path: Path) -> None:
    # Two tiny text pages keep the oracle independent of a production corpus.
    # The instance is still responsible for proving whether page locators are
    # exported by its parser.  Build a valid PDF with an xref table so the
    # oracle exercises parsing rather than malformed-input recovery.
    def page_stream(label: str) -> bytes:
        content = f"BT /F1 12 Tf 20 100 Td ({label}) Tj ET".encode("ascii")
        return f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 2 /Kids [3 0 R 4 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 7 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>",
        page_stream("FAROL_PAGE_ONE"),
        page_stream("FAROL_PAGE_TWO"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:]))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(output))


def _wait_for_parse(dataset: object, document_id: str, *, timeout_seconds: float = 120.0) -> object:
    deadline = time.monotonic() + timeout_seconds
    while True:
        documents = dataset.list_documents(id=document_id, page=1, page_size=1)  # type: ignore[attr-defined]
        assert documents, "RAGFlow no longer exposes the uploaded document"
        document = documents[0]
        status = str(getattr(document, "run", getattr(document, "status", ""))).casefold()
        if status in {"fail", "failed", "cancel", "cancelled", "canceled", "error"}:
            pytest.fail(f"RAGFlow parsing failed with status {status!r}")
        if (
            status in {"done", "success", "succeeded", "completed"}
            or float(getattr(document, "progress", 0.0) or 0.0) >= 1.0
        ):
            return document
        if time.monotonic() >= deadline:
            pytest.fail("RAGFlow parsing did not finish before the 120 second deadline")
        time.sleep(0.5)


def test_ragflow_v0272_dataset_parse_retrieve_and_cleanup(tmp_path: Path) -> None:
    endpoint, token, image_digest, sdk_version = _required_environment()
    if sdk_version != "0.27.2":
        pytest.fail(f"RAGFlow SDK contract is pinned to 0.27.2, got {sdk_version!r}")

    try:
        from ragflow_sdk import RAGFlow  # type: ignore[import-not-found]
    except ImportError:
        pytest.skip("not_run: ragflow_sdk 0.27.2 is not installed in the integration environment")

    fixture = tmp_path / "two-pages.pdf"
    _fixture_pdf(fixture)
    dataset = None
    dataset_name = f"farol-v2-spike-{os.urandom(8).hex()}"
    client = RAGFlow(api_key=token, base_url=endpoint)
    try:
        dataset = client.create_dataset(name=dataset_name)
        documents = dataset.upload_documents([{"display_name": fixture.name, "blob": fixture.read_bytes()}])
        assert documents, "RAGFlow accepted a dataset but returned no uploaded document"
        document = documents[0]
        dataset.parse_documents([document.id])
        document = _wait_for_parse(dataset, document.id)
        chunks = document.list_chunks()
        assert chunks, "RAGFlow parsing produced no chunks"
        chunk_text = "\n".join(str(getattr(chunk, "content", "")) for chunk in chunks)
        assert "FAROL_PAGE_ONE" in chunk_text or "FAROL_PAGE_TWO" in chunk_text
        locators = [
            getattr(chunk, "positions", None) or getattr(chunk, "position", None) or getattr(chunk, "metadata", None)
            for chunk in chunks
        ]
        assert any(locator for locator in locators), "RAGFlow returned chunks without locator metadata"
        retrieved = client.retrieve(question="Which page contains FAROL_PAGE_TWO?", dataset_ids=[dataset.id])
        assert retrieved, "RAGFlow retrieval returned no result for known fixture content"
    finally:
        if dataset is not None:
            client.delete_datasets(ids=[dataset.id])

    # Keep the test's receipt-safe identity observable without ever printing a
    # token or a private endpoint in pytest output.
    assert image_digest.startswith("ragflow@sha256:") or "@sha256:" in image_digest
    assert token not in dataset_name
