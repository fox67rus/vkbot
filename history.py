"""Хранилище истории диалогов в памяти процесса."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterator

HistoryKey = tuple[int, int]
HistoryMessage = dict[str, str]


class DialogHistory:
    """Последние N сообщений на пару «диалог + автор».

    Ключ ``(peer_id, from_id)``: в ЛС это один и тот же id, в беседе
    у каждого участника свой контекст. Хранятся только роли
    ``user`` и ``assistant`` — системный промпт добавляет AI-клиент.
    После рестарта история теряется: хранилище намеренно in-memory.
    """

    def __init__(self, max_messages: int = 20) -> None:
        if max_messages < 2:
            raise ValueError("max_messages должно быть не меньше 2")
        self.max_messages = max_messages
        self._data: dict[HistoryKey, deque[HistoryMessage]] = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    @staticmethod
    def make_key(peer_id: int, from_id: int) -> HistoryKey:
        return (peer_id, from_id)

    def get(self, key: HistoryKey) -> list[HistoryMessage]:
        """Копия истории для передачи в модель."""
        return list(self._data.get(key, ()))

    def add(self, key: HistoryKey, role: str, content: str) -> None:
        """Добавить реплику; самая старая вытесняется при переполнении."""
        self._data[key].append({"role": role, "content": content})

    def pop(self, key: HistoryKey) -> HistoryMessage | None:
        """Убрать последнюю реплику (откат при ошибке AI)."""
        bucket = self._data.get(key)
        if not bucket:
            return None
        return bucket.pop()

    def clear(self, key: HistoryKey) -> None:
        self._data.pop(key, None)

    def clear_all(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[HistoryKey]:
        return iter(self._data)
