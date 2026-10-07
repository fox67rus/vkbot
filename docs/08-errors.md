# 08. Обработка ошибок

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/tutorial/error-handling/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/exception_handling/code-exception/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/exception_handling/error-handler/>

## `VKAPIError`

`VKAPIError` — подтип `CodeException`: ошибка идентифицируется в `except` и без кода, и с кодом.

Два поля:
- `code` — код ошибки, `int`
- `error_msg` — описание ошибки, `str`

```python
from vkbottle import VKAPIError

try:
    await api.wall.post()
except VKAPIError as e:
    print("Возникла ошибка", e.code)
```

### С указанием кода — `VKAPIError[code]`

```python
try:
    await api.messages.send(peer_id=1, message="привет!", random_id=0)
except VKAPIError[902] as e:
    print("не могу отправить сообщение из-за настроек приватности")
except VKAPIError as e:
    print("не могу отправить:", e.error_msg)
```

Комбинирование (из [whats_new/4.0](https://vkbottle.readthedocs.io/ru/latest/whats_new/4.0/)):

```python
async def main():
    try:
        await api.users.get(user_ids=["123456789"])
    except VKAPIError[5]:
        print("Ой, неверный ключ доступа.")
    except VKAPIError[30]:
        print("Ой, у пользователя закрытый профиль.")
    except VKAPIError as e:
        print(f"Произошла ошибка {e.code}.")
```

Список всех ошибок ВК: <https://dev.vk.ru/reference/errors>

### Специфичные ошибки

`CaptchaError` имеет дополнительные поля:
- `captcha_sid` — идентификатор captcha, `str`
- `captcha_img` — ссылка на изображение, `str`

---

## `CodeException`

Базовый класс для исключений с кодом. Синтаксис generic-подобный — код указывается в **квадратных скобках**.

```python
class MyCodeError(CodeException):
    pass

try:
    raise MyCodeError[1]("Error description")
except MyCodeError[1]:
    print("Error with code 1 appeared")
except MyCodeError[2, 3]:
    print("Error with code 2 or 3 appeared")
except MyCodeError as e:  # Ошибка с любым кодом
    print(f"Error with code {e.code} appeared")
```

Базовое исключение для ошибок API импортируется как `VKAPIError`.

---

## ErrorHandler

### У бота — 4 метода

| Метод | Описание |
|---|---|
| `register_error_handler` | декоратор, принимает типы ошибок и async-хендлер. Если возникнет одна из указанных ошибок (или её подтип) — исполнится хендлер |
| `register_undefined_error_handler` | декоратор для неизвестных ошибок |
| `handle` | принимает инстанс ошибки, передаёт в соответствующий хендлер. Если хендлера нет — поднимает её |
| `catch` | декоратор. Ловит ошибки из декорированной функции и передаёт их `handle` |

```python
from vkbottle import Bot, VKAPIError

bot = Bot("token")

@bot.error_handler.register_error_handler(RuntimeError)
async def runtime_error_handler(e: RuntimeError):
    print("возникла ошибка runtime", e)

@bot.error_handler.register_error_handler(VKAPIError[902])
async def unable_to_write_handler(e: VKAPIError):
    print("человек не разрешил отправлять сообщения", e)
```

Несколько типов сразу:

```python
from typing import Union
from vkbottle import Bot, VKAPIError

bot = Bot("token")

@bot.error_handler.register_error_handler(TypeError, ValueError)
async def type_or_value_error_handler(e: TypeError | ValueError):
    print("возникла ошибка type или value", e)

@bot.error_handler.register_error_handler(*VKAPIError[6, 9])
async def limit_reached_write_handler(e: VKAPIError):
    print("ой, слишком много запросов", e)
```

> У `ErrorHandler` есть параметр `redirect_arguments: bool` — позволяет передавать в хендлер аргументы из задекорированной с помощью `catch` функции. В связке с ботом позволяет передать контекстные аргументы из правил и мидлварей.

### Отдельный `ErrorHandler`

```python
from vkbottle import ErrorHandler

error_handler = ErrorHandler(redirect_arguments=False, raise_exceptions=False)

# Если redirect_arguments = True, то все аргументы обернутой функции будут поступать и в хендлер исключения
# Если raise_exceptions = True, то все необработанные исключения будут выброшены
# (игнорируется, если есть обработчик для ненайденных ошибок)

@error_handler.register_error_handler(RuntimeError)
async def exc_handler_runtime(e: RuntimeError):
    print("Oh no runtime error occurred:", e)

@error_handler.register_error_handler(LookupError)
async def exc_handler_lookup(e: LookupError):
    print("Oh no lookup error occurred:", e)
```

Хендлер для ненайденных ошибок:

```python
@error_handler.register_undefined_error_handler
async def exc_handler_undefined(e: Exception):
    print("Oh no unknown error occurred", e)
```

Декоратор `catch`:

```python
@error_handler.catch
async def main():
    raise LookupError("I ve lost my keys")
```

```python
import asyncio
asyncio.run(main())
```

Вывод:

```
Oh no lookup error occurred: I've lost my keys
```

---

## Где обрабатываются ошибки поллинга

В цикле `listen()` исключения уходят в `error_handler.handle(e)` поллинга, затем делается backoff. См. [02-longpoll.md](02-longpoll.md).
