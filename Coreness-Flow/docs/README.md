# Документация

## Архитектура и контракты
- [ARCHITECTURE.md](architecture/ARCHITECTURE.md) — архитектура, слои, API Bus, конфигурация, lifecycle, структура проекта
- [PLUGINS.md](architecture/PLUGINS.md) — слои плагинов, контракт, config.json, контрибьюты в UI (get_contributions, гайд)
- [UI_GUIDELINES.md](architecture/UI_GUIDELINES.md) — UI Layer (Electron + React), layout, Design System

## Конфигурация
- [SCENARIO_CONFIG_GUIDE.md](configuration/SCENARIO_CONFIG_GUIDE.md) — сценарии: YAML, триггеры, шаги, переходы
- [AGENT_ROUTING.md](configuration/AGENT_ROUTING.md) — роутинг агента, тулзы как сценарии, кэш, модель для роутинга
- [STORAGE.md](configuration/STORAGE.md) — хранилище в сценариях (group_key + key → value)

## Справочники
- [ACTION_GUIDE.md](reference/ACTION_GUIDE.md) — гайд по действиям плагинов (вход/выход, параметры)
- [COMPLETION_GUIDE.md](reference/COMPLETION_GUIDE.md) — вызовы LLM (completion), модели, агрегаторы
- [CONTRIBUTION_REFERENCE.md](reference/CONTRIBUTION_REFERENCE.md) — контрибьюты плагинов
- [EVENT_GUIDE.md](reference/EVENT_GUIDE.md) — события: типы, источники, атрибуты (event_*, app_chat_* и др.)
- [PLACEHOLDERS.md](reference/PLACEHOLDERS.md) — плейсхолдеры: синтаксис, модификаторы

## Разработка
- [LOGGING_GUIDE.md](development/LOGGING_GUIDE.md) — логирование (файл, уровни)
- [TESTING_GUIDE.md](development/TESTING_GUIDE.md) — тестирование (pytest, структура)
