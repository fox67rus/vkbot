"""Тесты клиента ProxyAPI против мок-сервера."""

from __future__ import annotations

import asyncio

import pytest
from aiohttp import web

from ai import AIClientError, ProxyAIClient
from helpers import api_server, free_port

OK_RESPONSE = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": " Ответ модели "}}
    ],
}


def make_client(base_url: str, **overrides) -> ProxyAIClient:
    params = dict(
        api_key="sk-test",
        base_url=base_url,
        model="openai/gpt-5.4-mini",
        system_prompt="Ты ассистент.",
        temperature=0.7,
        max_tokens=1000,
        timeout=10.0,
        max_retries=3,
    )
    params.update(overrides)
    return ProxyAIClient(**params)


async def _ask(client: ProxyAIClient, text: str = "привет") -> str:
    try:
        return await client.ask([{"role": "user", "content": text}])
    finally:
        await client.close()


def test_ask_returns_content_and_builds_payload() -> None:
    seen: list[tuple[str, dict]] = []

    async def handler(request: web.Request) -> web.Response:
        seen.append((request.headers["Authorization"], await request.json()))
        return web.json_response(OK_RESPONSE)

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    result = asyncio.run(scenario())

    assert result == "Ответ модели"  # пробелы обрезаны
    assert len(seen) == 1
    auth, payload = seen[0]

    assert auth == "Bearer sk-test"
    assert payload["model"] == "openai/gpt-5.4-mini"
    assert payload["messages"][0] == {"role": "system", "content": "Ты ассистент."}
    assert payload["messages"][1] == {"role": "user", "content": "привет"}
    assert payload["temperature"] == 0.7
    assert payload["max_tokens"] == 1000


def test_system_prompt_skipped_when_empty() -> None:
    seen: list[dict] = []

    async def handler(request: web.Request) -> web.Response:
        seen.append(await request.json())
        return web.json_response(OK_RESPONSE)

    async def scenario() -> str:
        async with api_server(handler) as base:
            client = make_client(base, system_prompt="")
            return await _ask(client)

    asyncio.run(scenario())
    assert [m["role"] for m in seen[0]["messages"]] == ["user"]


def test_optional_params_not_sent_when_disabled() -> None:
    seen: list[dict] = []

    async def handler(request: web.Request) -> web.Response:
        seen.append(await request.json())
        return web.json_response(OK_RESPONSE)

    async def scenario() -> str:
        async with api_server(handler) as base:
            client = make_client(base, temperature=None, max_tokens=None)
            return await _ask(client)

    asyncio.run(scenario())
    assert "temperature" not in seen[0]
    assert "max_tokens" not in seen[0]


def test_400_retries_without_optional_params() -> None:
    payloads: list[dict] = []

    async def handler(request: web.Request) -> web.Response:
        body = await request.json()
        payloads.append(body)
        if "temperature" in body or "max_tokens" in body:
            return web.json_response(
                {"detail": "Unsupported parameter: 'temperature'"}, status=400
            )
        return web.json_response(OK_RESPONSE)

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    result = asyncio.run(scenario())

    assert result == "Ответ модели"
    assert len(payloads) == 2
    assert "temperature" not in payloads[1]
    assert "max_tokens" not in payloads[1]
    assert payloads[1]["model"] == "openai/gpt-5.4-mini"
    assert payloads[1]["messages"][0]["role"] == "system"


def test_rate_limit_is_retried() -> None:
    calls: list[int] = []

    async def handler(request: web.Request) -> web.Response:
        await request.json()
        calls.append(1)
        if len(calls) == 1:
            return web.json_response({"detail": "Rate limit exceeded"}, status=429)
        return web.json_response(OK_RESPONSE)

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    assert asyncio.run(scenario()) == "Ответ модели"
    assert len(calls) == 2


def test_persistent_400_without_optional_params_raises() -> None:
    calls: list[int] = []

    async def handler(request: web.Request) -> web.Response:
        await request.json()
        calls.append(1)
        return web.json_response({"detail": "Bad request"}, status=400)

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    with pytest.raises(AIClientError) as exc:
        asyncio.run(scenario())

    # один исходный запрос + один без temperature/max_tokens, дальше не ретраим
    assert len(calls) == 2
    assert "Bad request" in str(exc.value)
    assert exc.value.status == 400


def test_balance_error_surfaces_detail() -> None:
    async def handler(request: web.Request) -> web.Response:
        await request.json()
        return web.json_response({"detail": "Недостаточно средств на балансе"}, status=402)

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    with pytest.raises(AIClientError) as exc:
        asyncio.run(scenario())

    assert "Недостаточно средств на балансе" in str(exc.value)
    assert exc.value.status == 402


def test_upstream_error_message_extracted() -> None:
    async def handler(request: web.Request) -> web.Response:
        await request.json()
        return web.json_response(
            {"error": {"message": "The model `nope` does not exist", "type": "invalid"}},
            status=404,
        )

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    with pytest.raises(AIClientError) as exc:
        asyncio.run(scenario())

    assert "The model `nope` does not exist" in str(exc.value)
    assert exc.value.status == 404


def test_retries_exhausted_on_server_error() -> None:
    calls: list[int] = []

    async def handler(request: web.Request) -> web.Response:
        await request.json()
        calls.append(1)
        return web.json_response({"detail": "Service unavailable"}, status=503)

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base, max_retries=2))

    with pytest.raises(AIClientError) as exc:
        asyncio.run(scenario())

    assert len(calls) == 3  # первая попытка + два повтора
    assert exc.value.status == 503


def test_empty_content_is_an_error() -> None:
    async def handler(request: web.Request) -> web.Response:
        await request.json()
        return web.json_response({"choices": [{"message": {"content": "   "}}]})

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    with pytest.raises(AIClientError) as exc:
        asyncio.run(scenario())
    assert "Пустой ответ модели" in str(exc.value)


def test_unexpected_shape_is_an_error() -> None:
    async def handler(request: web.Request) -> web.Response:
        await request.json()
        return web.json_response({"foo": "bar"})

    async def scenario() -> str:
        async with api_server(handler) as base:
            return await _ask(make_client(base))

    with pytest.raises(AIClientError) as exc:
        asyncio.run(scenario())
    assert "Неожиданный формат ответа" in str(exc.value)


def test_connection_error_is_wrapped_after_retries() -> None:
    # порт, на котором никто не слушает
    dead_port = free_port()
    client = make_client(f"http://127.0.0.1:{dead_port}/v1", max_retries=2)

    with pytest.raises(AIClientError) as exc:
        asyncio.run(_ask(client))

    assert "Сетевая ошибка" in str(exc.value)
