"""Асинхронный клиент ProxyAPI (OpenAI-совместимый /chat/completions)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .errors import AIClientError

logger = logging.getLogger(__name__)

# Статусы, при которых имеет смысл повторить запрос
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
BACKOFF_BASE = 0.5
BACKOFF_CAP = 5.0


class ProxyAIClient:
    """Клиент генерации текста через ProxyAPI.

    Параметры ``temperature``/``max_tokens`` отправляются по желанию:
    если провайдер отвечает 400, запрос повторяется уже без них.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._system_prompt = system_prompt.strip()
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None

    @property
    def model(self) -> str:
        return self._model

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            )
        return self._session

    async def close(self) -> None:
        """Закрыть HTTP-сессию (вызывается из on_shutdown)."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def ask(self, messages: list[dict[str, str]]) -> str:
        """Отправить диалог модели и вернуть текст ответа.

        ``messages`` — список ``{"role": "user"|"assistant", "content": ...}``.
        Системный промпт добавляется внутрь метода.
        """
        request_messages = list(messages)
        if self._system_prompt:
            request_messages.insert(0, {"role": "system", "content": self._system_prompt})

        base_payload: dict[str, Any] = {"model": self._model, "messages": request_messages}

        optional: dict[str, Any] = {}
        if self._temperature is not None:
            optional["temperature"] = self._temperature
        if self._max_tokens is not None:
            optional["max_tokens"] = self._max_tokens

        use_optional = bool(optional)
        attempt = 0

        while True:
            payload = {**base_payload, **optional} if use_optional else dict(base_payload)

            try:
                status, data = await self._post(payload)
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt < self._max_retries:
                    attempt += 1
                    await self._sleep(attempt)
                    continue
                raise AIClientError(f"Сетевая ошибка при обращении к AI: {exc}") from exc

            if status == 200:
                return self._extract_text(data)

            # Провайдер может не принимать optional-параметры у конкретной модели
            if status == 400 and use_optional:
                logger.debug("400 от ProxyAPI, повторяем без temperature/max_tokens")
                use_optional = False
                continue

            if status in RETRYABLE_STATUSES and attempt < self._max_retries:
                attempt += 1
                await self._sleep(attempt)
                continue

            raise AIClientError(self._error_detail(data) or f"HTTP {status}", status=status)

    async def _post(self, payload: dict[str, Any]) -> tuple[int, Any]:
        session = self._get_session()
        async with session.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        ) as response:
            try:
                data = await response.json(content_type=None)
            except (aiohttp.ContentTypeError, ValueError):
                data = None
            return response.status, data

    @staticmethod
    async def _sleep(attempt: int) -> None:
        await asyncio.sleep(min(BACKOFF_BASE * (2 ** (attempt - 1)), BACKOFF_CAP))

    @staticmethod
    def _extract_text(data: Any) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIClientError(
                f"Неожиданный формат ответа ProxyAPI: {data!r}", status=200
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise AIClientError("Пустой ответ модели", status=200)
        return content.strip()

    @staticmethod
    def _error_detail(data: Any) -> str | None:
        """Достать текст ошибки: {"detail": ...} у ProxyAPI или {"error": {...}}."""
        if not isinstance(data, dict):
            return None
        detail = data.get("detail")
        if isinstance(detail, str) and detail:
            return detail
        error = data.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message:
                return message
        if isinstance(error, str) and error:
            return error
        return None
