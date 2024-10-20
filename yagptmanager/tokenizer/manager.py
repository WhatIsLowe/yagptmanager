from aiohttp import ClientSession
import logging
from typing import List

from .base import BaseTokenizer
from ..exceptions import TokenizationError

logger = logging.getLogger(__name__)


class Tokenizer(BaseTokenizer):
    """Класс для вычисления стоимости текста в токенах.

    :param model_uri: Ссылка на модель.
    :param max_tokens: Максимальное количество токенов.
    """

    url_completion: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion"
    url: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize"

    def __init__(self, model_uri: str, max_tokens: int):
        self.model_uri = model_uri
        self.max_tokens = max_tokens

    async def _make_request(self, url: str, body: dict, token: str) -> int:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

        async with ClientSession(headers=headers) as session:
            async with session.post(url=url, json=body) as response:
                if response.status != 200:
                    raise TokenizationError(f"Ошибка при токенизации: {response.status} {await response.text()}")
                data = await response.json()
                token_count = len(data["tokens"])
                logger.debug(f"Количество токенов: {token_count}")
                return token_count

    async def tokenize_completion(self, messages: List[dict], token: str) -> int:
        """Подсчитывает количество токенов в контексте с помощью API Yandex Cloud.

        :param messages: Контекст для токенизации.
        :param token: IAM токен.

        :return: Количество токенов в контексте.
        """

        payload = {
            "modelUri": self.model_uri,
            "CompletionOptions": {
                "stream": False,
                "maxTokens": self.max_tokens,
            },
            "messages": messages,
        }

        logger.debug(f"Запрос на токенизацию контекста: {payload}")
        return await self._make_request(self.url_completion, payload, token)

    async def tokenize(self, text: str, token: str) -> int:
        """Подсчитывает количество токенов в тексте с помощью API Yandex Cloud.

        :param text: Текст для токенизации.
        :param token: IAM токен.

        :return: Количество токенов в тексте
        """
        payload = {"modelUri": self.model_uri, "text": text}

        logger.debug(f"Запрос на токенизацию текста: {payload}")
        return await self._make_request(self.url, payload, token)
