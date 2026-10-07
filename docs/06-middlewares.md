# 06. Мидлвари и Return-менеджеры

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/tutorial/middlewares-return-managers/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/handling/middleware/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/handling/return-manager/>

## Мидлвари

Мидлвари — внешние слои, покрывающие обработку хендлеров. Два состояния:
- **`pre`** — до начала поиска хендлера (когда уже нашёлся нужный `view`)
- **`post`** — когда хендлер уже обработан: известно, какие хендлеры сработали и что они вернули

`pre`/`post` **не принимают аргументов** и должны возвращать `None`.

### Создание

```python
from vkbottle import BaseMiddleware
from vkbottle.bot import Message
```

```python
class MiddlewareName(BaseMiddleware[Message]):
```

Тип ивента указывается в дженерике. Для `MessageView` это `Message`, для `raw_event_view` — словарь.

### `async def pre(self)`

Доступ к ивенту через `self`. Может вернуть ошибку через `self.stop` или обновить контекст через `self.send`.

Отсев сообщений от ботов:

```python
from vkbottle.bot import Message
from vkbottle import BaseMiddleware, MiddlewareResponse

class NoBotMiddleware(BaseMiddleware[Message]):
    async def pre(self):
        if self.event.from_id < 0:
            self.stop("from_id меньше 0")
```

### `async def post(self)`

На обработку ивента повлиять уже не может. Обычно — статистика и логи:

```python
from vkbottle.bot import Message
from vkbottle import BaseMiddleware

class LogMiddleware(BaseMiddleware[Message]):
    async def post(self):
        if not self.handlers:
            return
        print(f"{len(self.handlers)} хендлеров сработало на сообщение. "
              f"Они вернули {self.handle_responses}, "
              f"все они принадлежали к view {self.view}")
```

`pre` и `post` можно использовать одновременно в одном мидлваре.

### Атрибуты `BaseMiddleware`

| Атрибут | Описание |
|---|---|
| `event` | сам ивент (тип указывается в дженерике) |
| `view` | `ABCView`, которым был обработан ивент |
| `handle_responses` | список того, что вернули хендлеры по порядку исполнения |
| `handlers` | список исполненных `ABCHandler` |

### Методы

- `self.stop(ошибка)` — исполнение view срочно останавливается
- `self.send({ключ: значение})` — в контекст добавляются аргументы (ключ = имя аргумента хендлера)

### Регистрация

Нужно определиться с view. У `MessageView` он в лейблере по адресу `.message_view`. У каждого view есть метод `register_middleware`:

```python
bot.labeler.message_view.register_middleware(NoBotMiddleware)
bot.labeler.message_view.register_middleware(LogMiddleware)
```

Методом `register_middleware` можно пользоваться и как декоратором.

> **vkbottle 4.0:** методы `pre`/`post` больше **не принимают** аргумент message — доступ через `self.event`.

Полный пример: [middleware_example.py](https://github.com/vkbottle/vkbottle/tree/master/examples/high-level/middleware_example.py)

---

## Return-менеджеры

Возвращая из хендлера значения определённых типов, вы запускаете хендлеры return-менеджера, которые производят действия.

### Стандартное поведение для `MessageView`

| тип значения | что произойдёт |
|---|---|
| `str` | строка отправится как сообщение |
| `tuple` или `list` | все элементы будут конвертированы в строки и отправлены как сообщения |
| `dict` | словарь распакуется как непозиционные аргументы для метода `message.answer` |

### Реализация

```python
from vkbottle import BaseReturnManager
from vkbottle.bot import Message
from typing import Union

class BotMessageReturnHandler(BaseReturnManager):
    @BaseReturnManager.instance_of(str)
    async def str_handler(self, value: str, message: Message, _: dict[str, Any]):
        await message.answer(value)

    @BaseReturnManager.instance_of((tuple, list))
    async def iter_handler(self, value: tuple | list, message: Message, _: dict[str, Any]):
        [await message.answer(str(e)) for e in value]

    @BaseReturnManager.instance_of(dict)
    async def dict_handler(self, value: dict, message: Message, _: dict[str, Any]):
        await message.answer(**value)
```

Первый аргумент хендлера — само возвращённое значение, второй — объект ивента, третий — данные из правил и мидлварей.

Декоратор `instance_of` принимает тип или кортеж типов.

> Создание кастомного менеджера для своего view выходит за рамки туториала — см. [View](https://vkbottle.readthedocs.io/ru/latest/high-level/handling/view/).

### Практический смысл

Хендлер можно написать компактно, просто вернув строку:

```python
@bot.on.message(lev="/die")
async def die_handler(message: Message):
    await bot.state_dispenser.set(message.peer_id, SuperStates.AWKWARD_STATE)
    return "ok"
```
