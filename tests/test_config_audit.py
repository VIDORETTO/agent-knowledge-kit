from __future__ import annotations

from pathlib import Path

from docops.config_audit import audit_config, audit_config_file


def test_stdio_config_does_not_require_network_credentials() -> None:
    result = audit_config(
        {
            "server": {
                "transport": "stdio",
                "auth": {"bearer_token": ""},
                "rate_limit": {"enabled": False},
                "metrics": {"enabled": False},
                "logging": {"format": "text"},
            }
        }
    )

    assert result.ok, result.errors
    assert result.transport == "stdio"


def test_http_config_requires_auth_rate_limit_metrics_and_json_logging() -> None:
    result = audit_config(
        {
            "server": {
                "transport": "streamable-http",
                "auth": {"bearer_token": "short"},
                "rate_limit": {"enabled": False},
                "metrics": {"enabled": False},
                "logging": {"format": "text"},
            }
        }
    )

    assert not result.ok
    codes = {error["code"] for error in result.errors}
    assert {"network_auth_required", "network_rate_limit_required", "network_metrics_required", "network_json_logging_required"} <= codes


def test_config_file_audit_is_portable_and_does_not_return_secrets(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "server:\n"
        "  transport: streamable-http\n"
        "  auth:\n"
        "    bearer_token: 1234567890abcdef\n"
        "  rate_limit:\n"
        "    enabled: true\n"
        "  metrics:\n"
        "    enabled: true\n"
        "  logging:\n"
        "    format: json\n",
        encoding="utf-8",
    )

    result = audit_config_file(config)

    assert result.ok, result.errors
    assert "1234567890abcdef" not in result.to_json()
