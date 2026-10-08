"""Общие помощники для тестов."""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from aiohttp import web

from vkbottle.tools.mini_types.bot import message_min


def free_port() -> int:
    """Свободный локальный порт (порт выбирается на короткое время)."""
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _bound_port(runner: web.BaseRunner) -> int:
    addresses = runner.addresses
    if not addresses:
        raise RuntimeError("Мок-сервер не поднялся")
    return int(addresses[0][1])


@asynccontextmanager
async def api_server(
    handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
    path: str = "/v1/chat/completions",
) -> AsyncIterator[str]:
    """Поднять мок-сервер ProxyAPI и вернуть ему базовый адрес."""
    app = web.Application()
    app.router.add_post(path, handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    try:
        # Клиент сам дописывает /chat/completions к базовому адресу
        yield f"http://127.0.0.1:{_bound_port(runner)}/v1"
    finally:
        await runner.cleanup()


def make_message(
    *,
    text: str = "",
    peer_id: int = 1,
    from_id: int = 1,
    group_id: int = 100,
    action: dict | None = None,
    payload: dict | str | None = None,
    replace_mention: bool = True,
):
    """Синтетическое сообщение в том виде, в каком его создаёт vkbottle."""
    message: dict = {
        "date": 1,
        "from_id": from_id,
        "id": 1,
        "peer_id": peer_id,
        "text": text,
        "conversation_message_id": 1,
        "out": 0,
        "version": 1,
        "fwd_messages": [],
    }
    if action is not None:
        message["action"] = action
    if payload is not None:
        # В API payload приходит строкой JSON
        message["payload"] = (
            payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        )

    event = {
        "type": "message_new",
        "v": "1",
        "group_id": group_id,
        "object": {"message": message, "client_info": {}},
    }
    return message_min(event, None, replace_mention)


def check(rule, message) -> bool:
    """Выполнить асинхронное правило над синтетическим сообщением."""
    return bool(asyncio.run(rule.check(message)))
