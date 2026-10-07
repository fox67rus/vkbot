# 11. Инструменты (tools)

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/tools/>
- разделы `formatting`, `keyboard`, `loop-wrapper`, `message-event`, `storage`, `template`, `uploaders`, `vkscript`, `waiter-machine`, `auth`

> Клавиатуры, шаблоны, загрузчики и Waiter Machine вынесены в другие файлы:
> [05-keyboards-attachments.md](05-keyboards-attachments.md), [07-states.md](07-states.md).

---

## Loop Wrapper

`LoopWrapper` нужен, чтобы контролировать event loop и хранить основные таски, `startup` и `shutdown`, которые будут исполнены при запуске event loop через `run_forever`.

> Если используете `LoopWrapper` вместе с `Bot`, учитывайте: у `Bot` уже есть свой `LoopWrapper` — `bot.loop_wrapper`, запускаемый при `bot.run_forever()`.

### Таски

```python
from vkbottle import LoopWrapper

async def my_task():
    ...

lw = LoopWrapper()
lw.add_task(my_task())
lw.run()
```

### on_startup и on_shutdown

`on_startup`-корутины запускаются перед запуском event loop, `on_shutdown` — при остановке. Это списки корутин:

```python
from vkbottle import LoopWrapper

async def startup_task():
    print("This is startup")

async def shutdown_task():
    print("This is shutdown")

lw = LoopWrapper()
lw.on_startup.append(startup_task())
lw.on_shutdown.append(shutdown_task())
lw.run()
```

### interval — повторяющаяся задача

```python
from vkbottle import LoopWrapper

lw = LoopWrapper()

@lw.interval(seconds=10)
async def repeated_task():
    print("I'll print this every 10 seconds!")

lw.run()
```

### timer — отложенная задача

```python
from vkbottle import LoopWrapper

lw = LoopWrapper()

@lw.timer(seconds=10)
async def delayed_task():
    print("I'll print this after 10 seconds!")

lw.run()
```

---

## Formatting

Форматирование текста через класс `Formatter` (наследует `str`, перегружает `format` и `format_map`).

```python
from vkbottle.tools.formatting import Formatter
```

Доступные типы: **bold** (полужирный), **italic** (курсив), **url** (ссылка), **underline** (подчёркнутый).

```python
Formatter("Hi, {}.").format("Alex")          # Hi, Alex.
Formatter("Hi, {name}.").format(name="Maria")  # Hi, Maria.
```

Идентификаторы форматирования:

```python
Formatter("{:bold}, nice formatting!").format("Wow")  # Wow, nice formatting!
Formatter("{framework:italic} has been around for over 5 years!").format(framework="vkbottle")  # vkbottle has been around for over 5 years!
```

Объединение типов через `+`:

```python
Formatter("Very cool {:bold+italic} ^_^").format("bold-italic message")  # Very cool bold-italic message ^_^
```

`format_map` принимает один аргумент типа `Mapping`:

```python
Formatter("My bestie is {bestie:underline}").format_map({"bestie": "telegrinder"})  # My bestie is telegrinder
```

> В оригинале документации пропущена закрывающая скобка `)` — здесь исправлено.

Свойства для получения json:
- `format_data` — словарь `{"version": ..., "items": [...]}`
- `raw_format_data` — сырой объект `format_data`

> `format_data` нужен для методов, работающих с форматированным текстом, например `messages.send`. См. [документация VK](https://dev.vk.ru/ru/reference/objects/message#format_data)

### Класс `Format` и функции

```python
from vkbottle.tools.formatting import Format
```

```python
bold("Hello, ") + italic("World!")  # Hello, World! ('Hello, ' is bold, 'World!' is italic)
"Hello, " + italic("World!")        # Hello, World! ('World!' is italic)
bold("Hello") + ", " + italic("World!")  # Hello, World!
bold("vkbottle documentation:") + " " + url(italic("click me"), href="vkbottle.readthedocs.io/ru/latest")  # vkbottle documentation: click me
```

`Format` имеет методы `as_data` и `as_raw_data`.

```python
await message.answer(Formatter("Hello, {:bold}!").format("World"))
await message.answer(underline(bold("Hello") + ", " + italic("World!")))
```

---

## MessageEvent — callback-кнопки

```python
from vkbottle import GroupEventType
from vkbottle.bot import MessageEvent

@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def handle_message_event(event: MessageEvent):
    await event.show_snackbar("Сейчас я исчезну")
```

Преимущества:
- Никакого `object` — всё в `event`, вместе с `group_id`
- Поддержка всех генераторов `event-data` соответствующими функциями
- Поддержка правил, связанных с `payload`
- Есть `message_edit` и `message_send`

### Старый способ

```python
from vkbottle import GroupEventType, GroupTypes, ShowSnackbarEvent

@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=GroupTypes.MessageEvent)
async def handle_message_event(event: GroupTypes.MessageEvent):
    await event.ctx_api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=event.object.user_id,
        peer_id=event.object.peer_id,
        event_data=ShowSnackbarEvent(text="Сейчас я исчезну").model_dump_json(),
    )
```

Полный пример: [callback_buttons.py](https://github.com/vkbottle/vkbottle/tree/master/examples/high-level/callback_buttons.py)

---

## Storage — хранилища

Хранилища нужны, чтобы хранить информацию в формате `ключ`: `значение`.

| Метод | Описание |
|---|---|
| `get(key)` | получить |
| `set(key, value)` | записать |
| `delete(key)` | удалить |
| `contains(key)` | проверить наличие |

### CtxStorage

Контекстное хранилище можно открыть и изменить из любого места в коде; доступно из коробки. Пример: [ctx_storage_example.py](https://github.com/vkbottle/vkbottle/tree/master/examples/low-level/ctx_storage_example.py)

### Своё хранилище (например на RabbitMQ)

- Наследуйтесь от `ABCStorage`
- Имплементируйте `get`, `set`, `delete`, `contains`

---

## VKScript Converter

Импортируйте `vkscript` и оберните функцию — после её вызова вернётся код, выполняющий ту же логику, но на `VKScript`:

```python
from vkbottle import vkscript

@vkscript
def my_execute(api, user_ids=()):
    message_ids = []
    for user_id in user_ids:
        user = api.users.get(user_ids=user_id)[0]
        message_ids.append(api.messages.send(
            message=f"{user.first_name}, спасибо что зашел на чай",
            random_id=0,
            peer_id=user_id,
        ))
    return message_ids

# далее вызывая эту функцию вы можете использовать ее ответ в качестве кода для execute
await api.execute(code=my_execute(user_ids=[10, 11, 12]))
```

---

## UserAuth — токен пользователя

> Мы не несём ответственности за блокировку ваших аккаунтов.

```python
from vkbottle import UserAuth

login = "89012345678"
password = "qwerty123"

async def main():
    token = await UserAuth().get_token(login, password)
```

По умолчанию используется мобильное приложение ВК. Можно указать своё, передав `client_id` и `client_secret` в конструктор.

Права доступа задаются параметром `scope`:

```python
from vkbottle import UserAuth, UserPermission

login = "89012345678"
password = "qwerty123"

async def main():
    token = await UserAuth().get_token(
        login, password,
        scope=[UserPermission.photos, UserPermission.video],
    )
```

По умолчанию включены: `friends`, `photos`, `video`, `stories`, `pages`, `status`, `notes`, `wall`, `ads`, `offline`, `docs`, `groups`, `notifications`, `stats`, `email`, `adsweb`, `exchange`, `market`.

Полный пример с обработкой капчи и 2FA — в [документации Auth](https://vkbottle.readthedocs.io/ru/latest/tools/auth/).
