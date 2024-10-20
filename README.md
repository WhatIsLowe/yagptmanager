# YaGptManager

## Установка
```bash
pip install
```
<hr>

## Использование

```Python
from yagptmanager import YaGptManager

yagpt = YaGptManager(
    service_account_key={}, # YOUR_YC_SERVICE_ACCOUNT_KEY
    yc_folder_id="YOUR_YC_FOLDER_ID",
    gpt_role="YOUR_GPT_ROLE",
    redis_dsn="YOUR_REDIS_DSN",
    async_mode=True,
)
yagpt.initialize()

yagpt.get_answer("YOUR_ANSWER", "SESSION_ID")
```