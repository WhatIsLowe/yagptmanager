from abc import ABC, abstractmethod
from typing import Optional


class BaseTokenizer(ABC):
    """Базовый абстрактный класс для вычисления количества токенов"""

    @abstractmethod
    async def tokenize_completion(self, messages: dict, token: Optional[str]) -> int:
        """Подсчитывает количество токенов в контексте"""

    @abstractmethod
    async def tokenize(self, text: str, token: Optional[str]) -> int:
        """Подсчитывает количество токенов в тексте"""
