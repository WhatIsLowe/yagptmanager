class YaGptException(Exception):
    """Базовое исключение YaGPT"""


class TokenLimitExceeded(YaGptException):
    """Превышен лимит токенов"""


class InvalidResponse(YaGptException):
    """Некорректный ответ от API"""


class RedisConnectionError(YaGptException):
    """Ошибка подключения к Redis"""


class RequestTimeoutException(YaGptException):
    """Время ожидания ответа истекло"""


class TokenizationError(YaGptException):
    """Ошибка при токенизации промпта"""


class EmptyTextError(YaGptException):
    """Попытка отправить пустой тескт"""
