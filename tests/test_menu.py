"""Тесты меню: экраны, клавиатуры, команды, связь с AI-веткой."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import content
import keyboards
import config
import handlers.chat as chat
import handlers.menu as menu
from vkbottle.dispatch.rules.base import MentionRule


class ScreenMessage:
    """Duck-typed аналог Message: текст, payload, запись ответов и клавиатур."""

    def __init__(
        self,
        text: str = "",
        peer_id: int = 7,
        from_id: int = 7,
        payload: dict | str | None = None,
    ):
        self.text = text
        self.peer_id = peer_id
        self.from_id = from_id
        self.payload = (
            payload if isinstance(payload, str) or payload is None
            else json.dumps(payload, ensure_ascii=False)
        )
        self.answers: list[str] = []
        self.keyboards: list[str | None] = []

    async def answer(self, text: str | None = None, **kwargs) -> None:
        self.answers.append(text)
        self.keyboards.append(kwargs.get("keyboard"))

    def get_payload_json(self):
        if self.payload is None:
            return None
        try:
            return json.loads(self.payload)
        except ValueError:
            return self.payload


def buttons_of(keyboard_json: str | None) -> list[dict]:
    """Все action кнопок клавиатуры (по строкам)."""
    if keyboard_json is None:
        return []
    data = json.loads(keyboard_json)
    return [button["action"] for row in data["buttons"] for button in row]


def payloads_of(keyboard_json: str | None) -> list[dict]:
    return [json.loads(action["payload"]) for action in buttons_of(keyboard_json)]


def run(coro) -> None:
    asyncio.run(coro)


def set_env(monkeypatch) -> None:
    """Минимальные ключи: AI-ветка не должна зависеть от настоящего .env."""
    monkeypatch.setenv("VK_TOKEN", "vk-token")
    monkeypatch.setenv("PROXYAPI_API_KEY", "sk-test")


# ------------------------------------------------------------------ главное меню


def test_menu_button_sends_welcome_with_keyboard() -> None:
    message = ScreenMessage(payload={"cmd": "menu"})

    run(menu.on_menu_button(message))

    assert message.answers == [content.welcome_text()]
    labels = [action["label"] for action in buttons_of(message.keyboards[0])]
    assert labels == [button["label"] for button in content.menu_buttons()]
    assert payloads_of(message.keyboards[0])[0] == {"cmd": "services"}


def test_menu_reopened_shows_title_instead_of_greeting() -> None:
    """«Назад»/«Меню» не должны каждый раз повторять «Здравствуйте!...»."""
    first = ScreenMessage(payload={"cmd": "menu"})
    run(menu.on_menu_button(first))
    assert first.answers == [content.welcome_text()]

    again = ScreenMessage(payload={"cmd": "menu"})
    run(menu.on_menu_button(again))

    assert again.answers == [content.menu_title()]
    assert "Здравствуйте" not in again.answers[0]
    # клавиатура при этом та же самая
    assert [b["label"] for b in buttons_of(again.keyboards[0])] == [
        b["label"] for b in buttons_of(first.keyboards[0])
    ]


def test_text_command_back_to_menu_uses_title_too() -> None:
    """Текстовая команда «меню» после приветствия тоже без повтора."""
    run(menu.on_alias_command(ScreenMessage(text="меню")))  # первое — приветствие

    second = ScreenMessage(text="меню")
    run(menu.on_alias_command(second))

    assert second.answers == [content.menu_title()]


def test_payload_is_json_string_as_vk_requires() -> None:
    """VK ждёт payload строкой — иначе кнопка не вернёт данные."""
    keyboard_json = keyboards.main_menu_keyboard(content.menu_buttons())

    for action in buttons_of(keyboard_json):
        assert isinstance(action["payload"], str)
        assert json.loads(action["payload"])["cmd"]


def test_main_menu_layout_two_per_row() -> None:
    buttons = content.menu_buttons()
    keyboard_json = keyboards.main_menu_keyboard(buttons)
    rows = json.loads(keyboard_json)["buttons"]

    assert len(rows) == (len(buttons) + 1) // 2
    assert sum(len(row) for row in rows) == len(buttons)


# ------------------------------------------------------------------- экраны


def test_services_screen_lists_every_service() -> None:
    message = ScreenMessage(payload={"cmd": "services"})

    run(menu.on_services_button(message))

    text = message.answers[0]
    for service in content.services_ordered():
        assert service["title"] in text
        assert service["price"] in text

    assert payloads_of(message.keyboards[0])[-1] == {"cmd": "menu"}
    service_ids = [p.get("id") for p in payloads_of(message.keyboards[0]) if p["cmd"] == "service"]
    assert service_ids == [service["id"] for service in content.services_ordered()]


def test_service_card_shows_description() -> None:
    message = ScreenMessage(payload={"cmd": "service", "id": "web"})

    run(menu.on_service_button(message))

    service = content.get_service("web")
    text = message.answers[0]
    assert service["title"] in text
    assert service["description"] in text
    assert service["price"] in text

    assert {"cmd": "services"} in payloads_of(message.keyboards[0])
    assert {"cmd": "menu"} in payloads_of(message.keyboards[0])


def test_unknown_service_falls_back_to_list() -> None:
    message = ScreenMessage(payload={"cmd": "service", "id": "nope"})

    run(menu.on_service_button(message))

    assert "в каталоге нет" in message.answers[0]
    service_ids = [p.get("id") for p in payloads_of(message.keyboards[0]) if p["cmd"] == "service"]
    assert "web" in service_ids


def test_price_screen_shows_all_prices() -> None:
    message = ScreenMessage(payload={"cmd": "price"})

    run(menu.on_price_button(message))

    text = message.answers[0]
    assert text.startswith(content.get_content()["price"]["header"])
    assert content.get_content()["price"]["footer"] in text
    assert len([p for p in payloads_of(message.keyboards[0])]) == 1  # только «Назад»


def test_manager_screen_offers_link_and_contacts() -> None:
    message = ScreenMessage(payload={"cmd": "manager"})

    run(menu.on_manager_button(message))

    text = message.answers[0]
    assert content.get_content()["manager"]["name"] in text
    assert content.get_content()["manager"]["phone"] in text

    link, label = content.manager_link()
    link_buttons = [a for a in buttons_of(message.keyboards[0]) if a["type"] == "open_link"]
    assert link_buttons == [{"type": "open_link", "link": link, "label": label}]


def test_manager_screen_without_link_has_no_open_link_button(monkeypatch) -> None:
    data = json.loads(json.dumps(content.get_content()))
    data["manager"].pop("link")
    data["manager"].pop("link_label")
    content.set_content(data)

    message = ScreenMessage(payload={"cmd": "manager"})
    run(menu.on_manager_button(message))

    assert not [a for a in buttons_of(message.keyboards[0]) if a["type"] == "open_link"]
    assert "Телефон:" in message.answers[0]


def test_static_screens_use_button_text() -> None:
    message = ScreenMessage(payload={"cmd": "about"})

    run(menu.on_about_button(message))

    assert message.answers[0] == content.static_text("about")
    assert {"cmd": "services"} in payloads_of(message.keyboards[0])


# ------------------------------------------------------- текстовые команды


def test_alias_command_opens_screen_in_private() -> None:
    message = ScreenMessage(text="  ЦЕНЫ ")

    run(menu.on_alias_command(message))

    assert message.answers[0] == content.price_text()
    assert message.keyboards[0] is not None  # в ЛС клавиатура прикрепляется


def test_alias_command_in_chat_has_no_keyboard() -> None:
    message = ScreenMessage(text="менеджер", peer_id=2000000001)

    run(menu.on_chat_alias_command(message))

    assert message.answers[0] == content.manager_text()
    assert message.keyboards[0] is None  # беседа: клавиатуры ВК не показывает


def test_chat_alias_requires_mention_and_command() -> None:
    from helpers import make_message

    handler = next(
        handler
        for handler in menu.bl.message_view.handlers
        if handler.handler.__name__ == "on_chat_alias_command"
    )
    assert any(isinstance(rule, MentionRule) for rule in handler.rules)

    async def all_rules_pass(message) -> bool:
        for rule in handler.rules:
            if not await rule.check(message):
                return False
        return True

    unmentioned = make_message(text="просто разговор", peer_id=2000000001)
    mentioned = make_message(text="[club100|Бот] услуги", peer_id=2000000001)
    mentioned_other = make_message(text="[club100|Бот] как погода?", peer_id=2000000001)

    assert not asyncio.run(all_rules_pass(unmentioned))
    assert asyncio.run(all_rules_pass(mentioned))
    assert not asyncio.run(all_rules_pass(mentioned_other))  # не команда меню


def test_free_text_is_not_a_command() -> None:
    assert not menu.is_menu_command(ScreenMessage(text="расскажи про погоду"))
    assert menu.is_menu_command(ScreenMessage(text="меню"))
    assert menu.is_menu_command(ScreenMessage(text="/start"))


# ------------------------------------------------- приветствие и AI-ветка


def test_welcome_marks_peer_only_once() -> None:
    assert menu.mark_welcomed(7) is True
    assert menu.mark_welcomed(7) is False
    menu.reset_welcomed()
    assert menu.mark_welcomed(7) is True


def test_first_private_message_shows_menu_instead_of_ai(monkeypatch) -> None:
    set_env(monkeypatch)
    client = config.get_ai_client()

    async def fail_ask(messages):  # noqa: ARG001
        raise AssertionError("AI не должен вызываться при первом сообщении")

    monkeypatch.setattr(client, "ask", fail_ask)

    message = ScreenMessage(text="привет")
    run(chat.private_message_handler(message))

    assert message.answers == [content.welcome_text()]
    assert {"cmd": "services"} in payloads_of(message.keyboards[0])


def test_second_message_goes_to_ai(monkeypatch) -> None:
    set_env(monkeypatch)
    client = config.get_ai_client()

    async def fake_ask(messages):  # noqa: ARG001
        return "ответ AI"

    monkeypatch.setattr(client, "ask", fake_ask)

    menu.mark_welcomed(7)
    message = ScreenMessage(text="что умеешь?")
    run(chat.private_message_handler(message))

    assert message.answers == ["ответ AI"]
    # под ответом AI — кнопка «Меню», чтобы меню было всегда под рукой
    assert payloads_of(message.keyboards[0]) == [{"cmd": "menu"}]


def test_ai_answer_has_no_keyboard_in_chat(monkeypatch) -> None:
    set_env(monkeypatch)
    client = config.get_ai_client()

    async def fake_ask(messages):  # noqa: ARG001
        return "ответ AI"

    monkeypatch.setattr(client, "ask", fake_ask)

    message = ScreenMessage(text="как дела?", peer_id=2000000001)
    run(chat._reply_with_ai(message))

    assert message.answers == ["ответ AI"]
    assert message.keyboards == [None]


def test_ai_ignores_button_payload(monkeypatch) -> None:
    set_env(monkeypatch)
    client = config.get_ai_client()

    async def fail_ask(messages):  # noqa: ARG001
        raise AssertionError("AI не должен вызываться на нажатие кнопки")

    monkeypatch.setattr(client, "ask", fail_ask)

    message = ScreenMessage(text="Услуги", payload={"cmd": "services"})
    run(chat._reply_with_ai(message))

    assert message.answers == []


# ---------------------------------------------------------------- payload


def test_get_payload_parses_string() -> None:
    message = SimpleNamespace(payload='{"cmd": "price"}')
    assert menu.get_payload(message) == {"cmd": "price"}


def test_get_payload_handles_missing_and_broken() -> None:
    assert menu.get_payload(SimpleNamespace(payload=None)) == {}
    assert menu.get_payload(SimpleNamespace(payload="не json")) == {}
    assert menu.get_payload(SimpleNamespace()) == {}


def test_get_payload_prefers_parser() -> None:
    message = SimpleNamespace(payload="x", get_payload_json=lambda: {"cmd": "menu"})
    assert menu.get_payload(message) == {"cmd": "menu"}


# -------------------------------------------------------------- клавиатуры


def test_services_keyboard_layout() -> None:
    services = content.services_ordered()
    keyboard_json = keyboards.services_keyboard(services, "🔙 Назад")
    rows = json.loads(keyboard_json)["buttons"]

    # по кнопке на услугу в своём ряду + отдельный ряд «Назад»
    assert len(rows) == len(services) + 1
    assert rows[-1][0]["color"] == "secondary"


def test_menu_short_keyboard() -> None:
    keyboard_json = keyboards.menu_short_keyboard("📋 Меню")
    rows = json.loads(keyboard_json)["buttons"]

    assert len(rows) == 1
    assert payloads_of(keyboard_json) == [{"cmd": "menu"}]
