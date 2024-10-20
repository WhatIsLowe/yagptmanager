import logging
import redis.asyncio as aioredis

from .base import BaseCache
from ..exceptions import RedisConnectionError

logger = logging.getLogger(__name__)


class CacheManager(BaseCache):
    """Менеджер кэша на основе Redis.

    :param redis_dsn: DSN строка для подключения к Redis.
    """

    def __init__(self, redis_dsn: str):
        self.redis = aioredis.from_url(redis_dsn, decode_responses=True)
        logger.debug(f"CacheManager инициализирован с Redis DSN: {redis_dsn}")

    async def get(self, key: str):
        try:
            value = await self.redis.get(key)
            logger.debug(f"Получено значение из кэша по ключу {key}: {value}")
            return value
        except Exception as e:
            logger.error(f"Ошибка при получении значения из Redis: {e}")
            raise RedisConnectionError(f"Ошибка подключения к Redis: {e}") from e

    async def set(self, key: str, value: str, ttl: int):
        try:
            await self.redis.set(key, value, ttl)
            logger.debug(f"Значение установлено в кэш по ключу {key} с TTL {ttl}")
        except Exception as e:
            logger.error(f"Ошибка при установке значения в Redis: {e}")
            raise RedisConnectionError(f"Ошибка записи в Redis: {e}") from e
