from __future__ import annotations

import subprocess
from pathlib import Path

from docops.repository_acquirer import RepositoryAcquirer, RepositoryAcquisitionResult
from docops.source_resolver import SourceCandidate


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_local_repository_resolves_docs_tree_commit_and_declared_license(tmp_path: Path) -> None:
    repo = tmp_path / "source"
    (repo / "docs" / "en").mkdir(parents=True)
    (repo / "docs" / "en" / "index.md").write_text("# Guide\n", encoding="utf-8")
    (repo / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "fixture@example.test")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "initial")

    result = RepositoryAcquirer().acquire(repo)

    assert result.ok
    assert result.docs_relative == "docs/en"
    assert result.commit
    assert result.version == "local"
    assert result.license["status"] == "declared"
    assert result.files == ["docs/en/index.md"]


def test_repository_scope_is_honoured_and_unsupported_files_are_not_selected(tmp_path: Path) -> None:
    repo = tmp_path / "source"
    (repo / "documentation").mkdir(parents=True)
    (repo / "documentation" / "guide.exe").write_text("not docs", encoding="utf-8")
    (repo / "documentation" / "guide.md").write_text("# Guide", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "fixture@example.test")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "initial")

    result = RepositoryAcquirer().acquire(repo, scope="documentation")

    assert result.ok
    assert result.docs_relative == "documentation"
    assert result.files == ["documentation/guide.md"]


def test_remote_repository_acquisition_blocks_private_network_targets() -> None:
    candidate = SourceCandidate(
        kind="repository",
        slug="private",
        canonical="http://127.0.0.1/private",
        repo_url="http://127.0.0.1/private",
    )

    result = RepositoryAcquirer().acquire(candidate)

    assert not result.ok
    assert result.errors[0]["code"] == "ssrf_blocked"


def test_temporary_repository_result_can_clean_up_only_its_owned_root(tmp_path: Path) -> None:
    temporary_root = tmp_path / "docops-owned-clone"
    temporary_root.mkdir()
    (temporary_root / "marker").write_text("temporary", encoding="utf-8")
    result = RepositoryAcquisitionResult(True, root=temporary_root, temporary=True)

    result.cleanup()

    assert not temporary_root.exists()
    assert not result.temporary
