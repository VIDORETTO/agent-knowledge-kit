from __future__ import annotations

import json

from scripts.run_ragflow_profile import main


def test_ragflow_profile_fails_closed_when_external_inputs_are_missing(monkeypatch, capsys) -> None:
    for name in (
        "DOCOPS_RAGFLOW_ENDPOINT",
        "DOCOPS_RAGFLOW_TOKEN",
        "DOCOPS_RAGFLOW_IMAGE_DIGEST",
        "DOCOPS_RAGFLOW_SDK_VERSION",
    ):
        monkeypatch.delenv(name, raising=False)

    assert main(["--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["reason"] == "missing_external_inputs"
    assert "DOCOPS_RAGFLOW_TOKEN" in payload["missing"]


def test_ragflow_profile_rejects_an_unpinned_image_before_importing_sdk(monkeypatch, capsys) -> None:
    monkeypatch.setenv("DOCOPS_RAGFLOW_ENDPOINT", "https://ragflow.example.test")
    monkeypatch.setenv("DOCOPS_RAGFLOW_TOKEN", "configured")
    monkeypatch.setenv("DOCOPS_RAGFLOW_IMAGE_DIGEST", "ragflow:0.27.2")
    monkeypatch.setenv("DOCOPS_RAGFLOW_SDK_VERSION", "0.27.2")

    assert main(["--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["reason"] == "image_digest_unpinned"
