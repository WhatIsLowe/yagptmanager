import json
import logging
from collections import deque
from typing import List, Optional, Deque

from .base import BaseContextManager
from ..cache.base import BaseCache
from ..types import MessageContext

logger = logging.getLogger(__name__)


class ContextManager(BaseContextManager):
    """Менеджер управления контекстом.

    :param cache_manager: Класс управления кэшем.
    :param max_context_messages: Максимальное количество сообщений в контексте.
    :param max_tokens: Максимальная стоимость контекста в токенах.
    """

    def __init__(self, cache_manager: BaseCache, max_context_messages: int = 5, max_tokens: int = 7500):
        self.cache_manager = cache_manager
        self.max_context_messages = max_context_messages
        self.max_tokens = max_tokens

    async def get_context(self, session_id: str) -> Optional[List[dict]]:
        """Получает из кэша и возвращает контекст по ключу.

        :param session_id: ID сессии в кэше.
        :return: Список словарей с контекстом или None.
        """
        context_json = await self.cache_manager.get(f"context:{session_id}")
        logger.debug(f"Контекст для данной сессии {session_id}: {context_json}")

        if context_json is not None:
            try:
                context: List[dict] = json.loads(context_json)
                return context
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка десериализации контекста: {e}")
                return None
        return None

    async def update_context(self, session_id: str, new_message: MessageContext) -> List[dict]:
        """Обновляет/создает и возвращает контекст из кэша.

        Получает текущий контекст и, если текущий контекст + новое сообщение превышают максимальный лимит по количеству
        сообщений в контексте, или стоимость текущего контекста + стоимость нового сообщения превышают лимит - удаляет
        более старые сообщения из контекста до тех пор, пока не уложится в лимит.
        :param session_id: ID сессии в кэше.
        :param new_message: Новое сообщение для добавления в контекст.
        :return: Список словарей контекста.
        """

        # Формирует из контекста очередь сообщений (первый пришел - первый ушел)
        context: Deque[dict] = deque(await self.get_context(session_id) or [])

        # Если длина контекста превышает заданный максимум - удаляет более старые сообщения
        while len(context) >= self.max_context_messages:
            context.popleft()

        # Вычисляет стоимость всех сообщений контекста + стоимость нового сообщения.
        total_tokens = sum(msg["tokens"] for msg in context) + new_message.tokens
        logger.debug(f"total_tokens: {total_tokens}")
        # Если стоимость контекста превышает заданный максимум - удаляет более старые сообщения.
        while total_tokens >= self.max_tokens and context:
            removed_message = context.popleft()
            total_tokens -= removed_message["tokens"]

        # Преобразует очередь обратно в список словарей и добавляет новое сообщение
        context_list = list(context)
        context_list.append({"role": new_message.role, "text": new_message.text, "tokens": new_message.tokens})
        # Сохраняет контекст в кэше с TTL в 3600 секунд.
        await self.cache_manager.set(f"context:{session_id}", json.dumps(context_list), ttl=3600)
        logger.debug(f"Контекст для сессии {session_id} обновлен")
        return context_list
