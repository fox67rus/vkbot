"""Тесты правил vkbottle на синтетических сообщениях."""

from __future__ import annotations

from vkbottle.dispatch.rules.base import ChatActionRule, FromUserRule, MentionRule

from helpers import check, make_message

CHAT = {"peer_id": 2000000001, "from_id": 1}
PRIVATE = {"peer_id": 7, "from_id": 7}


def test_mention_stripped_from_text_and_rule_fires() -> None:
    message = make_message(text="[club100|Бот] привет, как дела?", **CHAT)

    # replace_mention=True вырезал упоминание до правил
    assert message.text == "привет, как дела?"
    assert message.mention is not None and message.mention.id == -100
    assert message.is_mentioned is True
    assert check(MentionRule(mention_only=False), message) is True


def test_mention_rule_ignores_regular_chat_message() -> None:
    message = make_message(text="просто сообщение", **CHAT)

    assert message.is_mentioned is False
    assert check(MentionRule(mention_only=False), message) is False
    # правило по умолчанию тоже не срабатывает
    assert check(MentionRule(), message) is False


def test_mention_rule_never_fires_in_private_messages() -> None:
    message = make_message(text="привет бот", **PRIVATE)

    assert message.peer_id == message.from_id
    assert message.is_mentioned is False
    assert check(MentionRule(mention_only=False), message) is False


def test_default_mention_rule_catches_only_bare_mention() -> None:
    bare = make_message(text="[club100|Бот]", **CHAT)
    with_text = make_message(text="[club100|Бот] привет", **CHAT)

    assert bare.text.strip() == ""
    assert check(MentionRule(), bare) is True
    # с текстом по умолчанию не срабатывает — поэтому нам нужен mention_only=False
    assert check(MentionRule(), with_text) is False
    assert check(MentionRule(mention_only=False), with_text) is True


def test_mention_of_another_group_does_not_fire() -> None:
    message = make_message(text="[club555|Чужой] привет", **CHAT)

    assert message.mention is not None and message.mention.id == -555
    assert message.is_mentioned is False
    assert check(MentionRule(mention_only=False), message) is False


def test_mention_rule_ignored_when_replace_mention_disabled() -> None:
    message = make_message(
        text="[club100|Бот] привет", replace_mention=False, **CHAT
    )

    assert message.is_mentioned is False
    assert check(MentionRule(mention_only=False), message) is False


def test_chat_action_rule_matches_invite() -> None:
    message = make_message(
        text="",
        action={"type": "chat_invite_user", "member_id": 42},
        **CHAT,
    )

    assert check(ChatActionRule(["chat_invite_user"]), message) is True
    assert check(ChatActionRule("chat_invite_user"), message) is True
    assert check(ChatActionRule("chat_kick_user"), message) is False
    assert message.action.member_id == 42


def test_chat_action_rule_ignores_ordinary_message() -> None:
    message = make_message(text="привет", **CHAT)

    assert check(ChatActionRule(["chat_invite_user"]), message) is False


def test_from_user_rule() -> None:
    from_user = make_message(text="привет", **PRIVATE)
    from_group = make_message(text="привет", peer_id=7, from_id=-100)

    assert check(FromUserRule(), from_user) is True
    assert check(FromUserRule(), from_group) is False
