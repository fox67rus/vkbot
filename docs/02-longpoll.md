# 02. LongPoll API (Polling)

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/low-level/polling/>
- <https://vkbottle.readthedocs.io/ru/latest/high-level/bot/>
- <https://vkbottle.readthedocs.io/ru/latest/low-level/exception_handling/error-handler/>

> Раздел `low-level/polling` в документации — **краткий, без готовых примеров кода**. Примеры запуска ниже взяты из разделов `high-level/bot`, `tutorial/first-bot`, `high-level/bot/multibot` и официальных примеров, на которые ссылается документация. Поведение внутри цикла описано по исходникам установленной версии `4.11.0` (помечено явно).

## Зачем это нужно

Библиотека использует `Polling`, чтобы реализовывать longpoll. Для ботов и юзеров создан соответствующий поллинг (они разные). Свой поллинг можно написать, базируясь на абстрактном `ABCPolling`.

## Два способа получить события

| Способ | Класс | Требование |
|---|---|---|
| **LongPoll (polling)** | `BotPolling` | Не нужен свой сервер; работает «из коробки» |
| **Callback API (вебхук)** | `BotCallback` | Нужен свой сервер с доменным именем (DDNS не работает) |

Callback API разобран в [12-callback-api.md](12-callback-api.md).

---

## Запуск longpoll

### Синхронный запуск

```python
bot.run_forever()
```

> В документации `run_forever()` описан так: *«Помогает асинхронно запустить бота из синхронной среды… добавляет `run_polling` в таски `bot.loop_wrapper` и вызывает `bot.loop_wrapper.run()`»*.

> **В версии 4.11.0** `run_forever()` помечен как устаревший (`@deprecated("Deprecated. Use run() instead")`) — используется `bot.run()`.

Именно `bot.run()` используется в актуальном официальном примере `easy_bot.py`:

```python
# Runs the bot's main polling task and any startup/startup_tasks/shutdown
# coroutines registered on the bot. If you already have your own event loop,
# call `await bot.run_polling()` from within it instead.
bot.run()
```

### Асинхронный запуск

```python
await bot.run_polling()
```

Используйте, если у вас уже есть свой event loop. По документации: `bot.run_polling()` — «Асинхронный запуск longpoll».

`run_polling` принимает необязательный аргумент `custom_polling` — свой инстанс `ABCPolling`:

```python
await bot.run_polling(custom_polling)
```

### Мультибот (несколько лонгполов)

Источник: <https://vkbottle.readthedocs.io/ru/latest/high-level/bot/multibot/>

Мультибот запускает несколько лонгполов на переданных API и обрабатывает события со всех лонгполов одним основным ботом. Для запуска нужен `run_multibot` — он добавляет `run_polling` в таски и запускает eventloop. Импортируется из `vkbottle.bot`.

```python
run_multibot(bot, apis, polling_type=BotPolling)
```

- Основному боту токен для создания API передавать **не нужно**
- `apis` — любой итерируемый объект (можно сделать свой генератор)
- `polling_type` — если кастомизируете поллинг, меняется здесь

