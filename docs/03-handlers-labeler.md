# 03. Хендлеры и Labeler

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/high-level/handling/handler/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/bot/labeler/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/bot/>

## Хендлеры

Хендлеры — конечная точка в обработке событий. Они бывают **блокирующими** (если нашёлся подходящий хендлер, другие уже не проверяются) и **неблокирующими**. По умолчанию все хендлеры блокирующие.

Хендлеры помечаются декораторами через `Labeler` (`bot.labeler` или `bot.on` — `.on` нужен «для красоты и традиционного legacy вкботла из второй версии»).

```python
from vkbottle.bot import Bot, Message

bot = Bot("token")

@bot.on.message()
async def any_message(message: Message):
    await message.answer("Привет я бот")

bot.run_forever()
```

### Декораторы

| Декоратор | Что делает |
|---|---|
| `.message` | обрабатывает сообщения и из бесед, и из личной переписки |
| `.private_message` | только личная переписка |
| `.chat_message` | только беседы |

Отличие — только предустановленный `PeerRule`: в `message` не предустанавливается, в `chat_message` — `PeerRule(True)`, в `private_message` — `PeerRule(False)`.

### Аргументы декоратора

Декоратор принимает **позиционно** инстансы правил (`ABCRule`), а **в kwargs** — значения из `custom_rules`.

```python
# Позиционно — инстанс правила
@bot.on.message(CommandRule("say", ["!", "/"], 1))
async def say_handler(message: Message, args: tuple[str]):
    await message.answer(f"<<{args[0]}>>")
```

```python
# kwargs — шорткаты из custom_rules
@bot.on.message(command=("say", 1))
async def say_handler(message: Message, args: tuple[str]):
    await message.answer(f"<<{args[0]}>>")
```

### Передача данных из правила в хендлер

Если правило вернуло **словарь**, он распакуется и передастся в хендлер как непозиционные аргументы (если хендлер их принимает):

```python
# Кастомное правило MyRule возвращает словарь `{"some_key": "some_value"}`

@bot.on.message(MyRule())
async def some_key_handler(message: Message, some_key: str):
    await message.answer(f"some_key={some_value}")

@bot.on.message(MyRule())
async def regular_handler(message: Message):
    await message.answer("Этот хендлер не принимает аргумент 'some_key', поэтому он и не был передан")

@bot.on.message(MyRule())
async def kwargs_handler(message: Message, **kwargs: Any):
    await message.answer(f"В хендлер переданы аргументы: {kwargs}")
    # В хендлер переданы аргументы: {"some_key": "some_value"}
```

### Неблокирующие хендлеры

См. [View](https://vkbottle.readthedocs.io/ru/latest/high-level/handling/view/): хендлеры помечаются флагом `blocking`; неблокирующих несколько — количество не ограничено.

---

## Labeler

`BotLabeler` — удобная оболочка над роутерами. С помощью лейблера создаются хендлеры. Может использоваться в качестве портабельного диспатчера.

Метод `load` загружает хендлеры и мидлвари в текущий лейблер из переданного. Используется для разбивания кода на части.

### Пример разделения на модули

**bot.py**

```python
from vkbottle import Bot

bot = Bot("token")

for custom_labeler in labelers:
    bot.labeler.load(custom_labeler)

bot.run_forever()
```

**routes/__init__.py**

```python
from . import greetings, goodbyes

labelers = [greetings.bl, goodbyes.bl]
```

**routes/greetings.py**

```python
from vkbottle.bot import BotLabeler, Message

bl = BotLabeler()

@bl.message(text=["привет", "хай", "здравствуй"])
async def greeting(message: Message):
    await message.answer("Привет, друг")
```

**routes/goodbyes.py**

```python
from vkbottle.bot import BotLabeler, Message

bl = BotLabeler()

@bl.message(text=["пока", "до свидания"])
async def greeting(message: Message):
    await message.answer("До новых встреч")
```

> Хендлеры регистрируются в том же порядке, в котором импортируются модули.

### Кастомные правила лейблера

Правило, объявленное с параметрами, можно сделать шорткатом — через `custom_rules` (регистрировать **до объявления хендлеров**):

```python
bot.labeler.custom_rules["my_rule"] = MyRule
```

```python
@bot.on.message(my_rule=50)
```

### `auto_rules`

`auto_rules` — правила, которые накладываются на **все** хендлеры сообщений лейблера:

```python
from vkbottle.bot import BotLabeler, Message, rules

chat_labeler = BotLabeler()
chat_labeler.vbml_ignore_case = True
chat_labeler.auto_rules = [rules.PeerRule(from_chat=True), ChatInfoRule()]
```

> Внимание: правила в `auto_rules` распространяются только на хендлеры сообщений. Для сырых евентов нужен `raw_event_auto_rules` и кастомные правила.

См. подробнее: [09-code-separation.md](09-code-separation.md).

---

## View и Router

### Router

Роутер принимает запрос и передаёт его в подходящий `view`. Также передаёт ошибки, возникающие во время выполнения `view`.

Атрибуты:
- `views` — словарь с view
- `state_dispenser` — хранение состояний
- `error_handler` — обработка ошибок

Методы:
- `route` — принимает событие и контекст `API`, передаёт подходящему `view`
- `construct` — принимает атрибуты роутера и устанавливает их
- `add_view` — принимает имя `view` и сам `view`, добавляет в словарь `views`
- `view` — декоратор с тем же эффектом

### View

`View` — блокирующие менеджеры хендлеров. Если `process_event` вернул `True`, другие view уже не проверяются.

Порядок: сначала `process_view` (возвращает bool), при `True` вызывается `handle_event` — подбор хендлера.

У каждого view минимум 4 атрибута:
- `handlers` — лист `ABCHandler`
- `middlewares` — сет классов `BaseMiddleware`
- `middleware_instances` — лист объектов `BaseMiddleware` (используется в `pre_middleware`/`post_middleware`)
- `handler_return_manager` — `BaseReturnManager`

Рекомендуются `handlers` и `middlewares`.

Регистрация мидлваря: `view.register_middleware(BaseMiddleware)`.

Полный пример собственного view — в [документации View](https://vkbottle.readthedocs.io/ru/latest/high-level/handling/view/) (там `VoteView` + `FromFuncHandler` + кастомный `MyLabeler`).

---

## Raw-события

```python
from vkbottle import GroupEventType
from vkbottle.bot import MessageEvent

@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def handle_message_event(event: MessageEvent):
    await event.show_snackbar("Сейчас я исчезну")
```

Подробнее — [11-tools.md § MessageEvent](11-tools.md#messageevent--callback-кнопки).
