from abc import ABC, abstractmethod


class BasePromptCleaner(ABC):
    """Базовый абстрактный класс для очистки промпта"""

    @abstractmethod
    def clean(self, prompt: str) -> str:
        """Очищает промпт перед отправкой

        :param prompt: Исходный текст промпта

        :returns Очищеный текст промпта
        """
