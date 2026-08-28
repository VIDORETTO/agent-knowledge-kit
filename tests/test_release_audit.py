from __future__ import annotations

from pathlib import Path

from docops.release_audit import audit_release


def test_release_audit_rejects_prohibited_runtime_artifacts_and_secrets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("safe", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "index.bin").write_bytes(b"runtime")
    secret = "sk-" + "1234567890abcdef1234567890"
    (tmp_path / "config.yaml").write_text(f"api_key: {secret}\n", encoding="utf-8")

    result = audit_release(tmp_path)

    assert not result.ok
    codes = {finding["code"] for finding in result.findings}
    assert "prohibited_artifact" in codes
    assert "secret_like_value" in codes


def test_release_audit_accepts_synthetic_fixture_and_token_placeholder(tmp_path: Path) -> None:
    (tmp_path / "documents" / "fixtures").mkdir(parents=True)
    (tmp_path / "documents" / "fixtures" / "guide.md").write_text(
        "# Fixture\nUse a placeholder such as REPLACE_WITH_A_TOKEN.", encoding="utf-8"
    )
    (tmp_path / "config.example.yaml").write_text(
        'bearer_token: "REPLACE_WITH_A_RANDOM_TOKEN_OF_AT_LEAST_16_CHARACTERS"\n', encoding="utf-8"
    )

    result = audit_release(tmp_path)

    assert result.ok, result.findings


def test_release_audit_rejects_json_escaped_windows_author_paths(tmp_path: Path) -> None:
    escaped_path = "C:" + "\\\\" + "Users" + "\\\\" + "Author" + "\\\\" + "Documents" + "\\\\" + "docs"
    (tmp_path / "manifest.json").write_text(
        '{"source": "' + escaped_path + '"}',
        encoding="utf-8",
    )

    result = audit_release(tmp_path)

    assert not result.ok
    assert any(finding["code"] == "author_path" for finding in result.findings)
