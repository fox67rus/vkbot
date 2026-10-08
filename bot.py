"""Точка входа: сборка бота и запуск LongPoll-клиента."""

from __future__ import annotations

import logging
import sys

from vkbottle import VKAPIError
from vkbottle.bot import Bot

from config import ConfigError, get_ai_client, get_settings
from content import ContentError, get_content
from handlers import chat_labeler, greeting_labeler, menu_labeler
from handlers.menu import content_services_count
from middlewares import MessageLogMiddleware

logger = logging.getLogger(__name__)


def setup_logging(level: str) -> None:
    """Настроить уровень логирования своего кода и vkbottle."""
    logging.basicConfig(
        level=level,
        format="%(levelname)-8s | %(asctime)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("vkbottle").setLevel(level)


def _register_error_handlers(bot: Bot) -> None:
    """Не позволять ошибкам VK/API ронять поллинг."""

    @bot.error_handler.register_error_handler(
        VKAPIError[901], VKAPIError[902], VKAPIError[903]
    )
    async def _messaging_forbidden(error: VKAPIError) -> None:
        # 901/903 — ЛС закрыты, 902 — превышен лимит отправки
        logger.warning("Не удалось отправить сообщение в VK (код %s): %s", error.code, error)

    @bot.error_handler.register_error_handler(VKAPIError)
    async def _vk_error(error: VKAPIError) -> None:
        logger.warning("Ошибка VK API (код %s): %s", error.code, error)

    @bot.error_handler.register_undefined_error_handler
    async def _unexpected(error: Exception) -> None:
        logger.error("Необработанная ошибка в обработчике: %s", error, exc_info=error)


def create_bot() -> Bot:
    """Собрать бота: правила, мидлвари, обработчики ошибок."""
    settings = get_settings()
    # Контент проверяем сразу: битый data/content.json должен всплыть при
    # старте, а не в первом же обработчике
    get_content()

    bot = Bot(token=settings.vk_token)

    # Без этого флага message.mention / is_mentioned не работают
    # и MentionRule никогда не срабатывает
    bot.labeler.message_view.replace_mention = True

    bot.labeler.load(greeting_labeler)
    # Меню — до AI-лейблера: сначала кнопки и команды, потом текстовый фоллбэк
    bot.labeler.load(menu_labeler)
    bot.labeler.load(chat_labeler)
    bot.labeler.message_view.register_middleware(MessageLogMiddleware)

    _register_error_handlers(bot)

    # Закрыть HTTP-сессию клиента AI при остановке
    bot.on_shutdown.append(get_ai_client().close())

    return bot


def main() -> int:
    try:
        settings = get_settings()
        get_content()
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 1
    except ContentError as exc:
        print(f"Ошибка контента: {exc}", file=sys.stderr)
        return 1

    setup_logging(settings.log_level)
    logger.info("Запуск бота (модель AI: %s)", settings.ai_model)
    logger.info("Контент загружен: услуг — %s", content_services_count())

    bot = create_bot()
    bot.run()  # LongPoll, блокирующий вызов
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
