from __future__ import annotations

import json
from pathlib import Path

import docops


def test_generated_index_distinguishes_corpus_operator_and_backend_metrics(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "one.md").write_text("# One\n" + ("content " * 220), encoding="utf-8")
    (source / "two.md").write_text("# Two\nShort.", encoding="utf-8")
    output = tmp_path / "package"
    request = docops.OperationRequest(
        source,
        docops.OperationOptions(output_dir=output, source_root=tmp_path, slug="metrics", license="MIT"),
    )

    result = docops.apply(docops.plan(request))
    assert result.ok, result.errors
    index = json.loads((output / "rag" / "index.json").read_text(encoding="utf-8"))

    assert index["corpus_documents"] == 2
    assert index["operator_chunks"] >= 2
    assert index["backend_total_chunks"] is None
    assert index["metrics"] == {
        "corpus_documents": index["corpus_documents"],
        "operator_chunks": index["operator_chunks"],
        "backend_total_chunks": None,
        "backend_total_documents": None,
    }
    assert "chunks" not in index
