# Выжимка документации VKBottle

Локальная копия ключевых разделов документации фреймворка **vkbottle** (проверено на установленной версии `4.11.0`).

Источник: <https://vkbottle.readthedocs.io/ru/latest/>
Все примеры кода ниже взяты из документации и примеров, на которые она ссылается. Ничего не выдумано.

## Содержание

| Файл | Раздел документации | Что внутри |
|---|---|---|
| [01-quickstart.md](01-quickstart.md) | `tutorial/first-bot` | API, первый бот, запуск |
| [02-longpoll.md](02-longpoll.md) | `low-level/polling`, `high-level/bot` | **LongPoll API — как бот получает события** |
| [03-handlers-labeler.md](03-handlers-labeler.md) | `high-level/handling/handler`, `bot/labeler` | Хендлеры, лейблер, декораторы |
| [04-rules.md](04-rules.md) | `tutorial/rules`, `high-level/builtin-rules` | Правила + все встроенные правила |
| [05-keyboards-attachments.md](05-keyboards-attachments.md) | `tutorial/keyboards-attachments`, `tools/keyboard`, `tools/template` | Клавиатуры, вложения, шаблоны |
| [06-middlewares.md](06-middlewares.md) | `tutorial/middlewares-return-managers`, `high-level/handling/middleware` | Мидлвари и return-менеджеры |
| [07-states.md](07-states.md) | `high-level/handling/state-dispenser`, `tools/waiter-machine` | Стейт-машины и waiter |
| [08-errors.md](08-errors.md) | `tutorial/error-handling`, `low-level/exception_handling` | VKAPIError, ErrorHandler |
| [09-code-separation.md](09-code-separation.md) | `tutorial/code-separation` | Структура проекта, отдельные лейблеры |
| [10-low-level-api.md](10-low-level-api.md) | `low-level/api`, `http-client` | API, HTTP-клиент, токены, валидаторы |
| [11-tools.md](11-tools.md) | `tools/*` | Formatting, Storage, VKScript, LoopWrapper, Uploaders, MessageEvent |
| [12-callback-api.md](12-callback-api.md) | `tutorial/callback-bot`, `low-level/callback` | Callback API (вебхуки) |
| [13-faq.md](13-faq.md) | `tutorial/faq`, `modules`, `whats_new` | Asyncio-ловушки, FAQ, кастомизация |

## Быстрая шпаргалка

```python
from vkbottle.bot import Bot, Message

bot = Bot(token="token")

@bot.on.message(text="Привет")
async def hi_handler(message: Message):
    users_info = await bot.api.users.get(message.from_id)
    await message.answer("Привет, {}".format(users_info[0].first_name))

bot.run_forever()
```

- Хендлеры: `.message` (везде), `.private_message` (ЛС), `.chat_message` (беседа)
- Правила-шорткаты в декораторе: `text=`, `command=`, `regexp=`/`regex=`, `payload=`, `state=`, `from_chat=`, `func=`
- Запуск: `bot.run_forever()` (синхронный) или `await bot.run_polling()` (асинхронный)
- Методы API — только в `snake_case`: `messages.getById` → `api.messages.get_by_id`
- Не используйте `requests` / `time.sleep` — только `aiohttp` / `await asyncio.sleep`
