# seam-scope: compatibility-infrastructure (pure policy classifier)
from __future__ import annotations

from scripts.audit_dependencies import CHROMA_RESIDUAL_CVES, _classify, _raw_findings


def _audit(*dependencies: dict[str, object]) -> dict[str, object]:
    return {"dependencies": list(dependencies)}


def _dependency(name: str, version: str, *vulnerability_ids: str) -> dict[str, object]:
    return {
        "name": name,
        "version": version,
        "vulns": [
            {"id": vulnerability_id, "aliases": [], "fix_versions": []} for vulnerability_id in vulnerability_ids
        ],
    }


def test_dependency_audit_allows_only_the_documented_chroma_residuals() -> None:
    chroma = _dependency("chromadb", "1.5.9", *sorted(CHROMA_RESIDUAL_CVES))

    residual, unresolved = _classify([_audit(chroma)])

    assert not unresolved
    assert {finding["id"] for finding in residual} == CHROMA_RESIDUAL_CVES


def test_dependency_audit_rejects_future_chroma_and_non_chroma_findings() -> None:
    chroma = _dependency("chromadb", "1.5.9", "CVE-2099-00001")
    pytest = _dependency("pytest", "9.1.1", "CVE-2099-00002")

    residual, unresolved = _classify([_audit(chroma, pytest)])

    assert not residual
    assert {(finding["package"], finding["id"]) for finding in unresolved} == {
        ("chromadb", "CVE-2099-00001"),
        ("pytest", "CVE-2099-00002"),
    }


def test_dependency_audit_keeps_raw_findings_separate_from_policy_classification() -> None:
    chroma = _dependency("chromadb", "1.5.9", *sorted(CHROMA_RESIDUAL_CVES))

    raw = _raw_findings([_audit(chroma)])

    assert len(raw) == len(CHROMA_RESIDUAL_CVES)
    assert {finding["id"] for finding in raw} == CHROMA_RESIDUAL_CVES


def test_dependency_allowlist_is_bound_to_the_audited_chromadb_version() -> None:
    future = _dependency("chromadb", "9.9.9", *sorted(CHROMA_RESIDUAL_CVES))

    residual, unresolved = _classify([_audit(future)])

    assert residual == []
    assert {finding["id"] for finding in unresolved} == CHROMA_RESIDUAL_CVES
