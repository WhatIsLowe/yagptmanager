from abc import ABC, abstractmethod


class BaseCache(ABC):
    """Абстрактный базовый класс для управления кэшем"""

    @abstractmethod
    async def get(self, key: str):
        """Метод для получения значения из кэша"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int):
        """Метод для установки значения в кэш"""
        pass
