# План разработки: VK-бот с AI-ответами

## Постановка задачи

ВК-бот, который:
1. **Приветствует новых участников** в беседе (событие `chat_invite_user` / `chat_invite_user_by_link`).
2. **Отвечает на входящие сообщения** с помощью AI:
   - в **личных сообщениях** — на любое сообщение;
   - в **беседе** — только при упоминании бота (`@bot ...`).
3. Получает события через **LongPoll API** (без своего сервера).
4. Хранит ключи в **`.env`**, читает через **`python-dotenv`**.
5. Использует провайдер **ProxyAPI**, модель **`gpt-5.4-mini`** (полный id — `openai/gpt-5.4-mini`), настройки провайдера и модели — в `env`.

### Согласованные решения

| Вопрос | Решение |
|---|---|
| Поведение в беседе | Только при упоминании (ЛС — всегда) |
| Память диалога | История последних N пар сообщений, in-memory, глубина в `env` |

---

## Что выяснено до начала работы

### ProxyAPI

- Документация: <https://proxyapi.ru/docs/openai-text-generation>
- Базовый адрес: `https://api.proxyapi.ru/v1`
- Эндпоинт: `POST /v1/chat/completions`
- Авторизация: `Authorization: Bearer <КЛЮЧ>`
- Тело: `{"model", "messages": [{"role","content"}], ...}`
- Ответ: `choices[0].message.content`
- Модель подтверждена в каталоге: **`openai/gpt-5.4-mini`**, контекст 1M, 230 ₽ / 1370 ₽ за 1М токенов.
- Идентификатор лучше писать **полностью** (`openai/gpt-5.4-mini`), короткое имя не угадывает вендора.
- Модель **не помнит** предыдущие сообщения — историю надо передавать заново с ролью `assistant`.
- Коды ошибок: 400 (формат), 401 (ключ), 402 (баланс), 403 (доступ к модели), 404 (модель), 429 (лимит), 502/504 (сервис). Тело: `{"detail": "..."}` (проверки ProxyAPI) или `{"error": {"message": ...}}` (конечный сервис).
- Параметры `temperature`/`max_tokens` поддерживаются, но **у разных моделей по-разному** → заложить автоматический фоллбэк без них при 400.

### vkbottle 4.11.0

- `bot.run_forever()` помечен deprecated → используем **`bot.run()`**; для async-среды `await bot.run_polling()`.
- `bot.on_startup` / `bot.on_shutdown` — списки корутин (LoopWrapper тоже deprecated).
- **Упоминание**: нужно `bot.labeler.message_view.replace_mention = True`, иначе `message.mention`/`is_mentioned` не работают.
- **`MentionRule(mention_only=False)`** → `event.is_mentioned`. При `mention_only=True` (по умолчанию) сработает только голое упоминание без текста — нам это не подходит.
- `MentionRule` работает **только в беседах** (в ЛС `mention is None`) → нужен отдельный хендлер для ЛС.
- `ChatActionRule` читает `event.action.type.value`; типы: `chat_invite_user`, `chat_invite_user_by_link`, `chat_invite_user_by_message_request`.
- `action.member_id` — id вступившего; для групп отрицательный.
- **`auto_rules`** вшиваются в хендлер **в момент декорирования** → выставлять до декораторов; при `labeler.load()` переживают перенос.
- `message.answer()` сам режет текст на куски по 4096 и делает уникальный `random_id` на кусок.
- `bot.labeler.load(bl)` переносит handlers/middlewares и подменяет `bl.message_view` на общий view.

---

## Структура проекта

```
code/
├── PLAN.md                 ← этот файл
├── README.md               ← как запустить
├── .env.example            ← шаблон ключей
├── .gitignore
├── requirements.txt
├── pytest.ini
├── bot.py                  ← точка входа
├── config.py               ← загрузка .env + composition root
├── middlewares.py          ← логирование событий
├── history.py              ← история диалогов (in-memory)
├── ai/
│   ├── __init__.py
│   ├── errors.py           ← AIClientError
│   └── proxyapi.py         ← клиент ProxyAPI
├── handlers/
│   ├── __init__.py         ← реэкспорт лейблеров
│   ├── greeting.py         ← приветствие новичков
│   └── chat.py             ← AI-ответы
├── tests/
│   ├── conftest.py         ← изолированный .env, мгновенный backoff, сборка бота
│   ├── helpers.py          ← мок-сервер ProxyAPI, синтетические Message
│   ├── test_config.py      ← тесты конфигурации
│   ├── test_history.py     ← тесты истории
│   ├── test_rules.py       ← правила vkbottle
│   ├── test_ai_client.py   ← клиент против мок-сервера
│   ├── test_handlers.py    ← приветствие и AI-ответы
│   ├── test_dispatch.py    ← сквозная маршрутизация событий
│   └── test_bot.py         ← сборка бота
├── docs/                   ← выжимка документации vkbottle (уже есть)
└── venv/
```

Разделение кода — по [docs/09-code-separation.md](docs/09-code-separation.md): отдельные `BotLabeler` на модуль + `labeler.load(...)`.

---

## Этапы

### Этап 1 — Зависимости и конфигурация
- [x] `python-dotenv` установлен в venv
- [x] `requirements.txt`, `.gitignore`
- [x] `.env.example` со всеми переменными
- [x] `config.py`: `Settings` (frozen dataclass), `load_settings()`, `ConfigError`, ленивые синглтоны

**Переменные окружения:**

