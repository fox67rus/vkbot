"""Конфигурация бота: чтение .env и создание общих объектов.

Модуль является composition root: хендлеры импортируют отсюда
``get_settings``, ``get_ai_client`` и ``get_history``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

DEFAULT_BASE_URL = "https://api.proxyapi.ru/v1"
DEFAULT_MODEL = "openai/gpt-5.4-mini"
DEFAULT_SYSTEM_PROMPT = (
    "Ты полезный ассистент в ВК-сообществе. "
    "Отвечай кратко, по-русски, без markdown-разметки."
)
DEFAULT_GREETING = "Привет, {name}! Рады видеть тебя в беседе."
DEFAULT_BOT_GREETING = (
    "Бот подключён к беседе. Напишите мне в личные сообщения "
    "или упомяните здесь — и я отвечу с помощью AI."
)


class ConfigError(RuntimeError):
    """Отсутствует обязательная переменная окружения или она некорректна."""


@dataclass(frozen=True)
class Settings:
    vk_token: str
    proxyapi_api_key: str
    proxyapi_base_url: str
    ai_model: str
    ai_system_prompt: str
    ai_temperature: float | None
    ai_max_tokens: int | None
    ai_timeout: float
    ai_max_retries: int
    ai_history_pairs: int
    greeting_text: str
    bot_greeting_text: str
    log_level: str


def _required(name: str, missing: list[str]) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        missing.append(name)
    return value


def _text(name: str, default: str, *, allow_empty: bool = False) -> str:
    """Строка: отсутствие переменной -> значение по умолчанию.

    ``allow_empty=True`` позволяет явно задать пустую строку
    (например, чтобы обойтись без системного промпта).
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw and not allow_empty:
        return default
    return raw


def _optional_float(name: str, default: float) -> float | None:
    """Число; переменная, заданная пустой строкой, означает «не отправлять параметр»."""
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должен быть числом, получено {raw!r}") from exc


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должен быть целым числом, получено {raw!r}") from exc
    if value < 1:
        raise ConfigError(f"{name} должен быть больше нуля, получено {value}")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должен быть числом, получено {raw!r}") from exc
    if value <= 0:
        raise ConfigError(f"{name} должен быть больше нуля, получено {value}")
    return value


def _optional_int(name: str, default: int) -> int | None:
    """Целое; переменная, заданная пустой строкой, означает «не отправлять параметр»."""
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должен быть целым числом, получено {raw!r}") from exc


def load_settings() -> Settings:
    """Прочитать ``.env`` и вернуть настройки.

    Вызывать нужно до импорта хендлеров: они читают настройки лениво,
    поэтому порядок безопасен, а ошибки всплывают как можно раньше.
    """
    load_dotenv(ENV_PATH)

    missing: list[str] = []
    vk_token = _required("VK_TOKEN", missing)
    api_key = _required("PROXYAPI_API_KEY", missing)
    if missing:
        raise ConfigError(
            "Не заданы обязательные переменные в {path}: {names}. "
            "Скопируйте .env.example в .env и заполните их.".format(
                path=ENV_PATH, names=", ".join(missing)
            )
        )

    return Settings(
        vk_token=vk_token,
        proxyapi_api_key=api_key,
        proxyapi_base_url=_text("PROXYAPI_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        ai_model=_text("AI_MODEL", DEFAULT_MODEL),
        ai_system_prompt=_text(
            "AI_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT, allow_empty=True
        ),
        ai_temperature=_optional_float("AI_TEMPERATURE", 0.7),
        ai_max_tokens=_optional_int("AI_MAX_TOKENS", 1000),
        ai_timeout=_positive_float("AI_TIMEOUT", 60.0),
        ai_max_retries=_positive_int("AI_MAX_RETRIES", 3),
        ai_history_pairs=_positive_int("AI_HISTORY_PAIRS", 10),
        greeting_text=_text("GREETING_TEXT", DEFAULT_GREETING),
        bot_greeting_text=_text("BOT_GREETING_TEXT", DEFAULT_BOT_GREETING),
        log_level=_text("LOG_LEVEL", "INFO").upper(),
    )


_settings: Settings | None = None
_ai_client = None
_history = None


def get_settings() -> Settings:
    """Настройки из .env (кэшируются после первого чтения)."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def get_ai_client():
    """Единственный экземпляр клиента ProxyAPI."""
    global _ai_client
    if _ai_client is None:
        from ai import ProxyAIClient

        settings = get_settings()
        _ai_client = ProxyAIClient(
            api_key=settings.proxyapi_api_key,
            base_url=settings.proxyapi_base_url,
            model=settings.ai_model,
            system_prompt=settings.ai_system_prompt,
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens,
            timeout=settings.ai_timeout,
            max_retries=settings.ai_max_retries,
        )
    return _ai_client


def get_history():
    """Единственный экземпляр истории диалогов."""
    global _history
    if _history is None:
        from history import DialogHistory

        _history = DialogHistory(max_messages=get_settings().ai_history_pairs * 2)
    return _history
