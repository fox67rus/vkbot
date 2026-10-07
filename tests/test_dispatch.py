"""Сквозной тест маршрутизации: какое событие какой хендлер получит."""

from __future__ import annotations

import asyncio

from helpers import make_message

CHAT = {"peer_id": 2000000001, "from_id": 1}
PRIVATE = {"peer_id": 7, "from_id": 7}


async def _all_pass(rules, message) -> bool:
    for rule in rules:
        if not await rule.check(message):
            return False
    return True


def matching_handlers(bot, message) -> list[str]:
    """Имена хендлеров, чьи правила все выполняются (как в реальном view)."""
    return sorted(
        handler.handler.__name__
        for handler in bot.labeler.message_view.handlers
        if asyncio.run(_all_pass(handler.rules, message))
    )


def test_private_message_routes_to_ai(built_bot) -> None:
    message = make_message(text="привет бот", **PRIVATE)

    assert matching_handlers(built_bot, message) == ["private_message_handler"]


def test_mentioned_chat_message_routes_to_ai(built_bot) -> None:
    message = make_message(text="[club100|Бот] привет, как дела?", **CHAT)

    assert matching_handlers(built_bot, message) == ["chat_message_handler"]


def test_unmentioned_chat_message_matches_nothing(built_bot) -> None:
    """Бот молчит, пока его не упомянули."""
    message = make_message(text="просто разговор участников", **CHAT)

    assert matching_handlers(built_bot, message) == []


def test_chat_invite_routes_to_greeting(built_bot) -> None:
    message = make_message(
        text="",
        action={"type": "chat_invite_user", "member_id": 42},
        **CHAT,
    )

    assert matching_handlers(built_bot, message) == ["greet_new_member"]


def test_chat_invite_by_link_routes_to_greeting(built_bot) -> None:
    message = make_message(
        text="",
        action={"type": "chat_invite_user_by_link", "member_id": 42},
        **CHAT,
    )

    assert matching_handlers(built_bot, message) == ["greet_new_member"]


def test_message_from_another_community_is_ignored(built_bot) -> None:
    """FromUserRule вшит в AI-хендлеры: чужие боты не триггерят ответ."""
    message = make_message(text="[club100|Бот] ответь", peer_id=2000000001, from_id=-555)

    assert matching_handlers(built_bot, message) == []


def test_exactly_one_handler_matches_per_event(built_bot) -> None:
    cases = [
        make_message(text="привет", **PRIVATE),
        make_message(text="[club100|Бот] привет", **CHAT),
        make_message(text="тишина", **CHAT),
        make_message(text="", action={"type": "chat_invite_user", "member_id": 42}, **CHAT),
    ]
    for message in cases:
        assert len(matching_handlers(built_bot, message)) <= 1
