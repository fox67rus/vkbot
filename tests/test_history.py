"""Тесты истории диалогов."""

from __future__ import annotations

import pytest

from history import DialogHistory


def test_history_is_trimmed_to_max_messages() -> None:
    history = DialogHistory(max_messages=4)
    key = history.make_key(peer_id=1, from_id=1)

    for index in range(6):
        role = "user" if index % 2 == 0 else "assistant"
        history.add(key, role, f"m{index}")

    messages = history.get(key)
    assert len(messages) == 4
    assert messages[0]["content"] == "m2"  # старые вытеснены
    assert messages[-1]["content"] == "m5"


def test_unknown_key_does_not_create_bucket() -> None:
    history = DialogHistory(max_messages=4)

    assert history.get((999, 999)) == []
    assert len(history) == 0


def test_keys_are_isolated() -> None:
    history = DialogHistory(max_messages=10)
    private = history.make_key(peer_id=5, from_id=5)
    chat_a = history.make_key(peer_id=2000000001, from_id=1)
    chat_b = history.make_key(peer_id=2000000001, from_id=2)

    history.add(private, "user", "для лс")
    history.add(chat_a, "user", "для первого")
    history.add(chat_b, "user", "для второго")

    assert len(history) == 3
    assert history.get(private)[0]["content"] == "для лс"
    assert history.get(chat_a)[0]["content"] == "для первого"
    assert history.get(chat_b)[0]["content"] == "для второго"


def test_get_returns_a_copy() -> None:
    history = DialogHistory(max_messages=4)
    key = history.make_key(peer_id=1, from_id=1)
    history.add(key, "user", "привет")

    copy = history.get(key)
    copy.append({"role": "user", "content": "подделка"})

    assert len(history.get(key)) == 1


def test_pop_removes_last_message() -> None:
    history = DialogHistory(max_messages=4)
    key = history.make_key(peer_id=1, from_id=1)
    history.add(key, "user", "первый")
    history.add(key, "user", "второй")

    popped = history.pop(key)
    assert popped is not None and popped["content"] == "второй"
    assert [m["content"] for m in history.get(key)] == ["первый"]


def test_pop_on_empty_history_returns_none() -> None:
    assert DialogHistory().pop((1, 1)) is None


def test_clear() -> None:
    history = DialogHistory(max_messages=4)
    key = history.make_key(peer_id=1, from_id=1)
    history.add(key, "user", "привет")

    history.clear(key)
    assert history.get(key) == []
    assert len(history) == 0

    history.add(key, "user", "снова")
    history.clear_all()
    assert len(history) == 0


@pytest.mark.parametrize("bad_size", [0, 1])
def test_invalid_size_rejected(bad_size) -> None:
    with pytest.raises(ValueError):
        DialogHistory(max_messages=bad_size)
