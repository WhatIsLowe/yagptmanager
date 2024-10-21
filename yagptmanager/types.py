from enum import StrEnum
from pydantic import BaseModel


class Role(StrEnum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


class MessageContext(BaseModel):
    """Контекст сообщения для занесения в кэш.

    role (yagptmanager.types.Role): system | assistant | user.\n
    text (str): Текст сообщения.\n
    tokens (int): Стоимость сообщения в токенах.
    """
    role: Role
    text: str
    tokens: int
