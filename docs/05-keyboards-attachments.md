# 05. Клавиатуры, вложения, шаблоны

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/tutorial/keyboards-attachments/>
- <https://vkbottle.readthedocs.io/ru/latest/tools/keyboard/>
- <https://vkbottle.readthedocs.io/ru/latest/tools/template/>
- <https://vkbottle.readthedocs.io/ru/latest/tools/uploaders/>

## Клавиатура

> Подразумевается, что вы уже ознакомились с [документацией ВК](https://dev.vk.ru/api/bots/development/keyboard).

Импортируются `Keyboard`, `KeyboardButtonColor` и нужные `action` (например `Text`, `OpenLink`, `Location`, `VKApps`, `Callback`).

```python
from vkbottle import Keyboard, KeyboardButtonColor, Text

keyboard = Keyboard(one_time=True, inline=False)

keyboard.add(Text("Кнопка 1"), color=KeyboardButtonColor.POSITIVE)
# Первая строка (ряд) добавляется автоматически
keyboard.row()  # Переходим на следующую строку
keyboard.add(Text("Кнопка 2"))
keyboard.add(Text("Кнопка 3", payload={"command": 3}))
```

`one_time` и `inline` описаны в [документации ВК](https://vk.ru/dev/bots_docs_3?f=4.2.%20Структура%20данных).

### Методы `Keyboard`

| Метод | Описание |
|---|---|
| `add(action, color)` | добавляет кнопку к текущему ряду |
| `row()` | создаёт следующий ряд, переводит «курсор» |
| `get_json()` | преобразует клавиатуру в JSON для отправки |

### Билдер-интерфейс

```python
from vkbottle import Keyboard, KeyboardButtonColor, Text

# ...
keyboard = (
    Keyboard(one_time=True, inline=False)
    .add(Text("Кнопка 1"), color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("Кнопка 2"))
    .add(Text("Кнопка 3", payload={"command": 3}))
).get_json()

await message.answer(
    message="Смотри сколько кнопок!!",
    keyboard=keyboard)
```

### Отправка

```python
keyboard = ...  # see examples above

@bot.on.message()
async def send_keyboard(message):
    await message.answer("Here is your keyboard!", keyboard=keyboard)
```

Или:

```python
await message.answer(message="Смотри сколько кнопок!!", keyboard=keyboard.get_json())
```

> Клавиатура использует `json.dumps`. Если клавиатура статична — создайте её один раз и переиспользуйте готовый JSON.

> **Удаление клавиатуры** у пользователя: отправьте `EMPTY_KEYBOARD`.

Пример: [generate_keyboard.py](https://github.com/vkbottle/vkbottle/tree/master/examples/high-level/generate_keyboard.py)

---

## Вложения

### Если уже есть ссылка на вложение

Формат `"type{OWNER_ID}_{ITEM_ID}"`, например `"photo-41629685_457239401"`:

```python
attachment = ... # see example above

@bot.on.message
async def send_attachment(message):
    await message.answer("See that attachment!", attachment=attachment)
```

> В документации опечатка в декораторе (`@bot.on.messageasync`) — корректно `@bot.on.message()`.

### Если загружаете вложения динамически

Нужны загрузчики ([Uploaders](https://vkbottle.readthedocs.io/ru/latest/tools/uploaders/)):

```python
uploader = AnyUploader(bot.api)  # see uploaders types in "Uploaders documentation" above

@bot.on.message()
async def send_attachment(message):
    attachment = await uploader.upload("path/to/file")
    await message.answer("See that attachment!", attachment=attachment)
```

---

## Загрузчики (Uploaders)

Загрузка медиа в ВК. Принимают объект `API` при инициализации.

| Тип | Классы |
|---|---|
| **photo** | `PhotoMessageUploader` (в сообщение), `PhotoToAlbumUploader` (в альбом), `PhotoWallUploader` (на стену), `PhotoFaviconUploader` (аватарка), `PhotoChatFaviconUploader` (аватарка беседы), `PhotoMarketUploader` (картинка товара) |
| **doc** | `DocWallUploader` (на стену), `DocMessagesUploader` (в сообщение), `VoiceMessageUploader` (голосовые), `GraffitiUploader` (граффити) |
| **audio** | `AudioUploader` |
| **video** | `VideoUploader` |
| **speech** | аудио для распознавания речи |

### Интерфейс

- `.upload(...)` — возвращает **готовую строку аттачмента**
- `.raw_upload(...)` — возвращает **словарь** с ответом сервера

Оба имеют одинаковый интерфейс. Способ получения сервера различается — `.get_server(...)`.

> Не все аплоадеры имеют метод `upload` — для них невозможно вернуть строку аттачмента.

Методы базового класса (одинаковые для всех):
- `.upload_files(url, files)` — загрузка файлов методом POST
- `.get_bytes_io(data)` — приводит сырые байты в подходящий для ВК вид
- `.generate_attachment_string(attachment_type, owner_id, item_id, access_key)` — делает строку, которую ВК принимает как медиа
- `.read(file_source)` — читает файл; если `file_source` строка — из файла, если байты — возвращает их

Обычно нужен только `upload`.

### Пример

```python
from vkbottle import PhotoMessageUploader
from vkbottle.bot import Bot

bot = Bot("token")
photo_uploader = PhotoMessageUploader(bot.api)

@bot.on.message(text="photo")
async def handler(message):
    photo = await photo_uploader.upload(
        file_source="photo.png",
        peer_id=m.peer_id,
    )
    await message.answer(attachment=photo)

bot.run_forever()
```

Пример: [uploaders_example.py](https://github.com/vkbottle/vkbottle/blob/master/examples/high-level/uploaders_example.py)

---

## Шаблоны (Template)

ВК поддерживает один вид шаблона — **карусель**. [Документация ВК по шаблонам](https://vk.ru/dev/bot_docs_templates?f=5.%20Шаблоны%20сообщений)

- `TemplateElement` — элемент шаблона; названия полей совпадают с документацией ВК
- `template_gen` — создаёт шаблон из элементов

```python
from vkbottle import TemplateElement, template_gen

my_template = template_gen(
    TemplateElement(...), # о том как нужно сочетать параметры можно
    TemplateElement(...)  # прочитать в документации Вконтакте выше)
# my_template - готовый для отправки json
# ...
await message.answer("Держи карусель!", template=my_template)
```

Или:

```python
from vkbottle.tools import template_gen, TemplateElement

my_template = template_gen(TemplateElement(...), TemplateElement(...), TemplateElement(...))
```

Отправка:

```python
my_template = ...  # see example above

@bot.on.message()
async def send_template(message):
    await message.answer("Sending template...", template=my_template)
```
