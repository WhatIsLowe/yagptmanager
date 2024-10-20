import asyncio

import aiohttp
import logging
from typing import Optional, List, Dict, Tuple
from enum import StrEnum
from pydantic import BaseModel

from ..exceptions import (
    YaGptException,
    TokenLimitExceeded,
    InvalidResponse,
    RedisConnectionError,
    RequestTimeoutException,
    TokenizationError,
)

from ..prompt.base import BasePromptCleaner
from ..cache.base import BaseCache
from ..context.base import BaseContextManager
from ..tokenizer.base import BaseTokenizer

from ..auth import AuthManager
from ..context import ContextManager
from ..cache import CacheManager
from ..prompt import PromptManager
from ..tokenizer import Tokenizer
from ..types import MessageContext, Role


class Message(BaseModel):
    role: Role
    text: str


class YaGptManager:
    """Менеджер для работы с YandexGPT API.

    :param service_account_key: Авторизованный ключ сервисного аккаунта YandexCloud в формате JSON.
    :param gpt_role: Роль для GPT модели.
    :param yc_folder_id: ID папки YandexCloud.
    :param redis_dsn: DSN для подключения к Redis.
    :param tokenizer: (опционально) Класс токенизатора. Использовать только для кастомных классов.
    :param context_manager: (опционально) Класс для работы с контекстом. Использовать только для кастомных классов.
    :param cache_manager: (опционально) Класс для работы с кэшем. Использовать только для кастомных классов.
    :param prompt_manager: (опционально) Класс для работы с текстом запроса. Использовать только для кастомных классов.
    :param max_tokens: Максимальная стоимость контекста. По-умолчанию, 7500 токенов.
    :param max_context_messages: Максимальное количество сообщений в контексте. По-умолчанию, 5 сообщений.
    :param async_mode: Режим работы с YandexGPT. При синхронной работе: запросы к GPT выполняются последовательно -
    более быстрый ответ для отдельных запросов. При асинхронной работе: запросы к GPT добавляются в очередь и им
    присваивается ID операции - более долгий ответ для отдельных запросов, но позволяет выполнять несколько запросов
    одновременно.
    :param logger: (опционально) кастомный логгер.
    :param async_timeout: Таймаут ожидания готовности ответа для асинхронных запросов. По-умолчанию, 60 секунд.
    """

    base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1"

    def __init__(
        self,
        service_account_key: dict,
        gpt_role: str,
        yc_folder_id: str,
        redis_dsn: str,
        tokenizer: Optional[BaseTokenizer] = None,
        context_manager: Optional[BaseContextManager] = None,
        cache_manager: Optional[BaseCache] = None,
        prompt_manager: Optional[BasePromptCleaner] = None,
        max_tokens: int = 7500,
        max_context_messages: int = 5,
        async_mode: bool = False,
        logger: Optional[logging.Logger] = None,
        async_timeout: int = 60,
    ):
        self._gpt_role = gpt_role
        self._max_tokens = max_tokens
        self._max_context_messages = max_context_messages
        self._async_mode = async_mode
        self._async_timeout = async_timeout
        self.logger = logger or logging.getLogger(__name__)
        self._model_uri = f"gpt://{yc_folder_id}/yandexgpt-lite/latest"

        self._cache_manager = cache_manager or CacheManager(redis_dsn)
        self._context_manager = context_manager or ContextManager(self._cache_manager, max_context_messages, max_tokens)
        self._prompt_manager = prompt_manager or PromptManager()
        self._auth_manager = AuthManager(service_account_key=service_account_key)

        self._headers = {"Content-Type": "application/json", "x-folder-id": yc_folder_id}

        self._system_message = {
            "role": Role.SYSTEM.value,
            "text": self._gpt_role,
        }
        self._system_tokens = None
        self._role_tokens = None
        self._tokenizer = tokenizer or Tokenizer(self._model_uri, self._max_tokens)

    async def initialize(self):
        """Инициализирует"""

        iam_token = await self._auth_manager.get_token()
        self._role_tokens = await self._tokenizer.tokenize(self._gpt_role, iam_token)
        self.logger.debug(f"Токены роли YaGpt: {self._role_tokens}")

    async def _make_request(self, url: str, payload: dict) -> dict:
        """Формирует запрос и возвращает JSON ответ.

        :param url: URL запроса.
        :param payload: Тело запроса.
        :return: JSON ответ.
        """
        logging.debug(f"PAYLOAD: {payload}")
        try:
            # Получаем IAM токен и обновляем заголовки
            token = await self._auth_manager.get_token()
            headers = self._headers.copy()
            headers["Authorization"] = f"Bearer {token}"

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        err_text = await response.text()
                        raise InvalidResponse(f"Ошибка при запросе к Yandex GPT API: {response.status}: {err_text}")

                    if self._async_mode:
                        # При асинхронном запросе к YandexGPT - возвращается ответ с ID операции
                        operation_id = (await response.json())["id"]
                        response = await self._get_async_result(operation_id, token)
                        return response

                    return await response.json()

        except asyncio.TimeoutError as e:
            raise RequestTimeoutException(f"Таймаут запроса к Yandex GPT API: {e}") from e
        except aiohttp.ClientError as e:
            raise YaGptException(f"Ошибка соединения: {e}") from e

    async def _get_async_result(self, operation_id: str, token: str) -> dict:
        """Отслеживает статус асинхронного ответа YandexGPT.

        :param operation_id: ID операции, полученный в ответе на асинхронный запрос Yandex GPT.
        :param token: IAM токен.
        :return: JSON ответ.
        """

        url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
        headers = self._headers.copy()
        headers["Authorization"] = f"Bearer {token}"

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with asyncio.timeout(self._async_timeout):
                    while True:
                        await asyncio.sleep(1)
                        async with session.get(url) as response:
                            if response.status != 200:
                                raise InvalidResponse(
                                    f"Ошибка при получении результата асинхронного запроса: {response.status}: {await response.text()}"
                                )
                            self.logger.debug(f"Запрос статуса асинхрон: {response.status} | {await response.json()}")
                            operation_data = await response.json()
                            if operation_data["done"]:
                                return operation_data["response"]

            except asyncio.TimeoutError:
                raise RequestTimeoutException(
                    f"Превышено время ожидания ответа от Yandex GPT API (operation_id: {operation_id})"
                )

    async def _prepare_context(self, prompt: str, session_id: str, token: str) -> List[Dict]:
        """Очищает запрос и формирует контекст

        :param prompt: Текст запроса.
        :param session_id: ID сессии в кэше.
        :param token: IAM токен.
        :return: Общий контекст в виде списка словарей.
        """

        # Очищает запрос от запрещенных знаков
        if self._prompt_manager:
            prompt = self._prompt_manager.clean(prompt)
        # Вычисляет стоимость запроса в токенах
        prompt_tokens = await self._tokenizer.tokenize(prompt, token)
        # Обновляет контекст в кэше
        context = await self._context_manager.update_context(
            session_id, MessageContext(role=Role.USER, text=prompt, tokens=prompt_tokens)
        )
        return context

    async def get_answer(self, prompt: str, session_id: str) -> str:
        """Отвечает на запрос.

        :param prompt: Текст запроса.
        :param session_id: ID сессии в кэше.
        :return: Текст ответа на запрос.
        """
        token = await self._auth_manager.get_token()
        context = await self._prepare_context(prompt, session_id, token)
        body = {
            "modelUri": self._model_uri,
            "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": "500"},
            "messages": [self._system_message] + context,
        }
        response = await self._make_request(
            url=self.base_url + "/completionAsync" if self._async_mode else "/completion",
            payload=body,
        )

        answer_tokens = response["usage"]["completionTokens"]
        answer = response["alternatives"][0]["message"]["text"]
        _ = await self._context_manager.update_context(
            session_id, MessageContext(role=Role.ASSISTANT, text=answer, tokens=answer_tokens)
        )
        return answer
