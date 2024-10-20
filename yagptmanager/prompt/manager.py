import logging
import re
import emoji
import unicodedata

from .base import BasePromptCleaner
from ..exceptions import EmptyTextError

logger = logging.getLogger(__name__)


class PromptManager(BasePromptCleaner):
    def clean(self, prompt: str) -> str:
        """Очищает промпт от запрещенных(ненужных) символов.

        :param prompt: Текст запроса.
        :return: Очищенный текст запроса.
        """
        logger.debug(f"Очистка промпта: {prompt}")

        # Удаление эмодзи
        prompt = emoji.replace_emoji(prompt, replace="")

        # Удаление диакритических знаков
        prompt = unicodedata.normalize("NFD", prompt)
        prompt = "".join(char for char in prompt if unicodedata.category(char) != "Mn")

        # Удаление спецсимволов, кроме основных пунктуационных знаков
        prompt = re.sub(r"[^\w\s.,!?-]", "", prompt)

        # Удаление лишних пробелов до и после текста
        prompt = re.sub(r"\s+", " ", prompt).strip()

        # Если итоговый промпт пуст - выбрасывает исключение
        if not prompt or prompt == "":
            raise EmptyTextError("Отправка пустого сообщения или сообщение состоит только из запрещенных символов")

        logger.debug(f"Очищенный промпт: {prompt}")
        return prompt
