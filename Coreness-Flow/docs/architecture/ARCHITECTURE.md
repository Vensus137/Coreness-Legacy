# Архитектура проекта

Локальное desktop-приложение для автоматизации со встроенным AI (LLM + RAG). Один пользователь, Windows; интеграции с внешними системами (LLM, Discord, Slack, API).

---

## Требования к системе

- **Python:** 3.11 (рекомендуется; 3.12+ может потребовать проверки совместимости зависимостей)

---

## Стек и основные библиотеки

| Назначение | Технология |
|------------|------------|
| Язык | Python |
| LLM | Внешние агрегаторы (OpenAI-совместимый API, плагин ai_service) |
| Эмбеддинги / RAG | BGE-M3 ONNX INT8 + Qdrant (плагин vector_store) |
| Хранилище | SQLite (плагин database), Qdrant (векторное, embedded) |
| Конфигурация | JSON (настройки приложения и плагинов); YAML — сценарии |
| UI | Electron + React (frontend в `frontend/`) |
| Сборка | Electron Builder + Python backend |

---

## Принципы архитектуры

### Разделение слоёв

- **UI Layer:** frontend на Electron (React) в `frontend/`: экраны, компоненты, вызов backend по WebSocket. Без бизнес-логики; контракт обмена = API Bus (actions + events).
- **Backend Layer:** плагины с бизнес-логикой. Не знают про UI напрямую.
- **API Bus:** единая шина коммуникации между слоями (actions + events).

### Backend плагины

- **Хореография:** плагины самодостаточны, связь только через API Bus.
- **Единый контракт:** все плагины получают (config, context).
- **Конфигурация в приложении:** ядро передаёт плагинам `config` — целевую структуру (metadata, settings, actions, ui, app_metadata). Настройки мержатся из config.json + user_settings; метаданные приложения (project_root, data_path) — в **config["app_metadata"]**. **data_path** — каталог данных приложения (логи, БД, загрузки; напр. %APPDATA%\\CorenessFlow), не путать с **config["metadata"]** плагина (name, description).
- **Async-first:** плагины — async/await; actions и `run()` — всегда `async def`.
- **Обработка ошибок:** API Bus возвращает dict с явным `result` (success/error).

### API Bus

**Actions (request-response):** вызов с ожиданием ответа.  
**Events (fire-and-forget):** уведомления без ожидания ответа.

- Actions регистрируются контейнером из секции **actions** файла **config.json** плагина.
- Вызов действий: **call** — с ожиданием результата; **call_nowait** — запуск без ожидания.
- Events — для уведомления UI о событиях от бэкенда.

### UI плагины-мосты

Плагин **chats** (core) регистрирует в т.ч. `send_chat_message` и `clear_chat`: запись в storage и `api_bus.emit()` для UI. Сценарии вызывают эти действия по имени.

### UI Layer

Frontend (React) в `frontend/`; связь с backend по WebSocket (действия и события API Bus, JSON). Конфиг приложения передаётся с backend при инициализации или по запросу. Состав вкладок и сайдбара задаётся контрибьютами плагинов. Схемы точек контрибьюта и правила разработки слоя — [CONTRIBUTION_REFERENCE.md](CONTRIBUTION_REFERENCE.md); краткий гайд для плагинов — [PLUGINS.md](PLUGINS.md#контрибьюты-в-ui).

---

## Конфигурация и настройки

| Что | Где |
|-----|-----|
| Переопределения пользователя | `%APPDATA%\CorenessFlow\user_settings.json` (только изменённые значения) |
| Дефолты приложения | `config/app.json` (репозиторий) |
| Дефолты плагинов | Секция **settings** в **config.json** в папке плагина |

**Мерж:** для приложения — app.json + user_settings["app"] (user перекрывает). Для плагина конфиг — структура **metadata**, **settings**, **actions**, **contributes**, **app_metadata**. В **app_metadata** контейнер подкладывает пути (project_root, data_path). Действие get_app_metadata возвращает **paths** (для внутреннего использования) и **about** (для UI «О приложении»); для актуальных данных — вызывать get_app_metadata. Плагины берут настройки из config["settings"], метаданные приложения — из config["app_metadata"]. Секреты/токены — в SQLite через соответствующий плагин.

**Graceful shutdown:** таймауты (di_container_timeout, plugin_timeout и т.д.) задаются в app.json (секция settings / shutdown).

---

## Lifecycle

Electron main process запускает Python backend (отдельный процесс); backend поднимает API Bus, плагины, WebSocket-сервер. Окно открывает frontend (React); frontend подключается по WebSocket и вызывает actions / подписывается на events. Порядок: Electron main → spawn backend → инициализация backend → frontend загружается и подключается к backend.

**Порядок инициализации backend:** точка входа `run_backend.py` → API Bus → контейнер сканирует `plugins/` по наличию **config.json** → загрузка app.json + user_settings.json → для каждой папки плагина загрузка config.json, мерж с user_settings[plugin_id], подкладывание app_metadata → создание экземпляров плагинов (config, context), регистрация actions → run_blocking() при необходимости → run() в фоне → запуск WebSocket-сервера и ожидание подключения frontend.

---

## Структура проекта

```
Coreness-Flow/
├── run_backend.py             # Точка входа backend (запускается из Electron)
├── app/
│   ├── runtime/
│   │   ├── container.py       # Обнаружение плагинов (config.json), мерж конфига, создание экземпляров
│   │   ├── api_bus.py
│   │   ├── context.py
│   │   ├── logger.py
│   │   └── ...
│   ├── settings.py            # Загрузка app.json, user_settings.json, мерж, get_app_metadata
│   ├── backend_runner.py      # Инициализация ядра без UI (для Electron)
│   ├── ws_server.py           # WebSocket-сервер для frontend
│   └── ...
├── frontend/                  # Electron + React
│   ├── src/                   # Компоненты, стили, API (WebSocket)
│   ├── electron/              # Main process (окно, запуск backend)
│   └── ...
├── plugins/
│   ├── core/                  # Модули приложения (бэкенд)
│   │   ├── database/
│   │   │   ├── config.json
│   │   │   ├── database.py
│   │   │   ├── modules/
│   │   │   └── tests/
│   │   ├── chats/             # Чаты: storage + send_chat_message/clear_chat (emit в UI)
│   │   │   ├── config.json
│   │   │   └── chats.py
│   │   └── ...
│   ├── base/                  # В сборке, не ключевые
│   │   └── ...
│   └── extensions/            # Кастомные расширения (в перспективе)
│       └── ...
├── config/
│   ├── app.json               # Дефолты приложения (metadata, settings, actions, ui)
│   └── scenarios/             # Сценарии (YAML)
└── data/                      # Единая папка для данных (БД, Qdrant, логи, скачивания и т.д.)
    └── ...                    # Плагины сами решают что и в каком формате хранить
```

- **plugins/** — контейнер рекурсивно ищет папки с файлом **config.json** (имя папки = имя плагина). В корне плагина: `<имя_плагина>.py`, config.json, папка modules/ для кода, опционально tests/.
- **config/app.json** — тот же формат, что у плагинов (metadata.name = "app", settings с дефолтами приложения).
- **config/scenarios/** — YAML сценариев, поиск по мере надобности плагинами.
- **data/** — корневая папка для данных приложения и плагинов (SQLite, Qdrant, логи, скачивания). Формат и структура внутри — на усмотрение плагинов.
