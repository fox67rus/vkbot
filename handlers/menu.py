"""Главное меню: услуги, прайс-лист, описание услуги, связь с менеджером.

Работает двумя способами:

* **ЛС** — кнопки с payload (``{"cmd": "..."}``); каждая кнопка имеет
  собственный обработчик, поэтому сообщения с payload не доходят до AI.
* **Беседа** — ВК не показывает клавиатуры в беседах, поэтому те же экраны
  открываются текстовыми командами («меню», «услуги», «цены», «менеджер»),
  сказанными с упоминанием бота. Клавиатура в беседу не прикрепляется.

Экраны отрисовываются из ``data/content.json``: правка контента не требует
изменения кода. Приветствие (``menu.welcome``) уходит только при первом
открытии меню, повторные (кнопки «Назад»/«Меню», команда «меню») показывают
короткий заголовок ``menu.title``.
"""

from __future__ import annotations

import json
import logging

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules.base import FromUserRule, MentionRule

import keyboards
from content import (
    get_content,
    get_service,
    manager_link,
    manager_text,
    menu_buttons,
    menu_label,
    menu_title,
    back_label,
    price_text,
    service_card_text,
    services_list_text,
    services_ordered,
    static_text,
    welcome_text,
)

logger = logging.getLogger(__name__)

bl = BotLabeler()
# Игнорируем сообщения от других ботов — как в AI-лейблере
bl.auto_rules = [FromUserRule()]

# peer_id личного сообщения; в беседах он всегда больше
PRIVATE_PEER_LIMIT = 2_000_000_000

# Текстовая команда → экран меню (используется и в ЛС, и в беседе)
ALIASES: dict[str, str] = {
    "меню": "menu",
    "menu": "menu",
    "главное меню": "menu",
    "старт": "menu",
    "start": "menu",
    "/старт": "menu",
    "/start": "menu",
    "услуги": "services",
    "список услуг": "services",
    "прайс": "price",
    "прайс-лист": "price",
    "прайс лист": "price",
    "цены": "price",
    "стоимость": "price",
    "менеджер": "manager",
    "контакты": "manager",
    "связаться с менеджером": "manager",
    "помощь": "help",
    "help": "help",
    "о нас": "about",
}

# peer_id, которым уже показано приветствие с меню (только память процесса)
_welcomed: set[int] = set()


def mark_welcomed(peer_id: int) -> bool:
    """Запомнить peer_id; ``True`` — если меню показываем ему впервые."""
    if peer_id in _welcomed:
        return False
    _welcomed.add(peer_id)
    return True


def is_welcomed(peer_id: int) -> bool:
    """Приветствие этому peer_id уже отправлялось."""
    return peer_id in _welcomed


def reset_welcomed() -> None:
    """Забыть всех приветствованных (используется в тестах)."""
    _welcomed.clear()


def get_payload(message: Message) -> dict:
    """Payload нажатой кнопки как словарь; пустой dict, если его нет."""
    getter = getattr(message, "get_payload_json", None)
    if callable(getter):
        data = getter()
    else:
        data = getattr(message, "payload", None)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                data = None
    return data if isinstance(data, dict) else {}


def has_payload(message: Message) -> bool:
    """Сообщение пришло от кнопки, а не от человека."""
    return bool(get_payload(message))


