from abc import ABC, abstractmethod
from ..types import MessageContext


class BaseContextManager(ABC):
    """Абстрактный базовый класс для менеджера контекста"""

    @abstractmethod
    async def get_context(self, session_id: str) -> str:
        """Метод получения контекста

        :param session_id: Идентификатор сессии

        :returns Контекст данной сессии
        """
        pass

    @abstractmethod
    async def update_context(self, session_id: str, new_message: MessageContext):
        """Метод обновления контекста

        :param session_id: Идентификатор сессии
        :param new_message: Новое сообщение для добавления в контекст
        """
        pass