Пример: [multibot.py](https://github.com/vkbottle/vkbottle/tree/master/examples/high-level/multibot.py)

---

## Атрибуты и методы

### У `Bot`

| Атрибут/метод | Описание |
|---|---|
| `bot.polling` | объект поллинга |
| `bot.run_polling()` | асинхронный запуск longpoll |
| `bot.run_forever()` | синхронный запуск longpoll (в 4.11 устарел → `bot.run()`) |
| `bot.loop_wrapper` | LoopWrapper бота (см. [11-tools.md](11-tools.md)) |
| `bot.api` | API |
| `bot.process_event(event)` | передать уже полученное событие (для Callback API) |

### Интерфейс поллинга

| Метод | Описание |
|---|---|
| `get_server` | Получает сервер для поллинга и возвращает его |
| `get_event` | Получает сервер из `get_server` в параметр и делает долгий POST-реквест |
| `listen` | Асинхронный итератор (используется с `async with`). Генерирует приходящие ивенты |
| `construct` | Принимает API, конструирует поллинг с обновлённым API при каждом вызове. Возвращает собственный инстанс, может использоваться в билдер-интерфейсе |

### Стандартные параметры `BotPolling` / `UserPolling`

| Параметр | Описание |
|---|---|
| **api** | если не указано, будет получено в `listen` |
| **group_id** / **user_id** | если не указано, будет получено в `listen` |
| **wait** | лимит секунд, после которого ВК принудительно возвращает ответ на долгий реквест (даже если нет обновлений) |
| **rps_delay** | если не указано — задержка равна 0 |

---

## Как это работает внутри (по исходникам vkbottle 4.11.0)

Документация описывает интерфейс скупо, поэтому ниже — факты из исходников `vkbottle/polling/`, чтобы в проекте правильно использовать longpoll.

### Сигнатура `BotPolling.__init__`

```python
BotPolling(
    api=None,
    group_id=None,
    wait=None,
    rps_delay=None,
    skip_old_events=True,
    error_handler=None,
)
```

- `self.wait = min(wait or 25, 90)` — по умолчанию **25 секунд**, максимум **90**
- `self.rps_delay = rps_delay or 0`
- `skip_old_events=True` по умолчанию

### `get_server`

1. Если `group_id` не указан — вызывается `groups.getById`, `group_id` берётся из ответа.
   - Если групп нет (используется **пользовательский** токен) → `RuntimeError: "Unable to get group id for bot polling. Perhaps you are using a user access token?"`
2. Вызывается `groups.getLongPollServer` с параметром `group_id`.

### `get_event`

Делает долгий POST-запрос на сервер лонгполла:

- `act=a_check`, `key`, `ts`, `wait`, `rps_delay`
- `timeout = wait + 10` секунд

### Цикл `listen()`

Асинхронный генератор; работает до вызова `stop()`:

1. `server = get_server()`
2. `event = get_event(server)`
3. Если в ответе есть `"failed"` → обработка кода отказа (см. ниже)
4. Если нет `"ts"` → перезапрашивает сервер
5. Обновляет `server["ts"] = event["ts"]`, при наличии `updates` отдаёт событие наружу
6. Сохраняет `ts` на диск (см. «Персистентность ts»)

**Коды отказа (`failed`)** — `FailureCode`:

| Код | Название | Действие |
|---|---|---|
| 1 | `HISTORY_OUTDATED` | обновляет `server["ts"]` из события |
| 2 | `KEY_EXPIRED` | перезапрашивает сервер, **сохраняя старый `ts`** |
| 3 | `INFORMATION_LOST` | перезапрашивает сервер целиком |
| 4 | `INVALID_VERSION` | логирует `min_version`/`max_version`, ставит `lp_version = 3` и перезапрашивает сервер |

Неизвестный код → логирование ошибки, событие пропускается.

**Повторные попытки.** При `ClientConnectionError`, `asyncio.TimeoutError`, `VKAPIError[10]` сервер и `ts` **сохраняются** (чтобы не терять очередь событий), делается `asyncio.sleep(0.1 * retry_count)` с `retry_count` до 60. Прочие исключения уходят в `error_handler.handle(e)` и тоже идут с backoff.

### Персистентность `ts` (важно для проекта)

При `skip_old_events=True` (по умолчанию) состояние **не** восстанавливается — после рестарта бот начинает с «чистого» сервера.

При `skip_old_events=False` `ts` сохраняется в файл:

```
<cwd>/.vkbottle/bot-polling/<group_id>.json
```

Формат: `{"ts": "..."}`. Запись — атомарная (через `.tmp` + `replace`) и выполняется в отдельном потоке (`asyncio.to_thread`), чтобы не блокировать event loop. `ts` сохраняется **после** того, как событие было отдано на обработку, чтобы при падении посреди обработки событие не потерялось.

> Для проекта: если нужна устойчивость к рестартам — передавайте `BotPolling(skip_old_events=False)` и не удаляйте каталог `.vkbottle/`.

### Остановка

```python
bot.polling.stop()
```

Устанавливает внутренний `asyncio.Event`, цикл `listen()` завершается.

---

## Свой поллинг

Кастомный поллинг наследуется от `ABCPolling` и имплементирует методы:

- `async get_server()`
- `async get_event(server)`
- `async listen()` (async-итератор)
- `async construct(api, error_handler=None)`
- `stop()`
- свойство `api` (геттер/сеттер)

```python
class ABCPolling(ABC):
    @abstractmethod
    async def get_server(self) -> Any: ...

    @abstractmethod
    async def get_event(self, server: Any) -> dict[str, Any]: ...

    @abstractmethod
    async def listen(self) -> AsyncIterator[dict]: ...

    @property
    @abstractmethod
    def api(self) -> "ABCAPI": ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def construct(self, api, error_handler=None) -> Self: ...
```

Пример подключения своего поллинга — через `run_polling(custom_polling=...)` (см. выше) или `run_multibot(..., polling_type=...)`.

---

## Настройки сообщества для LongPoll

Из документации (`tutorial/first-bot`): проверьте, что в настройках лонгпола отмечены нужные события (в частности «новые сообщения») и сам лонгпол; стабильная версия API — `5.131`.

---

## Связанные страницы

- Polling: <https://vkbottle.readthedocs.io/ru/latest/low-level/polling/>
- Bot: <https://vkbottle.readthedocs.io/ru/latest/high-level/bot/>
- Callback API: [12-callback-api.md](12-callback-api.md)
- LoopWrapper (startup/shutdown/интервалы): [11-tools.md](11-tools.md)
