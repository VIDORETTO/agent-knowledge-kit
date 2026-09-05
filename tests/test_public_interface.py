from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import docops


def test_root_python_interface_builds_a_plan_without_legacy_imports(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nStable policy.\n", encoding="utf-8")
    output = tmp_path / "package"

    options = docops.OperationOptions(
        output_dir=output,
        source_root=tmp_path,
        slug="guide",
        license="MIT",
    )
    request = docops.OperationRequest("source", options)
    operation = docops.plan(request)

    assert operation.ok
    assert operation.request.options.output_dir == output.resolve()
    assert operation.to_dict()["plan_version"] == 1


def test_root_python_interface_applies_and_inspects_through_supported_types(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nStable policy.\n", encoding="utf-8")
    output = tmp_path / "package"
    request = docops.OperationRequest(
        "source",
        docops.OperationOptions(output_dir=output, source_root=tmp_path, slug="guide", license="MIT"),
    )

    result = docops.apply(docops.plan(request))
    inspection = docops.inspect(output)

    assert isinstance(result, docops.OperationResult)
    assert result.ok
    assert inspection["managed"] is True
    assert inspection["active"]["validation"]["ok"] is True


def test_root_operation_request_and_result_are_immutable(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\n", encoding="utf-8")
    output = tmp_path / "package"
    request = docops.OperationRequest(
        source,
        docops.OperationOptions(output_dir=output, slug="guide", license="MIT"),
    )
    result = docops.apply(docops.plan(request))

    with __import__("pytest").raises(FrozenInstanceError):
        request.source = "changed"
    with __import__("pytest").raises(FrozenInstanceError):
        result.ok = False


def test_root_operation_result_nested_data_is_immutable(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\n", encoding="utf-8")
    result = docops.apply(
        docops.plan(
            docops.OperationRequest(
                source,
                docops.OperationOptions(output_dir=tmp_path / "package", slug="guide", license="MIT"),
            )
        )
    )

    import pytest

    with pytest.raises(TypeError):
        result.manifest["changed"] = True
    with pytest.raises(AttributeError):
        result.errors.append({"code": "changed"})
    with pytest.raises(TypeError):
        result.state_diff["added"] = 99
    with pytest.raises(AttributeError):
        result.warnings.append("changed")
    with pytest.raises(TypeError):
        result.outcome["status"] = "changed"


def test_document_update_preserves_an_externally_enriched_skill(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    guide = source / "guide.md"
    guide.write_text("# Guide\nBefore factual policy.\n", encoding="utf-8")
    output = tmp_path / "package"
    request = docops.OperationRequest(
        source,
        docops.OperationOptions(output_dir=output, source_root=tmp_path, slug="guide", license="MIT"),
    )

    first = docops.apply(docops.plan(request))
    assert first.ok, first.errors
    skill = output / "skill" / "SKILL.md"
    enriched = (
        skill.read_text(encoding="utf-8").replace(
            "This structural scaffold contains headings and provenance only; an external `book-to-skill` skill may fold richer mental models into it.",
            "This skill contains the reviewed mental model from book-to-skill.",
        )
        + "\n## Mental model\n\nKeep the enriched decision model.\n"
    )
    skill.write_text(enriched, encoding="utf-8")
    docops.record_skill_enrichment(output, tool="book-to-skill", version="2.0")

    guide.write_text("# Guide\nAfter factual policy.\n", encoding="utf-8")
    update_request = docops.OperationRequest(
        source,
        docops.OperationOptions(
            output_dir=output,
            source_root=tmp_path,
            slug="guide",
            license="MIT",
            mode="update",
        ),
    )
    updated = docops.apply(docops.plan(update_request))

    assert updated.ok, updated.errors
    assert (output / "skill" / "SKILL.md").read_text(encoding="utf-8") == enriched
    assert (output / "rag" / "documents" / "guide.md").read_text(encoding="utf-8") == "# Guide\nAfter factual policy.\n"
    assert updated.manifest["readiness"]["skill"] == "skill-enriched"
