"""Служебные мидлвари."""

from __future__ import annotations

import logging

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

logger = logging.getLogger(__name__)


class MessageLogMiddleware(BaseMiddleware[Message]):
    """Логирует входящие сообщения и сработавшие хендлеры."""

    async def pre(self) -> None:
        event = self.event
        logger.debug(
            "Входящее сообщение: peer=%s from=%s text=%r",
            event.peer_id,
            event.from_id,
            (event.text or "")[:80],
        )

    async def post(self) -> None:
        if not self.handlers:
            return
        logger.debug("Сработало хендлеров: %s", len(self.handlers))
