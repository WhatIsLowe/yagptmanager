from enum import StrEnum
from pydantic import BaseModel


class MessageContext(BaseModel):
    role: str
    text: str
    tokens: int


class Role(StrEnum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
