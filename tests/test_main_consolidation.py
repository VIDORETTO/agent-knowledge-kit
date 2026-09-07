# seam-scope: implementation-infrastructure (main consolidation public seams)
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import docops


def test_lifecycle_facade_reports_one_versioned_public_status_without_private_paths(tmp_path: Path) -> None:
    package = tmp_path / "package"
    runtime = tmp_path / "runtime"

    facade = docops.LifecycleFacade(package, runtime_root=runtime)
    status = facade.status()

    assert status["schema_version"] == 1
    assert status["ok"] is True
    assert status["runtime"]["layout_version"] == 1
    assert status["runtime"]["status"] == "initialized"
    assert status["lifecycle"]["active"] == "absent"
    assert status["compatibility"]["cli"] == "expand-contract"
    serialized = json.dumps(status)
    assert str(runtime) not in serialized
    assert "sqlite" not in serialized.casefold()


def test_lifecycle_facade_rejects_unsupported_legacy_runtime_without_mutating_it(tmp_path: Path) -> None:
    package = tmp_path / "package"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    legacy = runtime / "runtime.json"
    legacy.write_text(json.dumps({"schema_version": 99, "layout_version": 1}), encoding="utf-8")

    facade = docops.LifecycleFacade(package, runtime_root=runtime)
    status = facade.status()

    assert status["ok"] is False
    assert status["code"] == "runtime_schema_unsupported"
    assert json.loads(legacy.read_text(encoding="utf-8"))["schema_version"] == 99


def test_lifecycle_facade_runs_through_the_existing_public_operation_seam(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "guide.md").write_text("# Guide\nFacade contract.\n", encoding="utf-8")
    package = tmp_path / "package"

    facade = docops.LifecycleFacade(package, runtime_root=tmp_path / "runtime")
    result = facade.run(
        source,
        options=docops.OperationOptions(output_dir=package, slug="guide", license="MIT"),
    )

    assert result.ok is True, result.errors
    status = facade.status()
    assert status["lifecycle"]["active"] == "valid"
    assert status["lifecycle"]["source"] == "materialized"


def test_lifecycle_facade_rejects_runtime_inside_active_generation(tmp_path: Path) -> None:
    package = tmp_path / "package"

    with pytest.raises(ValueError, match="outside"):
        docops.LifecycleFacade(package, runtime_root=package / ".docops-runtime")


