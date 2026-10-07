"""Ответы на входящие сообщения с помощью AI."""

from __future__ import annotations

import logging

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules.base import FromUserRule, MentionRule

from ai import AIClientError
from config import get_ai_client, get_history

logger = logging.getLogger(__name__)

bl = BotLabeler()
# Вшивается в хендлеры при декорировании: игнорируем сообщения от ботов
bl.auto_rules = [FromUserRule()]

EMPTY_TEXT_HINT = "Кажется, сообщение пустое. Напишите текст — и я отвечу."
AI_FAILED_TEXT = "Не получилось получить ответ от AI. Попробуйте ещё раз чуть позже."


async def _reply_with_ai(message: Message) -> None:
    """Собрать контекст, спросить модель и отправить ответ."""
    text = (message.text or "").strip()
    if not text:
        await message.answer(EMPTY_TEXT_HINT)
        return

    history = get_history()
    client = get_ai_client()
    key = history.make_key(message.peer_id, message.from_id)

    history.add(key, "user", text)
    try:
        reply = await client.ask(history.get(key))
    except AIClientError as exc:
        # Откатываем реплику, чтобы не копить "висящие" вопросы
        history.pop(key)
        logger.warning("Ошибка AI (peer=%s, from=%s): %s", key[0], key[1], exc)
        await message.answer(AI_FAILED_TEXT)
        return

    history.add(key, "assistant", reply)
    await message.answer(reply)


@bl.private_message()
async def private_message_handler(message: Message) -> None:
    """В личных сообщениях отвечаем на любое сообщение."""
    await _reply_with_ai(message)


@bl.chat_message(MentionRule(mention_only=False))
async def chat_message_handler(message: Message) -> None:
    """В беседе отвечаем только на упоминание бота.

    ``replace_mention=True`` на view уже вырезал ``[club123|Имя]``
    из ``message.text``, поэтому модель видит чистый вопрос.
    """
    await _reply_with_ai(message)
