# Плагины — разработка и конфигурация

Все плагины в `plugins/`. Контейнер рекурсивно находит папки с файлом **config.json** и загружает плагины. Имя папки = имя плагина. Конфигурация плагина — один файл **config.json** с универсальной структурой (metadata, settings, actions, contributes). Все плагины следуют единому контракту (config, context).

---

## Слои плагинов

| Слой | Назначение |
|------|------------|
| **core** | Модули приложения (бэкенд, чаты, БД и т.д.); могут регистрировать actions с emit в UI. |
| **base** | Входят в сборку, но не ключевые — без них приложение работает. |
| **extensions** | Кастомные расширения и интеграции (в перспективе — маркетплейс). |

---

## Структура папки плагина

```
plugins/<путь>/<имя_плагина>/
├── config.json        # Обязательно — конфиг (metadata, settings, actions, contributes)
├── <имя_плагина>.py   # Главный модуль плагина (имя файла = имя плагина)
├── modules/           # Дополнительные модули (не в корне)
│   └── ...
└── tests/             # Опционально — тесты плагина
```

Примеры: `plugins/core/database/`, `plugins/core/chats/` (чаты + send_chat_message/clear_chat для UI), `plugins/base/validator/`.

---

## Формат config.json

Единая структура для приложения (config/app.json) и всех плагинов (config.json в папке плагина):

