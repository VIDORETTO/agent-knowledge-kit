# seam-scope: implementation-infrastructure (public RAGFlow backend fixtures)
from __future__ import annotations

from typing import Any

import pytest

from docops.backends import BackendUnavailable
from docops.backends.ragflow import RagFlowAdapter, _RagFlowSdkClient


class FakeRagFlow:
    version = "0.27.2"

    def __init__(self) -> None:
        self.datasets: dict[str, list[dict[str, Any]]] = {}
        self.deleted: list[str] = []
        self.uploads: list[str] = []

    def health(self) -> dict[str, Any]:
        return {"ok": True, "version": self.version}

    def create_dataset(self, name: str) -> dict[str, str]:
        dataset_id = f"ds-{len(self.datasets) + 1}"
        self.datasets[dataset_id] = []
        return {"id": dataset_id, "name": name}

    def upload_document(self, dataset_id: str, content: str, metadata: dict[str, Any]) -> dict[str, str]:
        document_id = f"doc-{len(self.uploads) + 1}"
        self.uploads.append(document_id)
        self.datasets[dataset_id].append({"document_id": document_id, "content": content, "metadata": metadata})
        return {"id": document_id}

    def parse_document(self, dataset_id: str, document_id: str) -> dict[str, str]:
        return {"status": "done", "dataset_id": dataset_id, "document_id": document_id}

    def list_chunks(self, dataset_id: str, document_id: str) -> list[dict[str, Any]]:
        item = next(value for value in self.datasets[dataset_id] if value["document_id"] == document_id)
        block = item["metadata"]["blocks"][0]
        return [{"id": f"chunk-{document_id}", "content": item["content"], "metadata": block}]

    def search(self, dataset_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        return [{"id": "chunk-doc-1", "score": 0.9, "metadata": {"block_id": "block-1"}, "content": query}][:top_k]

    def delete_dataset(self, dataset_id: str) -> None:
        self.deleted.append(dataset_id)
        self.datasets.pop(dataset_id, None)


class FakeSdkChunk:
    def __init__(self, chunk_id: str, document_id: str, content: str) -> None:
        self.id = chunk_id
        self.document_id = document_id
        self.content = content
        self.positions = [1]


class FakeSdkDocument:
    def __init__(self, dataset_id: str, document_id: str, content: str) -> None:
        self.dataset_id = dataset_id
        self.id = document_id
        self.name = f"{document_id}.txt"
        self.content = content
        self.run = "DONE"
        self.progress = 1.0

    def list_chunks(
        self, *, page: int = 1, page_size: int = 30, keywords: str = "", id: str = ""
    ) -> list[FakeSdkChunk]:
        return [FakeSdkChunk(f"chunk-{self.id}", self.id, self.content)]


class FakeSdkDataset:
    def __init__(self, sdk: "FakeSdk", dataset_id: str, name: str) -> None:
        self.sdk = sdk
        self.id = dataset_id
        self.name = name
        self.document_count = 0
        self.chunk_count = 0

    def upload_documents(self, document_list: list[dict[str, Any]]) -> list[FakeSdkDocument]:
        document = FakeSdkDocument(self.id, f"doc-{len(self.sdk.documents) + 1}", document_list[0]["blob"].decode())
        self.sdk.documents[document.id] = document
        self.document_count += 1
        self.chunk_count += 1
        return [document]

    def async_parse_documents(self, document_ids: list[str]) -> None:
        return None

    def parse_documents(self, document_ids: list[str]) -> list[tuple[str, str, int, int]]:
        return [(document_id, "DONE", 1, 1) for document_id in document_ids]

    def list_documents(self, *, id: str | None = None, page_size: int = 30, **kwargs: Any) -> list[FakeSdkDocument]:
        documents = list(self.sdk.documents.values())
        return [document for document in documents if id is None or document.id == id]


class FakeSdk:
    version = "0.27.2"

    def __init__(self) -> None:
        self.datasets: dict[str, FakeSdkDataset] = {}
        self.documents: dict[str, FakeSdkDocument] = {}
        self.deleted: list[str] = []

    def list_datasets(
        self, *, page: int = 1, page_size: int = 1, id: str | None = None, **kwargs: Any
    ) -> list[FakeSdkDataset]:
        values = list(self.datasets.values())
        return [dataset for dataset in values if id is None or dataset.id == id]

    def create_dataset(self, *, name: str) -> FakeSdkDataset:
        dataset = FakeSdkDataset(self, f"ds-{len(self.datasets) + 1}", name)
        self.datasets[dataset.id] = dataset
        return dataset

    def retrieve(
        self, *, dataset_ids: list[str], question: str, page_size: int, top_k: int, **kwargs: Any
    ) -> list[FakeSdkChunk]:
        assert dataset_ids[0] in self.datasets
        return [FakeSdkChunk("chunk-doc-1", next(iter(self.documents)), question)]

    def delete_datasets(self, *, ids: list[str]) -> None:
        self.deleted.extend(ids)
        for dataset_id in ids:
            self.datasets.pop(dataset_id, None)


def test_ragflow_sdk_0272_adapter_normalizes_real_sdk_lifecycle() -> None:
    sdk = FakeSdk()
    adapter = RagFlowAdapter(
        client=_RagFlowSdkClient(sdk),
        config={"endpoint": "https://ragflow.example.test"},
    )
    candidate = adapter.prepare(
        "project-1",
        "ir-1",
        metadata={
            "documents": [
                {
                    "document_id": "ir-doc-1",
                    "content": "The default token is required.",
                    "blocks": [{"block_id": "block-1", "text": "The default token is required."}],
                }
            ]
        },
    )

    index = adapter.apply(candidate)
    result = adapter.query(index, adapter.query_request("default token", top_k=1))

    assert index.state == "queryable"
    assert result.hits[0]["block_id"] == "block-1"
    adapter.discard(candidate)
    assert sdk.deleted == [candidate.metadata["dataset_id"]]


def _documents() -> list[dict[str, Any]]:
    return [
        {
            "document_id": "ir-doc-1",
            "content": "The default token is required.",
            "blocks": [
                {
                    "block_id": "block-1",
                    "source_id": "source-1",
                    "source_revision_id": "source-rev-1",
                    "locators": [{"kind": "section", "label": "Authentication"}],
                }
            ],
        }
    ]


def test_ragflow_lifecycle_is_idempotent_and_keeps_external_ids_in_candidate_state() -> None:
    client = FakeRagFlow()
    adapter = RagFlowAdapter(
        client=client, config={"endpoint": "http://localhost:9380", "allow_insecure_localhost": True}
    )

    assert adapter.probe().status == "healthy"
    candidate = adapter.prepare("project-1", "ir-1", metadata={"documents": _documents()})
    assert adapter.prepare("project-1", "ir-1", metadata={"documents": _documents()}) == candidate
    index = adapter.apply(candidate)
    assert adapter.apply(candidate) == index
    assert index.state == "queryable"
    assert index.backend == "ragflow"
    assert index.external_ids
    assert adapter.mapping(index).entries[0]["block_id"] == "block-1"
    result = adapter.query(index, adapter.query_request("default token", top_k=1))
    assert result.hits[0]["block_id"] == "block-1"
    snapshot = adapter.snapshot(index)
    assert snapshot.index_revision == index.index_revision
    assert adapter.stats(index)["mapped_chunks"] == 1
    discarded = adapter.discard(candidate)
    assert discarded.status == "discarded"
    assert client.deleted == [candidate.metadata["dataset_id"]]
    with pytest.raises(BackendUnavailable) as missing:
        adapter.query(index, adapter.query_request("default token", top_k=1))
    assert missing.value.code == "index_unknown"


def test_ragflow_rejects_remote_http_without_explicit_localhost_policy() -> None:
    adapter = RagFlowAdapter(client=FakeRagFlow(), config={"endpoint": "http://ragflow.example.test"})

    with pytest.raises(BackendUnavailable) as caught:
        adapter.probe()
    assert caught.value.code == "tls_required"
