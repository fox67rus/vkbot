# 13. FAQ, asyncio-ловушки и кастомизация

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/tutorial/faq/>
- <https://vkbottle.readthedocs.io/ru/latest/modules/>
- <https://vkbottle.readthedocs.io/ru/latest/whats_new/4.0/>, <https://vkbottle.readthedocs.io/ru/latest/whats_new/4.3/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/user/>

## Asyncio: обязательные правила

### Писать `await` перед async-функцией, иначе она не запустится

```python
import asyncio

async def get_banana() -> str:
    return "banana"

async def main():
    print(get_banana())    # <coroutine object get_banana at 0x...>
    print(await get_banana())  # banana
```

### `await` — только внутри async-функций

```python
# bad
async def foo() -> str:
    return "foo"

def main():
    print(await foo())  # SyntaxError: 'await' outside async function

main()
```

```python
# bad
async def main():
    print("main")
    await main()  # SyntaxError: 'await' outside function
```

```python
# good
import asyncio

async def foo() -> str:
    return "foo"

async def main():
    print(await foo())

asyncio.run(main())
```

### Блокировки

В асинхронном программировании «блокирующие» — все функции без `await`, работающие по принципу IO. Не все они плохи, главное — не злоупотреблять. Если заблокировать выполнение надолго, бот зависнет.

| ❌ Плохо | ✅ Хорошо |
|---|---|
| `time.sleep(10)` | `await asyncio.sleep(10)` |
| `requests`, `urllib3`, `vk_api` и производные | `aiohttp` или встроенный `AiohttpClient` |

```python
# bad
async def send_httpbin_get() -> dict[str, Any]:
    r = requests.get('http://httpbin.org/get')
    if r.status_code == 200:
        js = r.model_dump_json()
        return js
```

```python
# good, recommended
from vkbottle.http import AiohttpClient

async def send_httpbin_get() -> dict[str, Any]:
    http_client = AiohttpClient()
    return await http_client.request_json('http://httpbin.org/get')
```

```python
# good
import aiohttp

async def send_httpbin_get() -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get('http://httpbin.org/get') as r:
            if r.status == 200:
                js = await r.json()
                return js
```

---

## Какие методы есть во фреймворке

Всё, что есть в [официальной документации от vk.ru](https://dev.vk.ru/reference). Синтаксис методов, параметры и ошибки аналогичны, только методы пишутся в **snake_case**, а не camelCase.

```python
from vkbottle.api import API

api = API("token")

# https://api.vk.ru/method/account.ban
await api.account.ban(owner_id=1)

# https://api.vk.ru/method/account.getBanned
await api.account.get_banned(offset=0, count=1)
```

Все официальные методы, ответы и ошибки **типизированы**.

---

## Как получить токен

- **Пользовательский:** самый простой способ — [vkhost.github.io](https://vkhost.github.io), либо `UserAuth` (см. [11-tools.md](11-tools.md#userauth--токен-пользователя))
- **Бота (сообщества):** [Бот Быстрый старт](https://dev.vk.ru/api/bots/getting-started)

> У токена бота не все методы доступны в отличие от пользовательского.

---

## Метода нет во фреймворке — `api.request`

См. подробно: [01-quickstart.md](01-quickstart.md#метода-нет-во-фреймворке)

```python
print(await bot.api.request("users.get", {}))
```

Возвращает **словарь** с json-ответом, а не типизированный объект.

---

## `Pydantic.error_wrappers.ValidationError`

Объекты типизированы и генерируются на основе [официальной VK-API схемы](https://github.com/VKCOM/vk-api-schema). ВК обновляет её без предупреждений — из-за этого возможны поломки с валидацией.

Решение — обновить типы:

```
pip install git+https://github.com/vkbottle/types -U
```

Если не помогло — пишите issue (**в vkbottle**, не в types) или в чат ВК/Telegram.

---

## Кастомизация зависимостей

VKBottle автоматически выбирает лучшую альтернативу для стандартных библиотек. Их **нет** в зависимостях — ставить самим.

### JSON (по убыванию приоритета)

`orjson` → `hyperjson` → `ujson` → `json`

### Logging (по убыванию приоритета)

`loguru` → `logging`

> Рекомендуется использовать `loguru` вместо `logging`. Возможно, он станет обязательной зависимостью в будущих релизах.

По умолчанию уровень логирования — **DEBUG**.

**logging:**
```python
import logging
logging.getLogger("vkbottle").setLevel(logging.INFO)
```

**loguru — установить уровень:**
```python
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")
```

Либо переменная окружения `LOGURU_LEVEL`.

**loguru — отключить полностью:**
```python
from loguru import logger

logger.disable("vkbottle")
```

---

## Изменения в vkbottle 4.0

- **Мидлвари:** `pre`/`post` больше не принимают аргумент message — доступ через `self.event`, тип указывается в дженерике.
- **Рулзы:** аргумент `message` переименован в `event`.
- **`CodeException`:** ошибка указывается в квадратных скобках — `VKAPIError[5]`.
- **Юзерботы:** добавлен класс `User`.

## Изменения в vkbottle 4.3

- `Message.get_full_message()` — получает полное сообщение из беседы по `conversation_message_id`. Полезно для работы с аттачментами (получение рабочих `access_key` или полное сообщение, если `Message.is_cropped == False`). Обновляет текущий объект и возвращает его.
- `Message.get_attachment_strings()` — аттачменты в виде строк для отправки. Желательно использовать вместе с `get_full_message()`.
- `Message.reply_message` и `Message.fwd_messages` заменены на объект `ForeignMessageMin`.
- Все объекты в `vkbottle-types` теперь **неизменяемы** — следствие: они хешируемы и могут использоваться в `set`.

---

## Юзербот (`User`)

> `User` (aka юзербот) реализован буквально «для галочки». Его использование запрещено несколькими [правилами ВКонтакте](https://vk.ru/terms) (п. 6.3.9, 6.7). Мы не несём ответственности за ваши аккаунты.

Из-за огромной разницы между `User Long Poll API` и `Bot Long Poll API` юзербот накладывает ограничения на сам фреймворк: универсальные типы не поддерживают специфичные функции, в `Rule` и `Middleware` нужно использовать дженерики.

Импортируется из `vkbottle.user`:
- `User`, `Blueprint`, `UserLabeler`, `Message`, `run_multibot`, `views`

Всё остальное идентично обычным ботам.

---

## Важно про запуск (vkbottle 4.11)

`bot.run_forever()` в 4.11 помечен как устаревший → используйте `bot.run()`. Подробнее: [02-longpoll.md](02-longpoll.md#запуск-longpoll).