| Секция | Содержимое |
|--------|-------------|
| **metadata** | name (= plugin_id), description |
| **settings** | Схема настроек: для каждой настройки — type, default, description (опционально min, max, options). Дефолты мержатся с user_settings[plugin_id]. |
| **actions** | Описание действий для регистрации в API Bus: description, input (payload), output (result, error, response_data). |
| **contributes** | Контрибьют в UI (как в VS Code): **contributes.workspace** — вкладка (id, label, icon, layout). Справочник опций: [CONTRIBUTION_REFERENCE.md](CONTRIBUTION_REFERENCE.md). Гайд: ниже [Контрибьюты в UI](#контрибьюты-в-ui). |

Пример:

```json
{
  "metadata": {
    "name": "database",
    "description": "Локальное хранилище SQLite"
  },
  "settings": {
    "db_path": {
      "type": "string",
      "default": "data/data.db",
      "description": "Путь к файлу БД"
    }
  },
  "actions": {
    "get_record": {
      "description": "Получить запись по id",
      "input": {
        "payload": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "optional": false }
          }
        }
      },
      "output": {
        "result": { "type": "string", "description": "success | error" },
        "error": { "type": "object", "properties": { "code": {}, "message": {} } },
        "response_data": { "type": "object", "properties": { "record": {} } }
      }
    }
  },
  "contributes": {}
}
```

- Обработчик действия получает один аргумент **payload** (dict) и возвращает dict с ключами `result`, при ошибке `error`, при успехе с данными — `response_data`.

---

## Контракт плагина

Конструктор — **два аргумента по порядку**: **config**, затем **context**.

```python
def __init__(self, config: dict, context):
    self.config = config
    self.api_bus = context.api_bus
    self.logger = context.logger
```

- **config** — целевая структура, без раскрытия во флэт: **metadata** (из config.json: name, description), **settings** (мерж дефолтов и user_settings[plugin_id] — настройки плагина), **actions**, **contributes**, **app_metadata** (подкладывает ядро — те же данные, что возвращает get_app_metadata: неизменяемые атрибуты приложения, основные пути и т.п., для исключения повторных вызовов). Плагины читают настройки из config["settings"], метаданные приложения — из config["app_metadata"]; config["metadata"] — свои метаданные (name, description). При необходимости получения актуальных метаданных приложения — через `api_bus.call("get_app_metadata", {})`.
- **context** — AppContext (api_bus, logger и т.д.). Регистрация действий выполняется контейнером по config["actions"]; вручную register в плагине не нужен.

Имена методов класса должны совпадать с ключами в **actions** (например `get_record` → метод `get_record(self, payload)`).

---

## Настройки, редактируемые из UI: подписка на обновление

Если плагин объявляет **contributes.settings** (поля настроек во вкладке «Настройки»), то при сохранении из UI бэкенд эмитит событие **`plugin:settings_changed:{plugin_id}`** (имя события содержит идентификатор плагина). В обработчик приходит только тот плагин, чьи настройки изменились — подписка идёт на своё событие, лишние вызовы других плагинов не происходят.

Плагин **обязан** подписаться на своё событие и применить новые настройки к состоянию (config, клиенты, кэши). Иначе сервис продолжит использовать старый config до перезапуска.

**Что сделать:**

1. Сохранить свой `plugin_id`: `self._plugin_id = (config.get("metadata") or {}).get("name")`.
2. В `__init__` подписаться на **своё** событие: `context.api_bus.subscribe(f"plugin:settings_changed:{self._plugin_id}", self._on_settings_changed)`.
3. Реализовать `_on_settings_changed(self, data: dict)`: в `data` приходит `{"plugin_id": ..., "settings": ...}`; обновить `self.config["settings"]` и все производные атрибуты/клиенты (пересоздать клиент, сбросить кэш и т.д.). Проверка `plugin_id` в обработчике не нужна — событие уже привязано к плагину.

Примеры: `plugins/core/vector_store/vector_store.py`, `plugins/core/database/database.py`, `plugins/core/ai_service/ai_service.py`, `plugins/base/download_service/download_service.py`.

---

## Вызовы действий (API Bus)

Плагины вызывают действия других плагинов или ядра через **api_bus**:

- **`await api_bus.call(action_name, payload)`** — вызов с ожиданием результата. Возвращает dict (`result`, `error`, `response_data`). Используйте, когда нужен ответ для дальнейшей логики.
- **`await api_bus.call_nowait(action_name, payload)`** — запуск без ожидания. Формат ответа тот же, что у **call**: при успехе — `{"result": "success"}`, при ошибке (action не найден, неверный payload) — обычный объект с `result` и `error`. После успешного возврата выполнение идёт в фоне, ошибки фона логируются. Подходит для длинных цепочек, результат которых приходит через события.

<sup>1</sup> **Сценарии и интеграции:** запуск сценариев (и в перспективе другие интеграции, генерация событий) — длинная цепочка, которая по сути не предполагает ответа в момент вызова; если ответ нужен, его можно реализовать внутри сценария (например отправкой сообщения в чат). Такие точки входа имеет смысл вызывать через **call_nowait**, чтобы не блокировать вызывающий код и остальные запросы.

---

## Многопоточность

Обработчики actions выполняются в worker-потоке (отдельный event loop). Настройка числа воркеров — в app.json (settings.api_bus.max_workers).

---

## run_blocking() и run()

- **run_blocking(progress_callback=None)** — опционально. Синхронный метод, вызывается контейнером **до показа основного окна** (пока splash). Для тяжёлой инициализации (например загрузка модели). `progress_callback(percent, message)` — для обновления прогресса на splash.
- **run()** — опционально. `async def run()` запускается контейнером в основном event loop. Использовать `await` для IO; тяжёлые синхронные операции — через `asyncio.to_thread()`.

---

## Импорты

Все импорты — **в начале файла плагина**, не внутри методов. Приложение загружает плагины в главном процессе; ленивые импорты в __init__/run/actions не допускаются (splash и изоляция процессов).

---

## Типы плагинов

- **Backend:** бизнес-логика, actions для сценариев и других плагинов (core, base, extensions).
- Плагины **core** при необходимости регистрируют действия с emit во frontend (например send_chat_message → chat:new_message). **base** и **extensions** — вывод в UI только через контракт воркспейсов (см. ниже).

---

## Контрибьюты в UI

Плагины объявляют в **contributes** в config.json вкладки, пункты сайдбара и меню. Приложение запрашивает контрибьюты вызовом **get_contributions** и строит UI по данным. Схемы точек контрибьюта, правила разработки и доработки слоя — **[CONTRIBUTION_REFERENCE.md](CONTRIBUTION_REFERENCE.md)**.

**Как объявить вкладку:** в config.json задать `contributes.workspace` по схеме из справочника; пункт появится в сайдбаре, по клику откроется вкладка.
