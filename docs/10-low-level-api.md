# 10. Low-level: API, HTTP-клиент, токены, валидаторы

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/low-level/api/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/http-client/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/api/token-generator/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/api/response-validator/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/api/request-rescheduler/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/api/request-validator/>

## API

```python
from vkbottle import API

# ...
api = API(token="token")
await api.messages.send(peer_id=1, message="Привет Павел Дуров!")
```

> **Внимание.** Все методы в vkbottle пишутся *снейк-кейсом*. `messages.getById` → `api.messages.get_by_id`.

### Параметры

- **token** — токен сообщества/пользователя или token-generator
- **ignore_error** — игнорировать ошибки VK API
- **http_client** — клиент для запросов
- **request_rescheduler** — рещедулер запросов

### Captcha-хендлер

```python
from vkbottle import CaptchaError

bot = ...

async def captcha_handler(e: CaptchaError):
    ...
    return code

bot.api.add_captcha_handler(captcha_handler)
```

---

## HTTP-Client

По умолчанию библиотека использует `SingleAiohttpClient` — его особенность в том, что он **всегда использует одну и ту же сессию**.

### Методы

| Метод | Что делает |
|---|---|
| `request_raw` | делает реквест; для aiohttp возвращает `aiohttp.ClientResponse` |
| `request_text` | делает реквест и читает поле `text` → `str` |
| `request_json` | делает реквест и десериализует json (через `choicelib` в порядке `json`, `ujson`, `hyperjson`, `orjson`) → `dict` |
| `request_content` | делает реквест и читает `content` → `bytes` (используется для скачивания медиа в аплоадерах) |

### Параметры

- `url` — ссылка
- `method` — HTTP метод (например `get`)
- `data` — данные запроса
- `**kwargs` — передаются как параметры в запросе

### Параметры инициализации `AiohttpClient`

- `session` — объект сессии (если не указан — создаётся новый)
- `json_processing_module` — модуль для десериализации json
- `optimize` — при `True` в конструктор сессии передаются `raise_for_status=True` и `skip_auto_headers={"User-Agent"}`
- `**session_params` — kwargs в конструктор сессии (можно передать `headers`, `cookies`)

### Пример

```python
from vkbottle.http import AiohttpClient

# ...
http_client = AiohttpClient()
await http_client.request_text("https://google.com")
```

Кастомный клиент наследуется от `ABCHTTPClient` и имплементирует методы выше.

> Подробнее о параметрах сессии: [документация aiohttp](https://docs.aiohttp.org/en/stable/client_reference.html)

---

## Token-Generator

У ВК есть лимиты на запросы, но они легко обходятся при нескольких токенах. Токен-генераторы автоматически распределяют токены по запросам.

| Генератор | Описание |
|---|---|
| `SingleTokenGenerator` | один токен на все запросы, принимает строку |
| `ConsistentTokenGenerator` | несколько токенов поочерёдно, принимает лист из строк |

> Для грамотного использования `ConsistentTokenGenerator` нужно рассчитать нагрузку по времени. Лимит ВК: **для ботов — 25/сек, для пользователей — 3/сек**.

Свой генератор — на базе [ABCTokenGenerator](https://github.com/vkbottle/vkbottle/blob/master/vkbottle/api/token_generator/abc.py).

---

## Response Validator

Валидации ответов ВК нужны от случаев, когда сервер возвращает html вместо json, до правильно сформированной ошибки после запроса.

### Стандартные валидаторы

| Валидатор | Действие |
|---|---|
| `JSONValidator` | парсит json самым правым парсером [из списка](https://vkbottle.readthedocs.io/ru/latest/modules/). Если вернулся необрабатываемый тип (например `NoneType`) — запускает `Request Rescheduler`, пока не будет получен валидный ответ |
| `VKErrorValidator` | вызывает `VKAPIError` от `CodeException` при респонсе с ошибкой от ВК |

### Свой валидатор

Пример с `response_validators` из `API` и `SomeRequestRescheduler`:

```python
from typing import TYPE_CHECKING, Any, NoReturn, Union
from vkbottle import API, ABCResponseValidator
from .request_rescheduler import SomeRequestRescheduler

if TYPE_CHECKING:
    from vkbottle.api import ABCAPI, API

class SomeResponseValidator(ABCResponseValidator):
    async def validate(
        self,
        method: str,
        data: dict[str, Any],
        response: Any,
        ctx_api: "ABCAPI | API",
    ) -> Any | NoReturn:
        if "error" not in response:
            return response
        if ctx_api.ignore_errors:
            return None
        if response["error"]["error_code"] != 6:
            return response
        # Обрабатываем ошибку 6, которая возникает при слишком частых запросах
        return await SomeRequestRescheduler().reschedule(
            ctx_api, method, data, response
        )

api = API("token")
# Этот валидатор должен идти после JSONResponseValidator,
# но раньше VKAPIErrorResponseValidator, чтобы он не обработал эту ошибку
api.response_validators.insert(1, SomeResponseValidator())
```

> Опечатка в документации: в сигнатуре `data: dict[str, Any]:` должен быть запятая.

См. также: [Request Rescheduler](https://vkbottle.readthedocs.io/ru/latest/low-level/api/request-rescheduler/), [Request Validator](https://vkbottle.readthedocs.io/ru/latest/low-level/api/request-validator/)
