"""Тесты хендлеров: приветствие и AI-ответы."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from vkbottle import VKAPIError

import config
import handlers.chat as chat
import handlers.greeting as greeting
from ai import AIClientError


class FakeUsersAPI:
    def __init__(self, first_name: str = "Мария", error: Exception | None = None):
        self.first_name = first_name
        self.error = error
        self.calls: list = []

    async def get(self, *, user_ids=None, **kwargs):
        self.calls.append(user_ids)
        if self.error is not None:
            raise self.error
        return [SimpleNamespace(first_name=self.first_name)]


class FakeMessage:
    """Минимальный duck-typed аналог Message для вызова хендлеров."""

    def __init__(
        self,
        *,
        text: str = "",
        peer_id: int = 7,
        from_id: int = 7,
        group_id: int = 100,
        action: SimpleNamespace | None = None,
        users: FakeUsersAPI | None = None,
    ):
        self.text = text
        self.peer_id = peer_id
        self.from_id = from_id
        self.group_id = group_id
        self.action = action
        self.ctx_api = SimpleNamespace(users=users or FakeUsersAPI())
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:  # noqa: ARG002
        self.answers.append(text)


def _set_env(monkeypatch) -> None:
    monkeypatch.setenv("VK_TOKEN", "vk-token")
    monkeypatch.setenv("PROXYAPI_API_KEY", "sk-test")


# ---------------------------------------------------------------- приветствие


def test_greeting_uses_member_name(monkeypatch) -> None:
    _set_env(monkeypatch)
    monkeypatch.setenv("GREETING_TEXT", "Добро пожаловать, {name}!")

    users = FakeUsersAPI(first_name="Мария")
    message = FakeMessage(
        peer_id=2000000001,
        from_id=1,
        action=SimpleNamespace(member_id=42),
        users=users,
    )

    asyncio.run(greeting.greet_new_member(message))

    assert users.calls == [[42]]
    assert message.answers == ["Добро пожаловать, Мария!"]


def test_greeting_falls_back_when_profile_unavailable(monkeypatch) -> None:
    _set_env(monkeypatch)
    monkeypatch.setenv("GREETING_TEXT", "Привет, {name}!")

    users = FakeUsersAPI(error=VKAPIError[901](error_msg="Access denied"))
    message = FakeMessage(
        peer_id=2000000001,
        from_id=1,
        action=SimpleNamespace(member_id=42),
        users=users,
    )

    asyncio.run(greeting.greet_new_member(message))

    assert message.answers == ["Привет, друг!"]


def test_greeting_when_bot_itself_added(monkeypatch) -> None:
    _set_env(monkeypatch)
    monkeypatch.setenv("BOT_GREETING_TEXT", "Бот в беседе.")

    message = FakeMessage(
        peer_id=2000000001,
        from_id=1,
        action=SimpleNamespace(member_id=-100),  # group_id = 100
    )

    asyncio.run(greeting.greet_new_member(message))

    assert message.answers == ["Бот в беседе."]
    assert message.ctx_api.users.calls == []  # профиль не запрашивали


def test_greeting_skips_other_communities(monkeypatch) -> None:
    _set_env(monkeypatch)

    message = FakeMessage(
        peer_id=2000000001,
        from_id=1,
        action=SimpleNamespace(member_id=-555),
    )

    asyncio.run(greeting.greet_new_member(message))

    assert message.answers == []


def test_greeting_skips_message_without_action(monkeypatch) -> None:
    _set_env(monkeypatch)

    message = FakeMessage(peer_id=2000000001, from_id=1, action=None)

    asyncio.run(greeting.greet_new_member(message))

    assert message.answers == []


# ----------------------------------------------------------------- AI-ответы


def test_ai_reply_builds_history_across_turns(monkeypatch) -> None:
    _set_env(monkeypatch)

    client = config.get_ai_client()
    calls: list[list[dict]] = []

    async def fake_ask(messages):
        calls.append(list(messages))
        return f"ответ {len(calls)}"

    monkeypatch.setattr(client, "ask", fake_ask)

    first = FakeMessage(text="привет", peer_id=7, from_id=7)
    asyncio.run(chat._reply_with_ai(first))

    second = FakeMessage(text="а кто ты?", peer_id=7, from_id=7)
    asyncio.run(chat._reply_with_ai(second))

    assert first.answers == ["ответ 1"]
    assert second.answers == ["ответ 2"]

    # в запрос второй раз ушла вся предыдущая переписка
    assert calls[0] == [{"role": "user", "content": "привет"}]
    assert calls[1] == [
        {"role": "user", "content": "привет"},
        {"role": "assistant", "content": "ответ 1"},
        {"role": "user", "content": "а кто ты?"},
    ]

    history = config.get_history()
    assert len(history.get(history.make_key(7, 7))) == 4


def test_ai_reply_is_isolated_per_user(monkeypatch) -> None:
    _set_env(monkeypatch)

    client = config.get_ai_client()
    seen: list[list[dict]] = []

    async def fake_ask(messages):
        seen.append(list(messages))
        return "ок"

    monkeypatch.setattr(client, "ask", fake_ask)

    asyncio.run(chat._reply_with_ai(FakeMessage(text="привет", peer_id=2000000001, from_id=1)))
    asyncio.run(chat._reply_with_ai(FakeMessage(text="и мне", peer_id=2000000001, from_id=2)))

    assert [m["content"] for m in seen[0]] == ["привет"]
    assert [m["content"] for m in seen[1]] == ["и мне"]


def test_empty_message_gets_hint_instead_of_ai_call(monkeypatch) -> None:
    _set_env(monkeypatch)

    client = config.get_ai_client()

    async def fake_ask(messages):  # noqa: ARG001
        raise AssertionError("AI не должен вызываться")

    monkeypatch.setattr(client, "ask", fake_ask)

    message = FakeMessage(text="   ", peer_id=7, from_id=7)
    asyncio.run(chat._reply_with_ai(message))

    assert message.answers == [chat.EMPTY_TEXT_HINT]
    assert len(config.get_history()) == 0


def test_ai_error_rolls_back_and_answers_user(monkeypatch) -> None:
    _set_env(monkeypatch)

    client = config.get_ai_client()

    async def fake_ask(messages):  # noqa: ARG001
        raise AIClientError("нет связи", status=None)

    monkeypatch.setattr(client, "ask", fake_ask)

    message = FakeMessage(text="привет", peer_id=7, from_id=7)
    asyncio.run(chat._reply_with_ai(message))

    assert message.answers == [chat.AI_FAILED_TEXT]
    # реплика откатилась, история не засорилась
    history = config.get_history()
    assert history.get(history.make_key(7, 7)) == []


def test_chat_labeler_rules(monkeypatch) -> None:
    """Хендлеры AI заведомо отфильтрованы: ЛС всегда, беседа — по упоминанию."""
    _set_env(monkeypatch)
    from handlers import chat_labeler

    handlers = chat_labeler.message_view.handlers
    assert len(handlers) == 2
    # auto_rules вшиты в хендлеры при декорировании
    assert any("FromUserRule" in str(h.rules) for h in handlers)
