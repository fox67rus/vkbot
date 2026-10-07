# 07. Состояния: State Dispenser и Waiter Machine

Источники:
- <https://vkbottle.readthedocs.io/ru/latest/high-level/handling/state-dispenser/>
- <https://vkbottle.readthedocs.io/ru/latest/tools/waiter-machine/>

## State Dispenser

StateDispenser'ы нужны для организации веточной системы пользователя: сложное меню, квиз, игра — это стейты.

### Методы

| Метод | Описание |
|---|---|
| `get(peer_id)` | Возвращает `StatePeer` (если запись есть) или `None` |
| `set(peer_id, state)` | Делает запись |
| `delete(peer_id)` | Удаляет запись |

Текущий стейт события доступен как `event.state_peer.state`.

### Полный пример

```python
from vkbottle import BaseStateGroup
from vkbottle.bot import Message, Bot

bot = Bot("t")

class SuperStates(BaseStateGroup):
    AWKWARD_STATE = "awkward"
    CONFIDENT_STATE = "confident"
    TERRIFYING_STATE = "terrifying"

@bot.on.message(state=SuperStates.AWKWARD_STATE)  # StateRule(SuperStates.AWKWARD_STATE)
async def awkward_handler(message: Message):
    await message.answer("oi awkward")

@bot.on.message(lev="/die")
async def die_handler(message: Message):
    await bot.state_dispenser.set(message.peer_id, SuperStates.AWKWARD_STATE)
    return "ok"

bot.run_forever()
```

### Ловить стейты

- `state=...` → `StateRule(state)`
- `state_group=...` → `StateGroupRule(state_group)`
- `StateRule(None)` → проверяет, что пользователь **не** находится ни в каком состоянии

### Payload в стейтах

`.set()` может принимать `**payload`, позже доступный как словарь из `message.state_peer.payload`:

```python
# ... In handler:
await bot.state_dispenser.set(message.peer_id, SuperStates.TERRIFYING_STATE, something=1)

# ... With state:
print(message.state_peer.payload["something"])  # 1
```

### Базовый стейт-диспенсер

```python
from vkbottle import API, BuiltinStateDispenser

state_dispenser = BuiltinStateDispenser()
```

Пераётся в `Bot`:

```python
bot = Bot(
    api=api,
    labeler=labeler,
    state_dispenser=state_dispenser,
)
```

---

## Waiter Machine

Waiter Machine — для создания быстрых воронок **без потери скоупа**.

> В отличие от State Dispenser, состояния никуда не сериализуются, поэтому Waiter Machine **не следует использовать** для сложных стейтов, где важна консистентность (например, транзакции) или которые активны долгое время.

### Простейший пример

```python
from vkbottle.bot import Bot, Message
from vkbottle.tools import WaiterMachine

bot = Bot("...")
wm = WaiterMachine()

@bot.on.message(text="/wm")
async def greeting(message: Message):
    await message.answer("Как тебя зовут?")
    # Следующая строчка остановит выполнение хендлера,
    # и исполнение пойдет дальше только когда будет получено
    # сообщение соответствующее заданным правилам
    # (в данном случае просто от того же пользователя)
    m, _ = await wm.wait(bot.on.message_view, message)
    await message.answer(f"Привет, {m.text.capitalize()}! Будем знакомы.")

bot.run_forever()
```

Из `.wait` возвращается **tuple** из двух элементов:
1. объект события, разрешившего ожидание (здесь — `Message`)
2. контекст, сформированный в ходе обработки события

Поэтому его можно сразу раскрыть в две переменные.

### `.wait` с правилами и `default_behaviour`

```python
await message.answer("Напиши мне твой номер телефона")
m, ctx = await wm.wait(bot.on.message_view, message, RegexRule(PHONE_NUMBER_REGEX), default_behaviour="Неверный формат, напиши еще раз в правильном формате")
```

`default_behaviour` принимает `Callable` (куда придёт событие) **либо любой другой объект**, который будет передан в return manager привязанный к активному view и обработан. В примере выше — строка, отправляемая как сообщение.

### `expiration`

Принимает `timedelta` или `int` (в секундах) — ограничивает время ожидания. Если ивент придёт позже `start_ts + expiration`, будет вызван `drop`, и ивент обработается в обычном view.

### `.drop`

Сбрасывает ожидание ивента по идентификатору.

---

## Что выбрать

| | State Dispenser | Waiter Machine |
|---|---|---|
| Хранение | сериализуется | в памяти, не сериализуется |
| Время жизни | долгое | короткое (воронка) |
| Сложные стейты / транзакции | ✅ да | ❌ нет |
| Простая последовательность вопросов | можно | ✅ удобнее |
