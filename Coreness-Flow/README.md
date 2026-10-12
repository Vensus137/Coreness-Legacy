# Coreness Flow

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Electron](https://img.shields.io/badge/Electron-React-47848F.svg?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Windows](https://img.shields.io/badge/Windows-10%2B-0078D6.svg?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🌐 **Язык:** **Русский** | [English](README_EN.md)

Большинство AI-ассистентов — это чат. `Coreness Flow` другой.

Агент не ждёт сообщения — он **реагирует на события**: входящий webhook, расписание, сигнал от плагина. Получив событие, запускает **сценарий** — цепочку шагов с вызовами LLM, переходами и действиями сторонних сервисов. Логика описана в **YAML** и меняется без правок кода.

Всё локально. Windows. Один пользователь под полным контролем.

## 🏗️ Как это устроено

```
Событие (чат / webhook / cron / API)
         ↓
Движок сценариев — матчит триггеры, запускает цепочку шагов
         ↓
Плагины — выполняют действия, вызывают LLM, пишут в хранилище
         ↓
UI получает результат через API Bus
```

Слои не знают друг о друге напрямую. **UI** — React поверх Electron, общается с бэкендом только через WebSocket и API Bus. **Плагины** — изолированные Python-модули; ядро находит их по `config.json`, регистрирует actions и передаёт управление. Новая интеграция — новая папка, без изменений в ядре.

## ✨ Что умеет

**📋 Сценарии на YAML**  
Триггеры (сообщение, webhook, cron), шаги, условные переходы, вызовы между сценариями. Данные передаются через `_cache` и плейсхолдеры — для простых цепочек код не нужен.

**⚡ Async-действия**  
Долгие операции запускаются в фоне через `call_nowait`, сценарий продолжается без блокировки. Готовность проверяется через плейсхолдеры `_async_action`.

**🔌 Плагинная система и контрибьюты в UI**  
Архитектура как у VS Code: `config.json` описывает metadata, settings, actions и **contributes**. Через contributes плагин добавляет вкладки, пункты сайдбара, секции настроек — фронт строит UI по данным одним вызовом `get_contributions`. Модель по аналогии с [VS Code Contribution Points](https://code.visualstudio.com/api/references/contribution-points), адаптирована под приложение.

**🤖 LLM и RAG**  
Роутинг запросов по сложности: простые задачи на дешёвую модель, сложные — на мощную. RAG локально: BGE-M3 ONNX INT8 + Qdrant embedded, без обязательных внешних сервисов.

## 🛠 Стек

| Компонент | Технология |
| :-- | :-- |
| Frontend | Electron + React |
| Backend | Python 3.11 |
| Транспорт | WebSocket, API Bus (actions + events) |
| LLM | OpenAI-совместимый API (агрегаторы) |
| RAG | BGE-M3 ONNX INT8 + Qdrant embedded |
| Хранилище | SQLite + JSON (конфиг) + YAML (сценарии) |

## 🎬 Демо

### Загрузка и главный чат

Сплеш-интро: запуск приложения, переход в главный чат — можно сразу задать вопрос.

<img src="https://habrastorage.org/webt/v9/ud/0t/v9ud0tfxjq0m7bmcea0dh1iplu8.gif" width="560" alt="Сплеш-интро"/>

### Чат

Удаление история чата и новые диалоги.

<img src="https://habrastorage.org/webt/j5/d_/dz/j5d_dzcamjcqndvciw8k5devyy4.gif" width="560" alt="Чат"/>

### Общие настройки

Общие настройки и возможности.

<img src="https://habrastorage.org/webt/fp/1t/ep/fp1tep2dacjxpngwbmlfgktke9i.gif" width="560" alt="Общие настройки"/>

### AI и векторное хранилище

Настройки AI-провайдера, векторное хранилище и управление им: просмотр и удаление чанков.

<img src="https://habrastorage.org/webt/5z/gf/re/5zgfrer-o4eebhvjcht-bpeevxy.gif" width="560" alt="AI и векторное хранилище"/>

## 👥 Для кого

- **Технари и аналитики** — персональная автоматизация без SaaS-подписок
- **Менеджеры и тимлиды** — единая точка для рутины: статусы, отчёты, мониторинг
- **Разработчики** — пример event-driven десктопного приложения с плагинами и контрибьютами в UI

## 🚀 Быстрый старт

**Из исходников** (нужны Python 3.11, Node.js, Windows):

```powershell
pip install -r requirements.txt
cd frontend && npm install && cd ..
.\scripts\run-dev.ps1
```

Backend и окно приложения поднимаются одной командой с hot reload.

**Или установка из релизов:** перейдите в блок **Releases** на странице репозитория, скачайте установщик для Windows и следуйте инструкциям в описании релиза.

## 📖 Документация

| Раздел | Документ |
| :-- | :-- |
| Архитектура | [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) |
| Плагины | [PLUGINS.md](docs/architecture/PLUGINS.md) |
| Сценарии | [SCENARIO_CONFIG_GUIDE.md](docs/configuration/SCENARIO_CONFIG_GUIDE.md) |
| Контрибьюты в UI | [CONTRIBUTION_REFERENCE.md](docs/reference/CONTRIBUTION_REFERENCE.md) |
| UI-гайдлайны | [UI_GUIDELINES.md](docs/architecture/UI_GUIDELINES.md) |

Навигация по разделам — **[docs/README.md](docs/README.md)**.

## 📄 Лицензия

Распространяется под лицензией [MIT](LICENSE).

<p align="center">
  <strong>Coreness</strong> — Create. Automate. Scale.
</p>
