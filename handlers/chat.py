"""Ответы на входящие сообщения с помощью AI."""

from __future__ import annotations

import logging

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules.base import FromUserRule, MentionRule

from ai import AIClientError
from config import get_ai_client, get_history
from content import menu_label
from handlers.menu import has_payload, is_menu_command, is_welcomed, show_menu
from keyboards import menu_short_keyboard

logger = logging.getLogger(__name__)

bl = BotLabeler()
# Вшивается в хендлеры при декорировании: игнорируем сообщения от ботов
bl.auto_rules = [FromUserRule()]

EMPTY_TEXT_HINT = "Кажется, сообщение пустое. Напишите текст — и я отвечу."
AI_FAILED_TEXT = "Не получилось получить ответ от AI. Попробуйте ещё раз чуть позже."

# peer_id личного сообщения; в беседах клавиатуру показывать нельзя
PRIVATE_PEER_LIMIT = 2_000_000_000


def _is_free_text(message: Message) -> bool:
    """Сообщение не от кнопки и не команда меню — его обрабатывает AI."""
    return not has_payload(message) and not is_menu_command(message)


def _menu_keyboard_for(peer_id: int) -> str | None:
    """Кнопка «Меню» под ответом AI — только в личных сообщениях."""
    if peer_id >= PRIVATE_PEER_LIMIT:
        return None
    return menu_short_keyboard(menu_label())


async def _reply_with_ai(message: Message) -> None:
    """Собрать контекст, спросить модель и отправить ответ."""
    if has_payload(message):
        # Нажатие кнопки: экраном займётся лейблер меню
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer(EMPTY_TEXT_HINT, keyboard=_menu_keyboard_for(message.peer_id))
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
        await message.answer(AI_FAILED_TEXT, keyboard=_menu_keyboard_for(message.peer_id))
        return

    history.add(key, "assistant", reply)
    await message.answer(reply, keyboard=_menu_keyboard_for(message.peer_id))


@bl.private_message(func=_is_free_text)
async def private_message_handler(message: Message) -> None:
    """В личных сообщениях: первое — приветствие с меню, дальше отвечает AI."""
    if not is_welcomed(message.peer_id):
        # Первое сообщение: show_menu сам отметит peer и отправит приветствие
        await show_menu(message)
        return
    await _reply_with_ai(message)



@bl.chat_message(MentionRule(mention_only=False), func=_is_free_text)
async def chat_message_handler(message: Message) -> None:
    """В беседе отвечаем только на упоминание бота.

    ``replace_mention=True`` на view уже вырезал ``[club123|Имя]``
    из ``message.text``, поэтому модель видит чистый вопрос.
    """
    await _reply_with_ai(message)
