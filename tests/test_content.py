"""Тесты контента: проверка data/content.json и текстов экранов."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import content
from content import ContentError


def sample_content() -> dict:
    """Минимальный валидный контент для негативных проверок."""
    return {
        "menu": {
            "welcome": "Привет!",
            "services_text": "Выберите услугу:",
            "back_label": "🔙 Назад",
            "menu_label": "📋 Меню",
            "buttons": [
                {"id": "services", "label": "📋 Услуги"},
                {"id": "price", "label": "💰 Прайс"},
                {"id": "manager", "label": "👩‍💼 Менеджер"},
                {"id": "about", "label": "ℹ️ О нас", "text": "Мы делаем сайты."},
                {"id": "help", "label": "💬 Помощь", "text": "Пишите вопросы."},
            ],
        },
        "services": [
            {
                "id": "web",
                "title": "Разработка сайта",
                "short": "Лендинги и сайты",
                "description": "Сайт под ключ.",
                "price": "от 80 000 ₽",
                "duration": "от 3 недель",
            },
            {
                "id": "design",
                "title": "Дизайн",
                "short": "UI/UX",
                "description": "Макеты в Figma.",
                "price": "от 35 000 ₽",
            },
        ],
        "price": {
            "header": "Прайс-лист:",
            "footer": "Смета бесплатно.",
            "order": ["design", "web"],
        },
        "manager": {
            "name": "Анна",
            "greeting": "Вам поможет менеджер:",
            "phone": "+7 (900) 000-00-00",
            "hours": "Пн–Пт",
            "link": "https://vk.com/id1",
            "link_label": "Написать менеджеру",
        },
    }


def write_content(tmp_path: Path, data: dict, *, raw: str | None = None) -> Path:
    path = tmp_path / "content.json"
    path.write_text(raw if raw is not None else json.dumps(data, ensure_ascii=False), "utf-8")
    return path


# ------------------------------------------------------------ файл из репозитория


def test_repository_content_is_valid() -> None:
    """Файл, лежащий в проекте, проходит проверку и содержит данные."""
    data = content.load_content()

    assert len(data["menu"]["buttons"]) >= 5
    assert len(data["services"]) >= 3
    for service in data["services"]:
        for field in ("id", "title", "description", "price"):
            assert service[field].strip()


def test_menu_title_defaults_when_missing() -> None:
    """Без menu.title в контенте — заголовок по умолчанию, а не ошибка."""
    content.set_content(sample_content())

    assert content.menu_title() == content.DEFAULT_MENU_TITLE
    assert "Здравствуйте" not in content.menu_title()


def test_menu_title_from_content() -> None:
    data = sample_content()
    data["menu"]["title"] = "Выберите пункт:"
    content.set_content(data)

    assert content.menu_title() == "Выберите пункт:"


def test_menu_title_must_be_text(tmp_path) -> None:
    data = sample_content()
    data["menu"]["title"] = 42
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="title"):
        content.load_content(path)


def test_get_content_caches_result() -> None:
    first = content.get_content()
    assert content.get_content() is first


def test_reset_content_rereads_file() -> None:
    first = content.get_content()
    content.reset_content()
    second = content.get_content()

    assert first is not second  # кэш сброшен, объект читается заново
    assert first == second  # но данные те же


# ------------------------------------------------------------------ ошибки


def test_missing_file(tmp_path) -> None:
    with pytest.raises(ContentError, match="не найден"):
        content.load_content(tmp_path / "nope.json")


def test_broken_json(tmp_path) -> None:
    path = write_content(tmp_path, {}, raw='{"menu": ')
    with pytest.raises(ContentError, match="Некорректный JSON"):
        content.load_content(path)


def test_missing_section(tmp_path) -> None:
    data = sample_content()
    del data["manager"]
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="manager"):
        content.load_content(path)


def test_empty_file_is_not_object(tmp_path) -> None:
    path = write_content(tmp_path, {}, raw="[1, 2, 3]")
    with pytest.raises(ContentError, match="JSON-объект"):
        content.load_content(path)


def test_unknown_menu_button(tmp_path) -> None:
    data = sample_content()
    data["menu"]["buttons"].append({"id": "delivery", "label": "🚚 Доставка"})
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="неизвестная кнопка «delivery»"):
        content.load_content(path)


def test_text_command_requires_text(tmp_path) -> None:
    data = sample_content()
    data["menu"]["buttons"][3].pop("text")  # about
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="text"):
        content.load_content(path)


def test_duplicate_button(tmp_path) -> None:
    data = sample_content()
    data["menu"]["buttons"].append({"id": "price", "label": "💰 Ещё раз"})
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="повторяется"):
        content.load_content(path)


def test_duplicate_service_id(tmp_path) -> None:
    data = sample_content()
    data["services"].append(dict(data["services"][0]))
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="id «web» повторяется"):
        content.load_content(path)


def test_service_requires_fields(tmp_path) -> None:
    data = sample_content()
    data["services"][0].pop("price")
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="price"):
        content.load_content(path)


def test_price_order_must_reference_existing_service(tmp_path) -> None:
    data = sample_content()
    data["price"]["order"] = ["web", "support"]
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="«support» не найдена"):
        content.load_content(path)


def test_manager_needs_phone_or_link(tmp_path) -> None:
    data = sample_content()
    data["manager"].pop("phone")
    data["manager"].pop("link")
    data["manager"].pop("link_label")
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="phone"):
        content.load_content(path)


def test_manager_link_must_be_http(tmp_path) -> None:
    data = sample_content()
    data["manager"]["link"] = "vk.com/id1"
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="http"):
        content.load_content(path)


def test_link_requires_label(tmp_path) -> None:
    data = sample_content()
    data["manager"].pop("link_label")
    path = write_content(tmp_path, data)

    with pytest.raises(ContentError, match="link_label"):
        content.load_content(path)


# ------------------------------------------------------------------ тексты


def test_services_ordered_follows_price_order() -> None:
    content.set_content(sample_content())

    assert [service["id"] for service in content.services_ordered()] == ["design", "web"]


def test_services_list_text_contains_titles_and_prices() -> None:
    content.set_content(sample_content())

    text = content.services_list_text()

    assert text.startswith("Выберите услугу:")
    assert "1. Дизайн — от 35 000 ₽" in text
    assert "2. Разработка сайта — от 80 000 ₽" in text


def test_price_text_has_header_footer_and_every_service() -> None:
    content.set_content(sample_content())

    text = content.price_text()

    assert text.startswith("Прайс-лист:")
    assert "Смета бесплатно." in text
    assert "Разработка сайта — от 80 000 ₽" in text
    assert "Дизайн — от 35 000 ₽" in text


def test_service_card_text_describes_service() -> None:
    content.set_content(sample_content())
    service = content.get_service("web")

    text = content.service_card_text(service)

    assert "Сайт под ключ." in text
    assert "Сроки: от 3 недель" in text
    assert "Цена: от 80 000 ₽" in text


def test_service_card_without_duration() -> None:
    content.set_content(sample_content())
    service = content.get_service("design")

    text = content.service_card_text(service)

    assert "Сроки" not in text
    assert "Цена: от 35 000 ₽" in text


def test_manager_text_and_link() -> None:
    content.set_content(sample_content())

    text = content.manager_text()

    assert "Менеджер: Анна" in text
    assert "Телефон: +7 (900) 000-00-00" in text
    assert "График: Пн–Пт" in text
    assert content.manager_link() == ("https://vk.com/id1", "Написать менеджеру")


def test_manager_without_link() -> None:
    data = sample_content()
    data["manager"].pop("link")
    data["manager"].pop("link_label")
    content.set_content(data)

    assert content.manager_link() is None
    assert "Телефон:" in content.manager_text()


def test_static_text_returns_button_text() -> None:
    content.set_content(sample_content())

    assert content.static_text("about") == "Мы делаем сайты."
    assert content.static_text("price") == ""  # у прайса текст задан в разделе price
    with pytest.raises(ContentError):
        content.static_text("delivery")  # такой кнопки нет


def test_get_service_unknown_returns_none() -> None:
    content.set_content(sample_content())

    assert content.get_service("nope") is None
