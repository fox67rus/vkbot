"""Тесты загрузки конфигурации из .env."""

from __future__ import annotations

import pytest

import config


def _set_required(monkeypatch) -> None:
    monkeypatch.setenv("VK_TOKEN", " vk-token ")
    monkeypatch.setenv("PROXYAPI_API_KEY", " sk-test ")


def test_missing_required_vars(monkeypatch) -> None:
    with pytest.raises(config.ConfigError) as exc:
        config.load_settings()

    message = str(exc.value)
    assert "VK_TOKEN" in message
    assert "PROXYAPI_API_KEY" in message
    assert str(config.ENV_PATH) in message


def test_defaults_match_plan(monkeypatch) -> None:
    _set_required(monkeypatch)
    settings = config.load_settings()

    assert settings.vk_token == "vk-token"  # пробелы обрезаны
    assert settings.proxyapi_api_key == "sk-test"
    assert settings.proxyapi_base_url == "https://api.proxyapi.ru/v1"
    assert settings.ai_model == "openai/gpt-5.4-mini"
    assert settings.ai_system_prompt  # не пустой
    assert settings.ai_temperature == 0.7
    assert settings.ai_max_tokens == 1000
    assert settings.ai_timeout == 60.0
    assert settings.ai_max_retries == 3
    assert settings.ai_history_pairs == 10
    assert "{name}" in settings.greeting_text
    assert settings.bot_greeting_text
    assert settings.log_level == "INFO"


def test_base_url_trailing_slash_removed(monkeypatch) -> None:
    _set_required(monkeypatch)
    monkeypatch.setenv("PROXYAPI_BASE_URL", "https://example.com/v1/")

    assert config.load_settings().proxyapi_base_url == "https://example.com/v1"


def test_empty_optional_params_are_disabled(monkeypatch) -> None:
    _set_required(monkeypatch)
    monkeypatch.setenv("AI_TEMPERATURE", "")
    monkeypatch.setenv("AI_MAX_TOKENS", "")
    monkeypatch.setenv("AI_SYSTEM_PROMPT", "")

    settings = config.load_settings()
    assert settings.ai_temperature is None
    assert settings.ai_max_tokens is None
    assert settings.ai_system_prompt == ""


def test_absent_optional_params_keep_defaults(monkeypatch) -> None:
    _set_required(monkeypatch)

    settings = config.load_settings()
    assert settings.ai_temperature == 0.7
    assert settings.ai_max_tokens == 1000


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("AI_TEMPERATURE", "hot"),
        ("AI_MAX_TOKENS", "10.5"),
        ("AI_TIMEOUT", "много"),
        ("AI_MAX_RETRIES", "0"),
        ("AI_HISTORY_PAIRS", "-1"),
    ],
)
def test_invalid_values_raise_config_error(monkeypatch, key, value) -> None:
    _set_required(monkeypatch)
    monkeypatch.setenv(key, value)

    with pytest.raises(config.ConfigError) as exc:
        config.load_settings()
    assert key in str(exc.value)


def test_settings_are_cached(monkeypatch) -> None:
    _set_required(monkeypatch)
    first = config.get_settings()

    monkeypatch.setenv("VK_TOKEN", "changed-later")
    assert config.get_settings() is first
    assert config.get_settings().vk_token == "vk-token"
