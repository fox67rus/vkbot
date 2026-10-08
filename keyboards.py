"""Клавиатуры ВКонтакте, собранные из контента ``data/content.json``.

Каждая кнопка несёт payload вида ``{"cmd": "..."}`` (для услуг — ещё и
``{"id": "..."}``). Payload передаётся **строкой**: так требует API ВКонтакте,
а при получении vkbottle сам разбирает его обратно в словарь.

Клавиатуры собираются заново при каждом вызове, поэтому сразу учитывают
правки JSON — кэшировать их не нужно.
"""

from __future__ import annotations

import json

from vkbottle import Keyboard, KeyboardButtonColor, OpenLink, Text

# Ряд главного меню: две кнопки в строке
MENU_ROW_WIDTH = 2


def payload(cmd: str, **extra) -> str:
    """Payload кнопки строкой JSON (набор ключей произвольный)."""
    return json.dumps({"cmd": cmd, **extra}, ensure_ascii=False, separators=(",", ":"))


def main_menu_keyboard(buttons: list[dict]) -> str:
    """Постоянное главное меню: по два пункта в ряд, порядок из JSON."""
    keyboard = Keyboard(one_time=False)
    for index, button in enumerate(buttons):
        if index and index % MENU_ROW_WIDTH == 0:
            keyboard.row()
        keyboard.add(Text(button["label"], payload=payload(button["id"])))
    return keyboard.get_json()


def services_keyboard(services: list[dict], back_label: str) -> str:
    """Список услуг: кнопка на каждую услугу + «Назад» в главное меню."""
    keyboard = Keyboard(one_time=False)
    for service in services:
        keyboard.row()
        keyboard.add(Text(service["title"], payload=payload("service", id=service["id"])))
    keyboard.row()
    keyboard.add(
        Text(back_label, payload=payload("menu")),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()


def service_keyboard(back_label: str, menu_label: str) -> str:
    """Карточка услуги: назад к списку услуг и в главное меню."""
    keyboard = Keyboard(one_time=False)
    keyboard.add(
        Text(back_label, payload=payload("services")),
        color=KeyboardButtonColor.SECONDARY,
    )
    keyboard.add(Text(menu_label, payload=payload("menu")))
    return keyboard.get_json()


def simple_menu_keyboard(back_label: str) -> str:
    """Экран без собственных кнопок (прайс, контакты): только «Назад»."""
    keyboard = Keyboard(one_time=False)
    keyboard.add(
        Text(back_label, payload=payload("menu")),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()


def manager_keyboard(link: str | None, link_label: str | None, back_label: str) -> str:
    """Контакты менеджера: кнопка-ссылка (если задана) + «Назад»."""
    keyboard = Keyboard(one_time=False)
    if link and link_label:
        keyboard.add(OpenLink(link, link_label), color=KeyboardButtonColor.POSITIVE)
    keyboard.row()
    keyboard.add(
        Text(back_label, payload=payload("menu")),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()


def menu_short_keyboard(menu_label: str) -> str:
    """Одна кнопка «Меню» — прикрепляется к ответам AI, чтобы меню было рядом."""
    keyboard = Keyboard(one_time=False)
    keyboard.add(Text(menu_label, payload=payload("menu")))
    return keyboard.get_json()
