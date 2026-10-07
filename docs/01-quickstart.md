# 01. Первый бот и API

Источник: <https://vkbottle.readthedocs.io/ru/latest/tutorial/first-bot/>, <https://vkbottle.readthedocs.io/ru/latest/low-level/api/>

## API — запросы к ВКонтакте

`API` — готовый инструмент для запросов к API ВКонтакте, с полной типизацией ([vkbottle/types](https://github.com/vkbottle/types)).

```python
from vkbottle import API
```

Все вызовы методов — через `await`:

```python
import asyncio
from vkbottle import API

async def main():
    api = API("token")
    await api.wall.post(message="#vkbottle прекрасен!")

asyncio.run(main())
```

Инициализация: строка (токен), лист строк (токены → автоматически конвертируются в token-generator) или готовый генератор.

```python
api = API(token="token")
await api.messages.send(peer_id=1, message="Привет Павел Дуров!")
```

> **Внимание.** Все методы в vkbottle пишутся *снейк-кейсом*. Например, метод [`messages.getById`](https://dev.vk.ru/method/messages.getById) пишется как `api.messages.get_by_id`.

### Параметры `API`

- **token** — токен сообщества/пользователя или [генератор токенов](https://vkbottle.readthedocs.io/ru/latest/low-level/api/token-generator/)
- **ignore_error** — игнорировать ошибки VK API
- **http_client** — клиент для запросов
- **request_rescheduler** — рещедулер запросов

### Captcha-хендлер

Должен решить капчу и вернуть её код:

```python
from vkbottle import CaptchaError

bot = ...

async def captcha_handler(e: CaptchaError):
    ...
    return code

bot.api.add_captcha_handler(captcha_handler)
```

### Метода нет во фреймворке?

Используйте `API.request`, `Bot.api.request` или `Message.ctx_api.request` — вернёт **словарь** с json-ответом, а не типизированный объект:

```python
import asyncio
from vkbottle.api import API

api = API("token")

async def main():
    await api.request("users.get", {})  # Single request

    # Multiple request for one session
    async for response in api.request_many(
        [api.APIRequest("users.get", {}), api.APIRequest("groups.get", {})]
    ):
        print(response)

asyncio.run(main())
```

Для бота:

```python
import asyncio
from vkbottle.bot import Bot

bot = Bot("token")

async def main():
    print(await bot.api.request("users.get", {}))  # Single request
    # Multiple request for one session
    async for response in bot.api.request_many(
        [bot.api.APIRequest("users.get", {}), bot.api.APIRequest("groups.get", {})]
    ):
        print(response)

asyncio.run(main())
```

Доступ к API из хендлера — через `message.ctx_api`:

```python
from vkbottle.bot import Bot, Message

bot = Bot(token="token")
admin_ids = [1, 100]

@bot.on.message(text="админы")
async def who_admins(message: Message):
    admins = [f"{adm.first_name} {adm.last_name}" for adm in (await message.ctx_api.users.get(admin_ids))]
    print((await message.ctx_api.request("users.get", {"user_ids": admin_ids})))
    await message.answer(f"Администраторы этого бота: {' '.join(admins)}")

bot.run_forever()
```

> В мультиботе `bot.api` недоступен — API получается из `event.ctx_api`.

---

## Первый бот

Импорт `Bot` из корня проекта (`vkbottle`) или из пакета `bot`:

```python
from vkbottle.bot import Bot
```

> **Bot — класс исключительно для групп.** Для юзербота см. [User](https://vkbottle.readthedocs.io/ru/latest/high-level/user/).

Инициализация обязательным аргументом `token` **или** `api`:

```python
# Инициализация токеном
bot = Bot(token="token")
# (или) Инициализация с апи
bot = Bot(api=api)
```

Готовый бот:

```python
from vkbottle.bot import Bot, Message

bot = Bot(token="token")

@bot.on.message(text="Привет")
async def hi_handler(message: Message):
    users_info = await bot.api.users.get(message.from_id)
    await message.answer("Привет, {}".format(users_info[0].first_name))

bot.run_forever()
```

### Разбор

- `@bot.on.message(text="Привет")` — декоратор: если сообщение отвечает правилам (`text="привет"`), сработает хендлер под ним. `bot.on` — псевдоним `bot.labeler`.
- `async def hi_handler(message: Message)` — хендлер; аргумент `message` обязателен, это объект события.
- `await bot.api.users.get(message.from_id)` — запрос к API.
- `await message.answer(...)` — шорткат ответа: аргументы идентичны `messages.send`, но **не требуют** `peer_id` и `random_id`.
- `bot.run_forever()` — синхронный запуск из обычной (не асинхронной) среды.

> Если код не работает — проверьте галочки в настройках лонгпола (событие «новые сообщения») и сам лонгпол; стабильная версия API — `5.131`.

### Три декоратора сообщений

| Декоратор | Обрабатывает |
|---|---|
| `.message` | и беседы, и личные переписки |
| `.private_message` | только личные переписки |
| `.chat_message` | только беседы |

На деле это просто предустановленный `PeerRule`:
- в `message` не предустанавливается
- в `chat_message` — `PeerRule(True)`
- в `private_message` — `PeerRule(False)`

---

## Варианты запуска

См. подробно: [02-longpoll.md](02-longpoll.md).

```python
bot.run_forever()   # синхронный запуск longpoll
```

```python
await bot.run_polling()  # асинхронный запуск longpoll (в своей async-среде)
```

---

## Примеры из документации

- [easy-bot](https://github.com/vkbottle/vkbottle/tree/master/examples/high-level/easy_bot.py)
- [uploaders_example](https://github.com/vkbottle/vkbottle/tree/master/examples/high-level/uploaders_example.py)