| Переменная | Обязательна | По умолчанию | Назначение |
|---|---|---|---|
| `VK_TOKEN` | ✅ | — | ключ сообщества |
| `PROXYAPI_API_KEY` | ✅ | — | ключ ProxyAPI (`sk-...`) |
| `PROXYAPI_BASE_URL` | | `https://api.proxyapi.ru/v1` | базовый адрес провайдера |
| `AI_MODEL` | | `openai/gpt-5.4-mini` | модель |
| `AI_SYSTEM_PROMPT` | | промпт ассистента | системная инструкция |
| `AI_TEMPERATURE` | | `0.7` | температура (пусто → не отправлять) |
| `AI_MAX_TOKENS` | | `1000` | лимит ответа (пусто → не отправлять) |
| `AI_TIMEOUT` | | `60` | таймаут запроса, с |
| `AI_MAX_RETRIES` | | `3` | повторы при 429/5xx и сетевых ошибках |
| `AI_HISTORY_PAIRS` | | `10` | глубина истории (пар реплик) |
| `GREETING_TEXT` | | ... | приветствие участника, `{name}` |
| `BOT_GREETING_TEXT` | | ... | когда в беседу добавили самого бота |
| `LOG_LEVEL` | | `INFO` | уровень логирования |

### Этап 2 — AI-клиент
- [x] `ai/proxyapi.py`: `ProxyAIClient.ask(messages) -> str`, `close()`
- [x] `AIClientError` с `status` и текстом ошибки
- [x] Ретраи на 429/500/502/503/504 + сетевые ошибки, экспоненциальный backoff
- [x] Фоллбэк: при 400 и наличии опциональных параметров — повторить без них
- [x] Разбор ошибок `detail` / `error.message`
- [x] Ленивое создание `aiohttp.ClientSession`, закрытие в `on_shutdown`

### Этап 3 — История диалога
- [x] `history.py`: `DialogHistory`, ключ `(peer_id, from_id)`, `deque(maxlen=2*pairs)`
- [x] Хранятся только `user`/`assistant`; системный промпт добавляется при запросе

### Этап 4 — Хендлеры
- [x] `handlers/greeting.py` — `chat_message(action=[...])`, получение имени через `users.get`, ответ на добавление самого бота
- [x] `handlers/chat.py` — `private_message()` + `chat_message(MentionRule(mention_only=False))`, общий `_reply_with_ai`
- [x] `auto_rules = [FromUserRule()]` — игнор сообщений от ботов

### Этап 5 — Сборка бота
- [x] `middlewares.py` — лог-мидлварь (`pre`/`post`)
- [x] `bot.py`: `create_bot()` → `replace_mention=True`, `load()` лейблеров, мидлварь, error-handler'ы (`VKAPIError[901/902/903]`, всё `VKAPIError`, undefined), `on_shutdown` для закрытия сессии, `bot.run()`
- [x] Fail-fast при пустом `.env` с понятным сообщением

### Этап 6 — Проверка
- [x] Синтаксис и импорты всех модулей
- [x] `load_settings()` — обязательные/опциональные/битые числа
- [x] `DialogHistory` — обрезка по maxlen, ключи изолированы
- [x] `ProxyAIClient` — **мок-сервер aiohttp**: успех, 400-фоллбэк, 429-ретрай, `detail`, `error.message`
- [x] Правила на синтетических `Message`: упоминание в беседе / без упоминания / ЛС / сервис-сообщение
- [x] Регистрация хендлеров: счётчик в `message_view.handlers`, `replace_mention=True`
- [x] `python -m compileall`

### Этап 7 — Документация
- [x] `README.md` с инструкцией запуска

---

## Что НЕ входит в задачу

- Callback API / свой сервер — используется LongPoll.
- Хранение истории в БД (только память, после рестарта очищается).
- Вложения, картинки, стриминг ответа.
- Юзербот.

---

## Риски

| Риск | Реакция |
|---|---|
| Модель отклоняет `temperature`/`max_tokens` (400) | Автоповтор без опциональных параметров |
| Пустой баланс (402) | Понятное сообщение в лог и пользователю |
| VK 902 — ЛС закрыты | Error-handler залогирует, не падает |
| Длинный ответ AI (>4096) | `message.answer()` режет сам |
| Рестарт — история теряется | Принято и задокументировано |

---

## Статус (итог)

Все этапы выполнены. Проверки:

- `python -m compileall` — ок.
- `python -m pytest` — **62 passed** (конфиг, история, правила, AI-клиент против
  мок-сервера, хендлеры, сквозная маршрутизация, сборка бота).
- `python bot.py` без `.env` — код возврата `1` и понятное сообщение о недостающих
  `VK_TOKEN` / `PROXYAPI_API_KEY` (fail-fast проверен).
- `bot.run()` → `run_polling()` → `BotPolling.listen()` — LongPoll подтверждён в
  исходниках vkbottle 4.11.0.

**Осталось для живого запуска** (требуется от вас):

1. `Copy-Item .env.example .env` и вписать `VK_TOKEN` и `PROXYAPI_API_KEY`.
2. `python bot.py`.
3. Проверить в ЛС бота и в беседе: упоминание в беседе → ответ, вход нового
   участника → приветствие.

Примечание: `labeler.load()` подменяет `bl.message_view` у общих лейблеров — для
продакшена это безвредно (бот собирается один раз), но в тестах из-за этого порядок
файлов имел бы значение. Фикстура `restore_labelers` в `tests/conftest.py` возвращает
исходные view после каждого теста.
