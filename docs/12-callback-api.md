# 12. Callback API (вебхуки)

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/tutorial/callback-bot/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/callback/>

> **Обязательно к прочтению:** <https://dev.vk.ru/api/callback/getting-started>

## Требования

- Нужен **собственный сервер с доменным именем. DDNS работать не будет.**
- Подразумевается наличие опыта в настройке веб-серверов.

## Два способа получать события

| | LongPoll | Callback API |
|---|---|---|
| Сервер | не нужен | нужен свой, с доменом |
| Класс | `BotPolling` | `BotCallback` |
| Запуск | `bot.run()` / `bot.run_polling()` | свой сервер + `bot.process_event(event)` |
| Документация | [02-longpoll.md](02-longpoll.md) | этот файл |

---

## Подключение к сообществу

### 1. Инициализировать параметры

```python
import os

TOKEN = os.getenv("VK_TOKEN") # ключ сообщества
url = os.getenv("VK_URL") # url = "http://example.com/whateveryouwnant"
title = os.getenv("VK_TITLE") # title = "server"
secret_key = os.getenv("VK_SECRET_KEY") # опционально
```

### 2. Создать `BotCallback`

```python
from vkbottle.callback import BotCallback

callback = BotCallback(
    url = url,
    title = title)
```

### 3. Инициализировать бота

```python
from vkbottle import Bot

bot = Bot(token=TOKEN, callback=callback)
```

### 4. Настроить сервер и обрабатывать события

Любой сервер (`aiohttp`, `flask`, `fastapi`):

```python
# event - событие, полученное от vk
await bot.process_event(event)
```

> **Внимание.** После подключения бот будет обрабатывать входящие сообщения. Для получения остальных событий необходимо включить их в настройках сообщества.

Пример: [examples/high-level/callback_api/app.py](https://github.com/vkbottle/vkbottle/blob/master/examples/high-level/callback_api/app.py)

### Установка сервера программно

У `Bot` есть метод `bot.setup_webhook()` — устанавливает сервер для `CallbackAPI` в сообщество.

---

## Методы `ABCCallback`

| Метод | Описание |
|---|---|
| `add_callback_server` | добавляет сервер в вашу группу ВК |
| `delete_callback_server` | удаляет сервер по `server_id` |
| `edit_callback_server` | редактирует настройки существующего сервера по `server_id` |
| `get_callback_confirmation_code` | получает код подтверждения вашего сервера |
| `get_callback_servers` | получает список серверов, подключённых к сообществу |
| `get_callback_settings` | получает список событий для сервера по `server_id` |
| `set_callback_settings` | устанавливает список событий для сервера по `server_id` |
| `construct` | принимает API, конструирует с обновлённым API; возвращает свой инстанс, может использоваться в билдер-интерфейсе |

### Параметры `BotCallback`

| Параметр | Описание |
|---|---|
| **url** | сервер, на который будут отправляться события |
| **title** | короткое имя сервера (показывается в настройках сообщества) |
| **secret_key** | секретный ключ для определения, что сообщение пришло именно от вашего бота. По умолчанию генерируется произвольная строка |
| **api** | если не указан — будет получен автоматически при создании объекта |
| **group_id** | если не указан — будет автоматически получен при установке сервера |

Своя реализация наследуется от `ABCCallback` и имплементирует методы выше.
