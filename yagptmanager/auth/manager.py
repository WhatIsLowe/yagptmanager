import asyncio
import json
import logging
from typing import Optional
import time
import aiohttp
import jwt
from jwt import InvalidTokenError
from cryptography.hazmat.primitives import serialization

from ..exceptions import YaGptException

logger = logging.getLogger(__name__)


class AuthManager:
    """Менеджер для получения и обновления IAM токенов с использованием сервисного аккаунта

    :param service_account_key: Авторизованный ключ сервисного аккаунта в формате JSON
    """

    IAM_TOKEN_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"

    def __init__(self, service_account_key: dict):
        self._service_account_key = service_account_key
        self._token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._lock = asyncio.Lock()
        self._service_account_id: Optional[str] = None
        self._private_key: Optional[bytes] = None
        self._validate_and_load_key()

    def _validate_and_load_key(self) -> None:
        """Проверяет наличие необходимых полей и загружает приватный ключ"""

        required_fields = ["id", "service_account_id", "created_at", "key_algorithm", "public_key", "private_key"]

        missing_fields = [field for field in required_fields if field not in self._service_account_key]
        if missing_fields:
            logger.error(f"Отсутствуют необходимые поля в ключе сервисного аккаунта: {missing_fields}")
            raise YaGptException(f"Отсутствуют необходимые поля в ключе сервисного аккаунта: {missing_fields}")

        key_algorithm = self._service_account_key.get("key_algorithm")
        if key_algorithm not in ["RSA_2048", "RSA_4096"]:
            logger.error("Неподдерживаемый алгоритм ключа. Ожидались 'RSA_2048' или 'RSA_4096'")
            raise YaGptException("Неподдерживаемый алгоритм ключа. Ожидались 'RSA_2048' или 'RSA_4096'")

        self._service_account_id = self._service_account_key.get("service_account_id")
        private_key_pem = self._service_account_key.get("private_key")
        self._private_key = private_key_pem.encode("utf-8")
        logger.debug("Ключ сервисного аккаунта загружен!")

    def _create_jwt(self) -> str:
        """Создает и подписывает JWT для аутентификации"""
        if not self._service_account_id or not self._private_key:
            logger.error("Сервисный аккаунт не загружен")
            raise YaGptException("Сервисный аккаунт не загружен")

        now = int(time.time())
        payload = {
            "iss": self._service_account_id,
            "sub": self._service_account_id,
            "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            "iat": now,
            "exp": now + 3600,
        }

        try:
            private_key = serialization.load_pem_private_key(self._private_key, password=None)
            headers = {"kid": self._service_account_key["id"]}
            jwt_encoded = jwt.encode(payload, private_key, algorithm="PS256", headers=headers)
            logger.debug(f"JWT успешно создан и подписан: {jwt_encoded}")
            return jwt_encoded
        except (ValueError, InvalidTokenError) as e:
            logger.error(f"Ошибка при создании JWT: {e}")
            raise YaGptException(f"Ошибка при создании JWT: {e}") from e

    async def _fetch_token(self) -> None:
        """Получает новый IAM токен, используя подписанный JWT"""
        jwt_token = self._create_jwt()

        payload = {"jwt": jwt_token}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.IAM_TOKEN_URL, json=payload) as response:
                    if response.status != 200:
                        err_text = await response.text()
                        logger.error(f"Ошибка при получении IAM токена: {response.status}: {err_text}")
                        raise YaGptException(f"Ошибка при получении IAM токена: {response.status}: {err_text}")

                    data = await response.json()
                    self._token = data["iamToken"]
                    expires_in = data.get("expiresIn", 43200)  # По умолчанию 12 часов
                    # Период обновления токена устанавливаем на 10 минут раньше
                    self._token_expiry = time.time() + expires_in - 600
                    logger.debug("Получен новый IAM токен")

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка соединения при получении IAM токена: {e}")
            raise YaGptException(f"Ошибка соединения при получении IAM токена: {e}") from e

    async def get_token(self) -> str:
        """Возвращает действительный IAM токен, обновляя его при необходимости"""

        async with self._lock:
            current_time = time.time()
            if not self._token or not self._token_expiry or current_time >= self._token_expiry:
                await self._fetch_token()
            else:
                logger.debug("Используется действующий IAM токен")
            return self._token
