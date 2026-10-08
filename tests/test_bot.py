"""Тесты сборки бота (самый последний шаг конфигурации)."""

from __future__ import annotations

import pytest

import bot as bot_module
import config


def test_create_bot_wires_everything(built_bot) -> None:
    view = built_bot.labeler.message_view

    # Без этого флага MentionRule в беседе никогда не сработает
    assert view.replace_mention is True

    # приветствие + меню (9 обработчиков кнопок и команд) + ЛС + беседа
    assert len(view.handlers) == 12
    names = {handler.handler.__name__ for handler in view.handlers}
    assert names == {
        "greet_new_member",
        # меню: кнопки с payload
        "on_menu_button",
        "on_services_button",
        "on_service_button",
        "on_price_button",
        "on_manager_button",
        "on_about_button",
        "on_help_button",
        # меню: текстовые команды (ЛС и беседа)
        "on_alias_command",
        "on_chat_alias_command",
        # AI-ответы
        "private_message_handler",
        "chat_message_handler",
    }

    assert len(view.middlewares) == 1
    assert len(built_bot.error_handler.error_handlers) == 4  # 901/902/903 + общий
    assert built_bot.error_handler.undefined_error_handler is not None
    assert len(built_bot.on_shutdown) == 1


def test_menu_is_registered_before_ai(built_bot) -> None:
    """Кнопки и команды должны обрабатываться раньше текстового AI-фоллбэка."""
    names = [handler.handler.__name__ for handler in built_bot.labeler.message_view.handlers]

    assert names.index("on_menu_button") < names.index("private_message_handler")
    assert names.index("on_alias_command") < names.index("private_message_handler")
    assert names.index("on_chat_alias_command") < names.index("chat_message_handler")


def test_error_handlers_are_specific(built_bot) -> None:
    """Ошибки ЛС и лимитов отправки обрабатываются отдельно от прочих."""
    handlers = built_bot.error_handler.error_handlers

    assert any(error_type.__name__.endswith("_901") for error_type in handlers)
    assert any(error_type.__name__.endswith("_902") for error_type in handlers)
    assert any(error_type.__name__.endswith("_903") for error_type in handlers)


def test_create_bot_requires_config(monkeypatch) -> None:
    monkeypatch.delenv("VK_TOKEN", raising=False)
    monkeypatch.delenv("PROXYAPI_API_KEY", raising=False)

    with pytest.raises(config.ConfigError):
        bot_module.create_bot()


def test_main_fails_fast_without_config(monkeypatch, capsys) -> None:
    monkeypatch.delenv("VK_TOKEN", raising=False)
    monkeypatch.delenv("PROXYAPI_API_KEY", raising=False)

    assert bot_module.main() == 1

    captured = capsys.readouterr()
    assert "Ошибка конфигурации" in captured.err
    assert "VK_TOKEN" in captured.err
