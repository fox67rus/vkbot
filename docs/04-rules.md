# 04. Правила (Rules)

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/tutorial/rules/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/builtin-rules/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/handling/rules/>

Правила («рулзы») нужны, чтобы хендлер ловил только нужные сообщения/события.

> **Внимание.** Все встроенные рулзы работают только с объектами `Message` и `MessageEvent` из `vkbottle.bot`. Для обработки сырых евентов нужно писать свою реализацию.

## Три способа использования

### 1. Импорт правила напрямую

```python
from vkbottle.dispatch.rules.base import CommandRule

@bot.on.message(CommandRule("say", ["!", "/"], 1))
async def say_handler(message: Message, args: tuple[str]):
    await message.answer(f"<<{args[0]}>>")
```

### 2. Шорткаты

Список названий — в разделе [Rules](https://vkbottle.readthedocs.io/ru/latest/high-level/handling/rules/):

```python
@bot.on.message(command=("say", 1))
async def say_handler(message: Message, args: tuple[str]):
    await message.answer(f"<<{args[0]}>>")
```

> Некоторые правила принимают итерируемый объект. Например, `CommandRule` принимает `command` и `args_count`, а в шорткате передаётся кортеж: `@bot.on.message(command=("help", 0))`.

### 3. Через `custom_rules`

См. [03-handlers-labeler.md](03-handlers-labeler.md).

---

## Полный список шорткатов

| Шорткат | Правило |
|---|---|
| `from_chat` | `PeerRule` |
| `mention` | `MentionRule` |
| `command` | `CommandRule` |
| `from_user` | `FromUserRule` |
| `peer_ids` | `FromPeerRule` |
| `sticker` | `StickerRule` |
| `attachment` | `AttachmentTypeRule` |
| `levenshtein` / `lev` | `LevenshteinRule` |
| `length` | `MessageLengthRule` |
| `action` | `ChatActionRule` |
| `payload` | `PayloadRule` |
| `payload_contains` | `PayloadContainsRule` |
| `payload_map` | `PayloadMapRule` |
| `func` | `FuncRule` |
| `coroutine` / `coro` | `CoroutineRule` |
| `state` | `StateRule` |
| `state_group` | `StateGroupRule` |
| `regexp` / `regex` | `RegexRule` |
| `macro` | `MacroRule` |
| `text` | `VBMLRule` |
| `fuzzy` | `FuzzyTextRule` |

Логика встроенных правил: [vkbottle/dispatch/rules/base.py](https://github.com/vkbottle/vkbottle/blob/master/vkbottle/dispatch/rules/base.py)

---

## Создание собственных правил

Правило — класс, реализующий интерфейс `ABCRule`, с **одним** асинхронным методом `check`. Он принимает ивент и возвращает:
- `False`, если проверка не пройдена
- `True`, либо **словарь** с аргументами (распакуются в хендлер как непозиционные)

### Напрямую

```python
from typing import Union
from vkbottle.bot import Message
from vkbottle.dispatch.rules import ABCRule

class MyRule(ABCRule[Message]):
    async def check(self, event: Message) -> dict[str, Any] | bool:
        ...
```

Логика:

```python
return len(message.text) < 100
```

Итог:

```python
from typing import Union
from vkbottle.bot import Message
from vkbottle.dispatch.rules import ABCRule

class MyRule(ABCRule[Message]):
    async def check(self, event: Message) -> bool:
        return len(event.text) < 100
```

Использование первым способом:

```python
@bot.on.message(MyRule())
```

### С параметрами (чтобы работало как шорткат)

```python
class MyRule(ABCRule[Message]):
    def __init__(self, lt: int = 100):
        self.lt = lt

    async def check(self, event: Message) -> bool:
        return len(event.text) < self.lt
```

Регистрация (до объявления хендлеров):

```python
bot.labeler.custom_rules["my_rule"] = MyRule
```

```python
@bot.on.message(my_rule=50)
```

### Через правила-врапперы

Правила-врапперы исполняют код, который получают параметром. Из коробки:
- `func` → `FuncRule` (принимает функцию, можно лямбду)
- `coro` / `coroutine` → `CoroutineRule`

```python
@bot.on.message(func=lambda message: len(message.text) < 100)
```

---

## Все встроенные правила

### `PeerRule(from_chat: bool = True)`

Ограничение источника сообщения. `PeerRule(from_chat=False)` — сообщение должно быть из личного диалога с ботом.

### `MentionRule(mention_only: bool = False)`

Проверяет, что бот упомянут в сообщении. При `mention_only=True` кроме упоминания в сообщении быть ничего не должно; иначе упоминание удаляется из текста, чтобы другие правила обработали сам текст.

### `CommandRule(command_text, prefixes, args_count = 0, sep = " ")`

Реагирует на команды. Вид команды:

```
{prefix}{command_text}{sep.join(args)}
```

- `command_text` — несколько вариантов названия команды
- `prefixes` — несколько префиксов (например: `'/'`, `'!'`)
- `args_count` — количество обязательных аргументов, `sep` — разделитель

### `VBMLRule(pattern, patcher = None, flags = None)`

Парсер текстов сообщений. Разметка VBML сделана специально для фреймворка — лёгкие паттерны с валидируемыми аргументами.

```python
rule = VBMLRule("/cmd <eggs:int>")
rst = await rule.check(Message(text="/cmd 11", ...))
assert rst == {"eggs": 11}
```

Больше: [документация VBML](https://github.com/tesseradecade/vbml/blob/master/docs/index.md)

### `RegexRule(regexp)`

Соответствие текста сообщения регулярному выражению. Шорткаты: `regexp`, `regex`.

### `StickerRule(sticker_ids = None)`

Отлавливает отправку стикеров. При `sticker_ids = None` подойдёт любое сообщение со стикером.

### `FromPeerRule(peer_ids)`

Сообщения от пользователя/группы с одним из указанных ID. Шорткат — `peer_ids`.

### `AttachementTypeRule(attachment_types)`

Сообщения с указанным типом вложений (например `photo`). Шорткат — `attachment`.

### `ForwardMessagesRule`

Проверяет, что сообщение содержит вложенные сообщения.

### `ReplyMessageRule(reply_message: bool = True)`

### `GeoRule`

Сообщения с геометкой.

### `LevenshteinRule(levenshtein_texts, max_distance: int = 1)` — DEPRECATED

> На данный момент обсуждается удаление этого правила из новых версий из-за его неоптимальности. Вместо этого рекомендуется использовать `FuzzyTextRule`.

Fuzzy string matching, `max_distance` — максимальное отклонение от заданного текста.

### `FuzzyTextRule(texts, min_ratio: float = 0.7)`

Fuzzy string matching. `min_ratio` — минимальная похожесть сообщения с переданным текстом (от 0 до 1).

### `MessageLengthRule(min_length: int)`

Ограничение минимальной длины текстового сообщения. Шорткат — `length`.

### `ChatActionRule(chat_action_types)`

Отлов событий в беседах (например `chat_invite_user`). [Документация ВК по chat actions](https://dev.vk.ru/reference/objects/message#action)

### `PayloadRule(payload)`

Проверяет, что payload сообщения равен одному из данных.

### `PayloadContainsRule(payload_part)`

Проверяет, что payload сообщения содержит данную часть.

### `PayloadMapRule(payload_map)`

Ассоциации нужных значений и типов в payload.

Payload:

```python
{"name": "boba", "data": {"action": "do", "number": 12}}
```

Payload map:

```python
PayloadMapRule({"name": str, "data": {"action": str, "number": int}})
```

Вместо типа можно передать валидатор (`ABCValidator`), функцию (будет вызвана со значением) или literal-значение:

```python
PayloadMapRule(
    {
        "name": "boba",
        "data": {
            "action": lambda x: x in ("do", "undo"),
            "number": int,
        }
    }
)
```

### `FromUserRule(from_user: bool = True)`

Проверяет, что сообщение отправлено пользователем, а не ботом. При `from_user = False` — наоборот.

### `FuncRule(func)`

Принимает функцию, вызванную с единственным аргументом-событием. Должна вернуть `bool` или `dict` с обновлением контекста.

### `CoroutineRule(coro)`

Ответ проверки правила получается из переданной корутины.

### `StateRule(state)`

Для стейт-машины: проверяет, что источник ивента находится в переданном состоянии. Если состояние = `None`, проверяет, что источник **не** находится ни в каком состоянии. Шорткат — `state`.

### `StateGroupRule(state_group)`

Проверяет, что пользователь находится в нужной коллекции состояний. Шорткат — `state_group`.