def test_real_mcp_reader_configuration_does_not_bootstrap_writable_state(tmp_path: Path) -> None:
    vendor = Path(__file__).resolve().parents[1] / "skills" / "vendor" / "knowledge-rag"
    environment = dict(os.environ)
    environment.update(
        {
            "KNOWLEDGE_RAG_DIR": str(tmp_path),
            "KNOWLEDGE_RAG_READ_ONLY": "1",
            "PYTHONPATH": os.pathsep.join(value for value in (str(vendor), environment.get("PYTHONPATH", "")) if value),
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from mcp_server.config import config; print(json.dumps({'read_only': config.read_only}))",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    output_lines = (result.stdout + result.stderr).splitlines()
    assert output_lines, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert json.loads(output_lines[-1])["read_only"] is True
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "documents").exists()
    assert not (tmp_path / "models_cache").exists()


def test_real_mcp_reader_rejects_mutation_before_orchestrator_startup(tmp_path: Path) -> None:
    vendor = Path(__file__).resolve().parents[1] / "skills" / "vendor" / "knowledge-rag"
    environment = dict(os.environ)
    environment.update(
        {
            "KNOWLEDGE_RAG_DIR": str(tmp_path),
            "KNOWLEDGE_RAG_READ_ONLY": "1",
            "PYTHONPATH": os.pathsep.join(value for value in (str(vendor), environment.get("PYTHONPATH", "")) if value),
        }
    )

    result = subprocess.run(
        [
            str(
                next(
                    (
                        candidate
                        for candidate in (
                            Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "python.exe",
                            Path(sys.executable),
                        )
                        if candidate.exists()
                    )
                )
            ),
            "-c",
            "import json; from mcp_server.server import add_document; print(json.dumps(json.loads(add_document('safe', 'general/blocked.md'))))",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    output_lines = (result.stdout + result.stderr).splitlines()
    payload = json.loads(output_lines[-1])
    assert payload["status"] == "error"
    assert payload["code"] == "read_only_session"
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "documents").exists()


def test_runtime_environment_declares_reader_or_writer_capability(tmp_path: Path) -> None:
    from docops.runtime import runtime_environment

    reader = runtime_environment(tmp_path, read_only=True)
    writer = runtime_environment(tmp_path, read_only=False)

    assert reader["KNOWLEDGE_RAG_READ_ONLY"] == "1"
    assert writer["KNOWLEDGE_RAG_READ_ONLY"] == "0"


def test_harness_declares_the_reader_capability_boundary(tmp_path: Path) -> None:
    from docops.harness import build_harness_manifest

    manifest = build_harness_manifest(tmp_path)

    assert manifest["mcp"]["mode"] == "read_only"
    assert manifest["mcp"]["env"]["KNOWLEDGE_RAG_READ_ONLY"] == "1"
    assert manifest["mcp"]["write_capabilities"] == []


def test_harness_declares_one_canonical_generation_and_operator(tmp_path: Path) -> None:
    from docops.harness import build_harness_manifest
    from docops.revisions import package_revisions

    manifest = build_harness_manifest(tmp_path)
    generation = manifest["generation"]
    revisions = package_revisions(tmp_path)

    assert manifest["operator_skill"] == {"name": "docops-agent", "discovery": "docops skill path"}
    assert generation["schema_version"] == 1
    for key in (
        "release_id",
        "composition_hash",
        "corpus_revision",
        "index_revision",
        "skill_revision",
        "router_revision",
        "policy_revision",
    ):
        assert generation[key] == revisions[key]
    assert manifest["mcp"]["env"]["KNOWLEDGE_RAG_GENERATION"] == generation["release_id"]


def test_harness_rejects_generation_and_environment_drift(tmp_path: Path) -> None:
    from docops.harness import build_harness_manifest, read_harness_manifest

    manifest = build_harness_manifest(tmp_path)
    manifest["mcp"]["env"]["KNOWLEDGE_RAG_GENERATION"] = "release-drift"
    path = tmp_path / "harness.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="generation"):
        read_harness_manifest(path)


def test_harness_rejects_a_package_changed_after_generation_was_declared(tmp_path: Path) -> None:
    from docops.harness import build_harness_manifest, read_harness_manifest

    manifest = build_harness_manifest(tmp_path)
    manifest_path = tmp_path / "harness.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "skill").mkdir()
    (tmp_path / "skill" / "SKILL.md").write_text("# changed\n", encoding="utf-8")

    with pytest.raises(ValueError, match="generation"):
        read_harness_manifest(manifest_path)


def test_router_routes_persistent_changes_to_the_lifecycle() -> None:
    from docops.retrieval import route_query

    assert route_query("How do I update an admitted source?") == "lifecycle"
    assert route_query("What is the exact default version?") == "rag"
    assert route_query("Why is the exact default chosen this way?") == "both"


def test_generated_router_declares_precedence_authority_abstention_and_untrusted_content() -> None:
    from docops.generation import router_artifact

    router = router_artifact("fixture")
    normalized = router.casefold()

    for phrase in (
        "docops-agent",
        "conceptual",
        "literal",
        "persistent",
        "untrusted",
        "citation",
        "abstain",
        "divergence",
        "generation",
        "read-only",
    ):
        assert phrase in normalized


def test_agent_skill_is_discoverable_with_command_cards_and_harness_guidance() -> None:
    from docops.agent_skill import find_skill_root, skill_metadata

    root = find_skill_root()
    metadata = skill_metadata()

    assert metadata["name"] == "docops-agent"
    assert Path(metadata["path"]).resolve() == root
    assert (root / "SKILL.md").is_file()
    assert (root / "references" / "command-cards.md").is_file()
    assert (root / "references" / "skill-interoperability.md").is_file()
    assert (root / "references" / "scheduler-runbooks.md").is_file()


def test_agent_bootstrap_is_read_only_checkable_idempotent_and_preserves_rules(tmp_path: Path) -> None:
    from docops.agent_skill import install_agents_bootstrap

    target = tmp_path / "AGENTS.md"
    target.write_text("# Local rules\n\nKeep this instruction.\n", encoding="utf-8")

    missing = install_agents_bootstrap(tmp_path, check=True)
    first = install_agents_bootstrap(tmp_path)
    second = install_agents_bootstrap(tmp_path)
    content = target.read_text(encoding="utf-8")

    assert missing == {"ok": False, "changed": False, "status": "missing"}
    assert first["status"] == "installed"
    assert second == {"ok": True, "changed": False, "status": "present"}
    assert content.startswith("# Local rules")
    assert content.count("DOCOPS-PERSISTENT-KNOWLEDGE") == 1
    assert content.count("preservar proveniência") == 1


def test_agent_skill_discovery_rejects_incomplete_or_linked_roots(tmp_path: Path) -> None:
    from docops.agent_skill import find_skill_root, install_agents_bootstrap

    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    with pytest.raises(FileNotFoundError):
        find_skill_root(incomplete)

    project = tmp_path / "project"
    project.mkdir()
    try:
        project_link = tmp_path / "project-link"
        project_link.symlink_to(project, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ValueError, match="symbolic link"):
        install_agents_bootstrap(project_link)


def test_agent_skill_cli_exposes_discovery_and_bootstrap_modes(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    path_result = subprocess.run(
        [sys.executable, "-m", "docops", "skill", "path", "--json"],
        check=False,
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert path_result.returncode == 0, path_result.stdout + path_result.stderr
    path_payload = json.loads(path_result.stdout)
    assert path_payload["name"] == "docops-agent"
    assert (Path(path_payload["path"]) / "SKILL.md").is_file()

    check_result = subprocess.run(
        [sys.executable, "-m", "docops", "agents-bootstrap", "--root", str(tmp_path), "--check", "--json"],
        check=False,
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert check_result.returncode == 2
    assert json.loads(check_result.stdout)["status"] == "missing"


def test_cli_exposes_a_canonical_lifecycle_hierarchy_and_explicit_legacy_map() -> None:
    from docops.__main__ import CLI_COMPATIBILITY_MAP

    assert CLI_COMPATIBILITY_MAP["source-register"] == "lifecycle source register"
    assert CLI_COMPATIBILITY_MAP["candidate-approve"] == "lifecycle candidate approve"
    assert CLI_COMPATIBILITY_MAP["reader-query"] == "lifecycle reader query"
    assert CLI_COMPATIBILITY_MAP["feedback-report"] == "lifecycle feedback report"

    root_help = subprocess.run(
        [sys.executable, "-m", "docops", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert root_help.returncode == 0
    assert "lifecycle" in root_help.stdout
    assert "temporary compatibility" in root_help.stdout.casefold()

    lifecycle_help = subprocess.run(
        [sys.executable, "-m", "docops", "lifecycle", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert lifecycle_help.returncode == 0
    assert {"source", "candidate", "reader", "learning", "feedback"}.issubset(lifecycle_help.stdout.casefold().split())


def test_canonical_and_flat_source_commands_have_the_same_json_contract(tmp_path: Path) -> None:
    flat = subprocess.run(
        [
            sys.executable,
            "-m",
            "docops",
            "source-register",
            "--package",
            str(tmp_path / "package"),
            "--source-id",
            "docs-main",
            "--canonical",
            "https://example.test/docs",
            "--owner",
            "operator",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    canonical = subprocess.run(
        [
            sys.executable,
            "-m",
            "docops",
            "lifecycle",
            "source",
            "register",
            "--package",
            str(tmp_path / "package"),
            "--source-id",
            "docs-main",
            "--canonical",
            "https://example.test/docs",
            "--owner",
            "operator",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert flat.returncode == canonical.returncode == 0, flat.stdout + flat.stderr + canonical.stdout + canonical.stderr
    assert json.loads(flat.stdout) == json.loads(canonical.stdout)
    assert canonical.stderr == ""


def test_lifecycle_status_canonical_alias_has_no_deprecation_in_json(tmp_path: Path) -> None:
    canonical = subprocess.run(
        [
            sys.executable,
            "-m",
            "docops",
            "lifecycle",
            "status",
            "--package",
            str(tmp_path / "package"),
            "--runtime-root",
            str(tmp_path / "runtime"),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert canonical.returncode == 0, canonical.stdout + canonical.stderr
    payload = json.loads(canonical.stdout)
    assert payload["compatibility"]["cli"] == "expand-contract"
    assert "deprecat" not in canonical.stdout.casefold()


def test_real_mcp_reader_rejects_every_writer_tool(tmp_path: Path) -> None:
    vendor = Path(__file__).resolve().parents[1] / "skills" / "vendor" / "knowledge-rag"
    environment = dict(os.environ)
    environment.update(
        {
            "KNOWLEDGE_RAG_DIR": str(tmp_path),
            "KNOWLEDGE_RAG_READ_ONLY": "1",
            "PYTHONPATH": os.pathsep.join(value for value in (str(vendor), environment.get("PYTHONPATH", "")) if value),
        }
    )
    script = (
        "import json; from mcp_server.server import add_document, update_document, remove_document, "
        "add_from_url, reindex_documents; print(json.dumps({name: json.loads(call()) for name, call in {"
        "'add_document': lambda: add_document('safe', 'general/blocked.md'), "
        "'update_document': lambda: update_document('general/blocked.md', 'safe'), "
        "'remove_document': lambda: remove_document('general/blocked.md'), "
        "'add_from_url': lambda: add_from_url('https://example.invalid'), "
        "'reindex_documents': lambda: reindex_documents()}.items()}))"
    )
    executable = next(
        candidate
        for candidate in (
            Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "python.exe",
            Path(sys.executable),
        )
        if candidate.exists()
    )

    result = subprocess.run(
        [str(executable), "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads((result.stdout + result.stderr).splitlines()[-1])
    assert {item["code"] for item in payload.values()} == {"read_only_session"}
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "documents").exists()


def test_real_mcp_reader_process_starts_without_bootstrap_or_watcher(tmp_path: Path) -> None:
    from docops.mcp_client import first_json_payload, start_mcp_server
    from docops.runtime import runtime_environment

    root = Path(__file__).resolve().parents[1]
    vendor = root / "skills" / "vendor" / "knowledge-rag"
    executable = next(
        candidate
        for candidate in (root / ".venv" / "Scripts" / "python.exe", Path(sys.executable))
        if candidate.exists()
    )
    writer_environment = runtime_environment(tmp_path, vendor_root=vendor, read_only=False)
    setup = subprocess.run(
        [
            str(executable),
            "-c",
            "import chromadb; from mcp_server.server import FastEmbedEmbeddings; "
            "client=chromadb.PersistentClient(path='data/chroma_db'); "
            "client.get_or_create_collection(name='knowledge_base', embedding_function=FastEmbedEmbeddings())",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**writer_environment, "PYTHONDONTWRITEBYTECODE": "1"},
        cwd=tmp_path,
    )
    assert setup.returncode == 0, setup.stdout + setup.stderr
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())

    reader_environment = runtime_environment(tmp_path, vendor_root=vendor, read_only=True)
    reader_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    client = None
    try:
        client = start_mcp_server(executable, tmp_path, env=reader_environment)
        listed = client.call("tools/list", timeout=30)
        assert not listed.get("error"), listed
        names = {tool.get("name") for tool in listed.get("result", {}).get("tools", []) if isinstance(tool, dict)}
        assert {"search_knowledge", "get_document"}.issubset(names)

        denied = client.call(
            "tools/call",
            name="add_document",
            arguments={"content": "safe", "filepath": "general/blocked.md"},
            timeout=30,
        )
        payload = first_json_payload(denied)
        assert payload == {
            "status": "error",
            "code": "read_only_session",
            "message": "this MCP session is query-only; use a maintenance worker to mutate the index",
        }
    finally:
        if client is not None:
            client.close()

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file())
    assert after == before


def test_real_mcp_reader_hides_revoked_document_before_reading_it(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    vendor = root / "skills" / "vendor" / "knowledge-rag"
    tombstone = tmp_path / ".docops" / "revocations.json"
    tombstone.parent.mkdir()
    tombstone.write_text(
        json.dumps({"sources": [{"destinations": ["general/revoked.md"]}]}),
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment.update(
        {
            "KNOWLEDGE_RAG_DIR": str(tmp_path),
            "KNOWLEDGE_RAG_READ_ONLY": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join(value for value in (str(vendor), environment.get("PYTHONPATH", "")) if value),
        }
    )
    executable = next(
        candidate
        for candidate in (root / ".venv" / "Scripts" / "python.exe", Path(sys.executable))
        if candidate.exists()
    )
    result = subprocess.run(
        [
            str(executable),
            "-c",
            "import json; from mcp_server.server import get_document; "
            "print(json.dumps(json.loads(get_document('general/revoked.md'))))",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads((result.stdout + result.stderr).splitlines()[-1])
    assert payload["code"] == "source_revoked"
    assert not (tmp_path / "data").exists()