def _normalize(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def is_menu_command(message: Message) -> bool:
    """Текст — команда меню, сказанная человеком (до AI-фоллбэка).

    Сообщения с payload отбрасываются: их обрабатывают кнопочные хендлеры,
    иначе одна кнопка совпала бы сразу с двумя обработчиками.
    """
    if has_payload(message):
        return False
    return _normalize(message.text) in ALIASES


def _is_private(peer_id: int) -> bool:
    return peer_id < PRIVATE_PEER_LIMIT


async def _send_screen(message: Message, text: str, keyboard_json: str | None = None) -> None:
    """Отправить экран; клавиатура — только в личных сообщениях."""
    if keyboard_json and _is_private(message.peer_id):
        await message.answer(text, keyboard=keyboard_json)
    else:
        await message.answer(text)


# ------------------------------------------------------------------ экраны


async def show_menu(message: Message) -> None:
    """Главное меню.

    Приветствие («Здравствуйте!...») — только при первом открытии меню;
    «Назад» и «Меню» показывают короткий заголовок, иначе пользователь
    читал бы приветствие на каждом нажатии.
    """
    text = welcome_text() if mark_welcomed(message.peer_id) else menu_title()
    await _send_screen(message, text, keyboards.main_menu_keyboard(menu_buttons()))


async def show_services(message: Message) -> None:
    """Список услуг с ценами и кнопками для перехода к описанию."""
    await _send_screen(
        message,
        services_list_text(),
        keyboards.services_keyboard(services_ordered(), back_label()),
    )


async def show_service(message: Message, service_id: str) -> None:
    """Описание одной услуги; неизвестный id — возврат к списку."""
    service = get_service(service_id)
    if service is None:
        logger.warning("Запрошена неизвестная услуга: %r", service_id)
        await _send_screen(
            message,
            "Такой услуги в каталоге нет. Вот актуальный список:",
            keyboards.services_keyboard(services_ordered(), back_label()),
        )
        return
    await _send_screen(
        message,
        service_card_text(service),
        keyboards.service_keyboard(back_label(), menu_label()),
    )


async def show_price(message: Message) -> None:
    """Прайс-лист по всем услугам."""
    await _send_screen(message, price_text(), keyboards.simple_menu_keyboard(back_label()))


async def show_manager(message: Message) -> None:
    """Контакты менеджера + кнопка-ссылка для быстрой связи."""
    link = manager_link()
    keyboard_json = keyboards.manager_keyboard(
        link[0] if link else None,
        link[1] if link else None,
        back_label(),
    )
    await _send_screen(message, manager_text(), keyboard_json)


async def show_static(message: Message, command: str) -> None:
    """Экран с готовым текстом из JSON («О нас», «Помощь»)."""
    await _send_screen(
        message,
        static_text(command),
        keyboards.main_menu_keyboard(menu_buttons()),
    )


async def show_command(message: Message, command: str) -> None:
    """Открыть экран по имени команды (для кнопок и текстовых команд)."""
    if command == "menu":
        await show_menu(message)
    elif command == "services":
        await show_services(message)
    elif command == "price":
        await show_price(message)
    elif command == "manager":
        await show_manager(message)
    elif command in ("about", "help"):
        await show_static(message, command)


# --------------------------------------------------------------- обработчики


@bl.private_message(payload={"cmd": "menu"})
async def on_menu_button(message: Message) -> None:
    """Кнопка «Меню» или «Назад»."""
    await show_menu(message)


@bl.private_message(payload={"cmd": "services"})
async def on_services_button(message: Message) -> None:
    """Кнопка «Услуги»."""
    await show_services(message)


@bl.private_message(payload_map={"cmd": "service", "id": str})
async def on_service_button(message: Message) -> None:
    """Кнопка конкретной услуги в списке."""
    await show_service(message, str(get_payload(message).get("id", "")))


@bl.private_message(payload={"cmd": "price"})
async def on_price_button(message: Message) -> None:
    """Кнопка «Прайс-лист»."""
    await show_price(message)


@bl.private_message(payload={"cmd": "manager"})
async def on_manager_button(message: Message) -> None:
    """Кнопка «Менеджер»."""
    await show_manager(message)


@bl.private_message(payload={"cmd": "about"})
async def on_about_button(message: Message) -> None:
    """Кнопка «О нас»."""
    await show_static(message, "about")


@bl.private_message(payload={"cmd": "help"})
async def on_help_button(message: Message) -> None:
    """Кнопка «Помощь»."""
    await show_static(message, "help")


@bl.private_message(func=is_menu_command)
async def on_alias_command(message: Message) -> None:
    """Текстовая команда в ЛС («меню», «цены», «услуги», «менеджер»…)."""
    await show_command(message, ALIASES[_normalize(message.text)])


@bl.chat_message(MentionRule(mention_only=False), func=is_menu_command)
async def on_chat_alias_command(message: Message) -> None:
    """Та же команда в беседе — по упоминанию бота, без клавиатуры."""
    await show_command(message, ALIASES[_normalize(message.text)])


def content_services_count() -> int:
    """Число услуг в контенте — удобно для диагностики при старте."""
    return len(get_content()["services"])
