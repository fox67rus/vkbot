"""Общие фикстуры: изолированный .env, быстрые ретраи, сборка бота."""

from __future__ import annotations

import asyncio

import pytest

import config
from ai import ProxyAIClient

ENV_KEYS = [
    "VK_TOKEN",
    "PROXYAPI_API_KEY",
    "PROXYAPI_BASE_URL",
    "AI_MODEL",
    "AI_SYSTEM_PROMPT",
    "AI_TEMPERATURE",
    "AI_MAX_TOKENS",
    "AI_TIMEOUT",
    "AI_MAX_RETRIES",
    "AI_HISTORY_PAIRS",
    "GREETING_TEXT",
    "BOT_GREETING_TEXT",
    "LOG_LEVEL",
]


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """Тесты не должны зависеть от настоящего .env и от друг друга."""
    # Несуществующий путь: load_dotenv ничего не подмешает
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / ".env")
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(config, "_settings", None)
    monkeypatch.setattr(config, "_ai_client", None)
    monkeypatch.setattr(config, "_history", None)


@pytest.fixture(autouse=True)
def instant_backoff(monkeypatch):
    """Убрать паузы backoff, чтобы ретраи в тестах были мгновенными."""

    async def _instant(attempt: int) -> None:  # noqa: ARG001
        return None

    monkeypatch.setattr(ProxyAIClient, "_sleep", staticmethod(_instant))


@pytest.fixture(autouse=True)
def restore_labelers():
    """``labeler.load()`` подменяет ``bl.message_view`` у общих лейблеров.

    В проде бот собирается один раз, а в тестах это ломало бы порядок
    файлов — поэтому возвращаем исходные view после каждого теста.
    """
    from handlers import chat_labeler, greeting_labeler

    saved = [
        (labeler, labeler.message_view, labeler.raw_event_view)
        for labeler in (greeting_labeler, chat_labeler)
    ]
    yield
    for labeler, message_view, raw_event_view in saved:
        labeler.message_view = message_view
        labeler.raw_event_view = raw_event_view


@pytest.fixture
def built_bot(monkeypatch, isolated_env, restore_labelers):
    """Собранный бот с фиктивными ключами; сессия AI закрывается на выходе."""
    import bot as bot_module

    monkeypatch.setenv("VK_TOKEN", "vk-token")
    monkeypatch.setenv("PROXYAPI_API_KEY", "sk-test")
    bot = bot_module.create_bot()

    async def drain_shutdown() -> None:
        for coro in bot.on_shutdown:
            await coro

    yield bot
    asyncio.run(drain_shutdown())
