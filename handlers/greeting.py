"""Приветствие новых участников беседы."""

from __future__ import annotations

import logging

from vkbottle import VKAPIError
from vkbottle.bot import BotLabeler, Message

from config import get_settings

logger = logging.getLogger(__name__)

bl = BotLabeler()

# Все события "в беседу вошёл участник"
GREETING_ACTIONS = [
    "chat_invite_user",
    "chat_invite_user_by_link",
    "chat_invite_user_by_message_request",
]


async def _member_first_name(message: Message, member_id: int) -> str | None:
    """Имя вошедшего участника или None, если VK не отдал профиль."""
    try:
        users = await message.ctx_api.users.get(user_ids=[member_id])
    except VKAPIError as exc:
        logger.warning("Не удалось получить профиль %s: %s", member_id, exc)
        return None
    if not users:
        return None
    return users[0].first_name


@bl.chat_message(action=GREETING_ACTIONS)
async def greet_new_member(message: Message) -> None:
    """Ответить на вступление участника (или самого бота) в беседу."""
    action = message.action
    if action is None or action.member_id is None:
        return

    settings = get_settings()
    member_id = action.member_id

    # В беседу добавили самого бота
    if message.group_id is not None and member_id == -message.group_id:
        await message.answer(settings.bot_greeting_text)
        return

    # Другие сообщества не приветствуем
    if member_id <= 0:
        return

    name = await _member_first_name(message, member_id) or "друг"
    await message.answer(settings.greeting_text.replace("{name}", name))
