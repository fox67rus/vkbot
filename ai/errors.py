"""Исключения клиента AI."""

from __future__ import annotations


class AIClientError(RuntimeError):
    """Ошибка обращения к AI-провайдеру."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status
