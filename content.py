"""Контент бота: чтение и проверка ``data/content.json``, тексты экранов.

Весь пользовательский контент — приветствие, меню, услуги, прайс, контакты
менеджера — лежит в одном JSON-файле. Правка контента не требует изменения
кода: отредактируйте файл и перезапустите бота.

Файл проверяется при загрузке: отсутствие раздела, дубли id услуг или
неизвестная кнопка меню дают :class:`ContentError` с понятным сообщением,
а не ``KeyError`` посреди обработчика.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
CONTENT_PATH = BASE_DIR / "data" / "content.json"

# Разделы, обязательные на верхнем уровне файла
REQUIRED_SECTIONS = ("menu", "services", "price", "manager")
# Кнопки меню умеют открывать только эти экраны
KNOWN_COMMANDS = ("services", "price", "manager", "about", "help")
# ... а текст этих экранов хранится прямо в кнопке (поле "text")
TEXT_COMMANDS = ("about", "help")
# Обязательные поля каждой услуги
SERVICE_FIELDS = ("title", "short", "description", "price")
# Заголовок меню, если в JSON не задан свой (menu.title)
DEFAULT_MENU_TITLE = "Главное меню. Выберите пункт ниже:"


class ContentError(RuntimeError):
    """Файл контента отсутствует, не разбирается или не прошёл проверку."""


def _fail(message: str) -> None:
    raise ContentError(message)


def _require_text(container: dict, key: str, where: str) -> str:
    """Строка обязана присутствовать и не быть пустой."""
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where}: ожидается непустая строка «{key}»")
    return value  # type: ignore[return-value]


def _optional_text(container: dict, key: str, where: str) -> str | None:
    """Строка может отсутствовать, но если есть — должна быть строкой."""
    value = container.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where}: «{key}» должно быть непустой строкой")
    return value


def _require_object(value: Any, where: str) -> dict:
    if not isinstance(value, dict):
        _fail(f"{where}: ожидается JSON-объект")
    return value  # type: ignore[return-value]


def _require_list(value: Any, where: str) -> list:
    if not isinstance(value, list) or not value:
        _fail(f"{where}: ожидается непустой список")
    return value  # type: ignore[return-value]


def validate_content(data: Any, source: Path | str = CONTENT_PATH) -> dict:
    """Проверить структуру контента и вернуть его же.

    Поднимает :class:`ContentError` с указанием раздела и пути к файлу.
    """
    if not isinstance(data, dict):
        _fail(f"{source}: ожидается JSON-объект на верхнем уровне")

    for section in REQUIRED_SECTIONS:
        if section not in data:
            _fail(f"{source}: нет обязательного раздела «{section}»")

    # ------------------------------------------------------------- меню
    menu = _require_object(data["menu"], "menu")
    _require_text(menu, "welcome", "menu")
    # Повторные открытия меню: заголовок без приветствия (fallback — дефолтный)
    _optional_text(menu, "title", "menu")
    _require_text(menu, "services_text", "menu")
    _optional_text(menu, "back_label", "menu")
    _optional_text(menu, "menu_label", "menu")

    buttons = _require_list(menu.get("buttons"), "menu.buttons")
    seen_buttons: set[str] = set()
    for index, raw_button in enumerate(buttons):
        where = f"menu.buttons[{index}]"
        button = _require_object(raw_button, where)
        command = button.get("id")
        if command not in KNOWN_COMMANDS:
            _fail(
                f"{where}: неизвестная кнопка «{command}», "
                f"доступны: {', '.join(KNOWN_COMMANDS)}"
            )
        if command in seen_buttons:
            _fail(f"{where}: кнопка «{command}» повторяется")
        seen_buttons.add(command)
        _require_text(button, "label", where)
        if command in TEXT_COMMANDS:
            _require_text(button, "text", where)

    # ----------------------------------------------------------- услуги
    services = _require_list(data["services"], "services")
    service_ids: set[str] = set()
    for index, raw_service in enumerate(services):
        where = f"services[{index}]"
        service = _require_object(raw_service, where)
        service_id = service.get("id")
        if not isinstance(service_id, str) or not service_id.strip():
            _fail(f"{where}: нужен непустый строковый «id»")
        if service_id in service_ids:
            _fail(f"{where}: id «{service_id}» повторяется")
        service_ids.add(service_id)
        for field in SERVICE_FIELDS:
            _require_text(service, field, where)
        _optional_text(service, "duration", where)

    # ------------------------------------------------------------- прайс
    price = _require_object(data["price"], "price")
    _require_text(price, "header", "price")
    _optional_text(price, "footer", "price")

    order = price.get("order", [])
    if not isinstance(order, list):
        _fail("price: «order» должно быть списком id услуг")
    for service_id in order:
        if service_id not in service_ids:
            _fail(f"price.order: услуга «{service_id}» не найдена в разделе services")

    # ---------------------------------------------------------- менеджер
    manager = _require_object(data["manager"], "manager")
    _require_text(manager, "name", "manager")
    _require_text(manager, "greeting", "manager")
    _optional_text(manager, "phone", "manager")
    _optional_text(manager, "hours", "manager")

    link = _optional_text(manager, "link", "manager")
    if link is not None:
        if not link.startswith(("http://", "https://")):
            _fail("manager: «link» должна начинаться с http:// или https://")
        _require_text(manager, "link_label", "manager")
    if not manager.get("phone") and not link:
        _fail("manager: укажите «phone» и/или «link» — иначе некуда отправить пользователя")

    return data


def load_content(path: Path | str = CONTENT_PATH) -> dict:
    """Прочитать и проверить файл контента."""
    path = Path(path)
    if not path.exists():
        raise ContentError(f"Файл контента не найден: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"Некорректный JSON в {path}: {exc}") from exc
    except OSError as exc:
        raise ContentError(f"Не удалось прочитать {path}: {exc}") from exc
    return validate_content(data, path)


_cache: dict | None = None


def get_content() -> dict:
    """Контент из ``data/content.json`` (кэшируется после первого чтения)."""
    global _cache
    if _cache is None:
        _cache = load_content()
    return _cache


def set_content(data: Any, *, source: str = "ручной ввод") -> dict:
    """Проверить и положить контент в кэш (используется в тестах и при перезагрузке)."""
    global _cache
    _cache = validate_content(data, source)
    return _cache


def reset_content() -> None:
    """Сбросить кэш: следующий ``get_content()`` прочитает файл заново."""
    global _cache
    _cache = None


# ------------------------------------------------------------------ тексты


def menu_buttons() -> list[dict]:
    return list(get_content()["menu"]["buttons"])


def back_label() -> str:
    return get_content()["menu"].get("back_label") or "🔙 Назад"


def menu_label() -> str:
    return get_content()["menu"].get("menu_label") or "📋 Меню"


def welcome_text() -> str:
    """Приветствие — показывается только при первом открытии меню."""
    return get_content()["menu"]["welcome"]


def menu_title() -> str:
    """Заголовок меню при повторных открытиях: без «Здравствуйте!...»."""
    return get_content()["menu"].get("title") or DEFAULT_MENU_TITLE


def services_intro() -> str:
    return get_content()["menu"]["services_text"]


def get_service(service_id: str) -> dict | None:
    for service in get_content()["services"]:
        if service["id"] == service_id:
            return service
    return None


def services_ordered() -> list[dict]:
    """Услуги в порядке ``price.order``, остальные — в порядке файла."""
    data = get_content()
    services = data["services"]
    order = data["price"].get("order") or []
    by_id = {service["id"]: service for service in services}
    ordered = [by_id[service_id] for service_id in order if service_id in by_id]
    ordered_ids = {service["id"] for service in ordered}
    ordered.extend(s for s in services if s["id"] not in ordered_ids)
    return ordered


def _numbered_lines() -> list[str]:
    return [
        f"{number}. {service['title']} — {service['price']}"
        for number, service in enumerate(services_ordered(), start=1)
    ]


def services_list_text() -> str:
    """Экран «Услуги»: вступление + нумерованный список с ценами."""
    lines = [services_intro(), ""]
    lines.extend(_numbered_lines())
    return "\n".join(lines)


def service_card_text(service: dict) -> str:
    """Карточка одной услуги: описание, сроки, цена."""
    lines = [service["title"], "", service["description"], ""]
    if service.get("duration"):
        lines.append(f"Сроки: {service['duration']}")
    lines.append(f"Цена: {service['price']}")
    return "\n".join(lines)


def price_text() -> str:
    """Прайс-лист: заголовок + все услуги по порядку + сноска."""
    price = get_content()["price"]
    lines = [price["header"], ""]
    lines.extend(_numbered_lines())
    footer = price.get("footer")
    if footer:
        lines.append(footer)
    return "\n".join(lines)


def manager_text() -> str:
    """Контакты менеджера (сама ссылка — на кнопке)."""
    manager = get_content()["manager"]
    lines = [manager["greeting"], "", f"Менеджер: {manager['name']}"]
    if manager.get("phone"):
        lines.append(f"Телефон: {manager['phone']}")
    if manager.get("hours"):
        lines.append(f"График: {manager['hours']}")
    return "\n".join(lines)


def manager_link() -> tuple[str, str] | None:
    """``(ссылка, подпись кнопки)`` или ``None``, если ссылки нет."""
    manager = get_content()["manager"]
    if manager.get("link"):
        return manager["link"], manager["link_label"]
    return None


def static_text(command: str) -> str:
    """Текст экрана, который целиком лежит в кнопке меню («О нас», «Помощь»)."""
    for button in menu_buttons():
        if button["id"] == command:
            return button.get("text", "")
    raise ContentError(f"Кнопка «{command}» не найдена в menu.buttons")
