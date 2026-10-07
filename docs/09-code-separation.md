# 09. Разделение кода

Источник: <https://vkbottle.readthedocs.io/ru/latest/tutorial/code-separation/>

Разделение кода — очень важная вещь для создания структуры проекта. В vkbottle можно использовать составляющие фреймворка **отдельно от `Bot`**.

Кроме того, `auto_rules` помогает установить правила, которые накладываются на **все** хендлеры сообщений.

> Внимание: правила в `auto_rules` распространяются только на хендлеры сообщений. Для сырых евентов нужен `raw_event_auto_rules` и кастомные правила.

## Стандартная иерархия файлов

```
/src/
├── handlers
│   ├── __init__.py
│   ├── admin.py
│   ├── chat.py
│   └── ping.py
├── bot.py
└── config.py
```

### `config.py`

Все глобальные переменные, используемые в разных частях проекта:

```python
from vkbottle import API, BuiltinStateDispenser
from vkbottle.bot import BotLabeler

api = API("token")
labeler = BotLabeler()
state_dispenser = BuiltinStateDispenser()
```

> В данном примере стейт-диспенсер не используется, но объявлен для наглядности. Если хотите использовать — импортируйте из `config.py` и укажите `state_dispenser` в `Bot` в `bot.py`.

### `ping.py`

```python
from config import labeler

@labeler.message(text="ping")
async def ping_handler(message):
    await message.answer("pong")
```

### `chat.py` — свой лейблер + `auto_rules`

1. Правило, чтобы все сообщения шли только из чата
2. Правило, получающее информацию о чате и возвращающее её для всех хендлеров этого лейблера
3. Несколько хендлеров

```python
from vkbottle.bot import BotLabeler, Message, rules
from vkbottle_types.objects import MessagesConversation

class ChatInfoRule(rules.ABCRule[Message]):
    async def check(self, message: Message) -> dict[str, Any]:
        chats_info = await message.ctx_api.messages.get_conversations_by_id(message.peer_id)
        return {"chat": chats_info.items[0]}

chat_labeler = BotLabeler()
chat_labeler.vbml_ignore_case = True
chat_labeler.auto_rules = [rules.PeerRule(from_chat=True), ChatInfoRule()]

@chat_labeler.message(command="самобан")
async def kick(message: Message, chat: MessagesConversation):
    await message.ctx_api.messages.remove_chat_user(message.chat_id, message.from_id)
    await message.answer(f"Участник самоустранился из {chat.chat_settings.title} по собственному желанию")

@chat_labeler.message(text="где я")
async def where_am_i(message: Message, chat: MessagesConversation):
    await message.answer(f"Вы в <<{chat.chat_settings.title}>>")
```

> Обратите внимание: `ChatInfoRule` возвращает **словарь** — `chat` автоматически приходит аргументом в каждый хендлер лейблера.

### `admin.py`

Хендлеры доступны только, например, создателю бота:

```python
from vkbottle.bot import BotLabeler, Message, rules

admin_labeler = BotLabeler()
admin_labeler.auto_rules = [rules.FromPeerRule(1)]  # Допустим, вы являетесь Павлом Дуровым

@admin_labeler.message(command="halt")
async def halt(_):
    exit(0)
```

### `handlers/__init__.py`

Импортируем все лейблеры:

```python
from .chat import chat_labeler
from .admin import admin_labeler
from .ping import labeler

# Если использовать глобальный лейблер, то все хендлеры будут зарегистрированы
# в том же порядке, в котором они были импортированы
__all__ = ("admin_labeler", "chat_labeler", "labeler")
```

### `bot.py`

```python
from vkbottle import Bot
from config import api, state_dispenser, labeler
from handlers import chat_labeler, admin_labeler
```

> Так как в папке `handlers` есть `__init__.py`, интерпретатор выполнит код в `echo.py`, и не нужно импортировать лейблер оттуда.

Загружаем хендлеры в глобальный лейблер:

```python
labeler.load(chat_labeler)
labeler.load(admin_labeler)
```

Создаём бота:

```python
bot = Bot(
    api=api,
    labeler=labeler,
    state_dispenser=state_dispenser,
)
```

Запускаем:

```python
bot.run_forever()
```

Пример: [code_separation](https://github.com/vkbottle/vkbottle/tree/master/examples/high-level/code_separation)

---

## Альтернатива: отдельные модули через `BotLabeler`

Более короткий вариант (источник: [Labeler](https://vkbottle.readthedocs.io/ru/latest/high-level/bot/labeler/)) — см. [03-handlers-labeler.md](03-handlers-labeler.md).

```python
# bot.py
from vkbottle import Bot

bot = Bot("token")

for custom_labeler in labelers:
    bot.labeler.load(custom_labeler)

bot.run_forever()
```

```python
# routes/__init__.py
from . import greetings, goodbyes

labelers = [greetings.bl, goodbyes.bl]
```

```python
# routes/greetings.py
from vkbottle.bot import BotLabeler, Message

bl = BotLabeler()

@bl.message(text=["привет", "хай", "здравствуй"])
async def greeting(message: Message):
    await message.answer("Привет, друг")
```

---

## Blueprint

> Блупринты являются **устаревшей** частью фреймворка и будут удалены в следующих версиях. Новый способ разделения кода — разделение через `BotLabeler` и `labeler.load(...)`.

Источник: <https://vkbottle.readthedocs.io/ru/latest/high-level/bot/blueprint/>
