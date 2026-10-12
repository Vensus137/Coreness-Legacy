---
title: Гайд по действиям
description: Полный справочник всех доступных действий в Coreness Flow. AI, сценарии, БД, векторное хранилище и др.
keywords: действия coreness flow, completion, scenario, database, vector_store, AI
---

# 🎯 Гайд по действиям

Полное описание всех доступных действий с их параметрами и результатами.

## ⚙️ Общие параметры действий

При вызове действий в сценариях доступны дополнительные параметры (при необходимости):

- **`_namespace`** (`string`, опционально) — кастомный ключ для вложенности в `_cache`. Если указан, данные сохраняются в `_cache[_namespace]` вместо плоского кэша. Доступ через `{_cache._namespace.field}`.

- **`_response_key`** (`string`, опционально) — кастомное имя для основного поля результата (помечено 🔀). Основное поле сохраняется в `_cache` под указанным именем. Доступ через `{_cache.{_response_key}}`. Только для действий с переименуемым полем результата.

---

## 📋 Содержание

- [ai_service](#ai_service) (4 действий)
  - [completion](#completion)
  - [get_aggregators](#get_aggregators)
  - [get_models](#get_models)
  - [validate_token](#validate_token)
- [chats](#chats) (14 действий)
  - [chat_claim_message](#chat_claim_message)
  - [chat_create](#chat_create)
  - [chat_delete](#chat_delete)
  - [chat_get_history](#chat_get_history)
  - [chat_get_message](#chat_get_message)
  - [chat_get_messages](#chat_get_messages)
  - [chat_list](#chat_list)
  - [chat_mark_message_drawn](#chat_mark_message_drawn)
  - [chat_set_pinned](#chat_set_pinned)
  - [chat_set_title](#chat_set_title)
  - [chat_submit_message](#chat_submit_message)
  - [clear_chat](#clear_chat)
  - [remove_chat_message](#remove_chat_message)
  - [send_chat_message](#send_chat_message)
- [condition_parser](#condition_parser) (5 действий)
  - [add_to_tree](#add_to_tree)
  - [build_condition](#build_condition)
  - [check_match](#check_match)
  - [parse_condition](#parse_condition)
  - [search_in_tree](#search_in_tree)
- [database](#database) (4 действий)
  - [delete_storage](#delete_storage)
  - [get_storage](#get_storage)
  - [set_storage](#set_storage)
  - [sync_storage](#sync_storage)
- [download_service](#download_service) (1 действий)
  - [download_and_extract](#download_and_extract)
- [placeholder_processor](#placeholder_processor) (3 действий)
  - [process_placeholders](#process_placeholders)
  - [process_placeholders_full](#process_placeholders_full)
  - [process_text_placeholders](#process_text_placeholders)
- [scenario_processor](#scenario_processor) (6 действий)
  - [delete_cache](#delete_cache)
  - [execute_scenario](#execute_scenario)
  - [process_scenario_event](#process_scenario_event)
  - [set_cache](#set_cache)
  - [sync_scenarios](#sync_scenarios)
  - [wait_for_action](#wait_for_action)
- [validator](#validator) (1 действий)
  - [validate](#validate)
- [vector_store](#vector_store) (4 действий)
  - [add_chunks](#add_chunks)
  - [delete_chunks](#delete_chunks)
  - [list_chunks](#list_chunks)
  - [search_chunks](#search_chunks)

<a id="ai_service"></a>
## ai_service

**Описание:** Сервис запросов к LLM

<a id="completion"></a>
### completion

**Описание:** Комплишн через агрегатор (chat completions). Поддерживает историю сообщений, RAG-контекст и tool calling.

**Входные параметры:**

- **`prompt`** (`string`) — Текст запроса пользователя (текущее сообщение)
- **`system_prompt`** (`string`, опционально) — Системный промпт (инструкции и роль ассистента). Добавляется первым сообщением с role=system.
- **`context`** (`string`, опционально) — Кастомный контекст сценария (например текущая дата). Добавляется в user-сообщение после RAG и tool_results, непосредственно перед prompt.
- **`messages`** (`array (of object)`, опционально) — История сообщений чата. Каждый объект: { sender, text } или { role, content }. sender: user→user, assistant→assistant, system/auto→user. Добавляется между system_prompt и итоговым user-сообщением.
  - **`sender`** (`string`) — Отправитель: user, assistant, system, auto
  - **`text`** (`string`) — Текст сообщения
- **`chunks`** (`array (of object)`, опционально) — RAG-чанки из search_chunks. Оборачиваются в <context>...</context> и добавляются в итоговое user-сообщение перед prompt.
  - **`text`** (`string`) — Текст чанка
- **`model`** (`string`, опционально) — Модель (по умолчанию из активного профиля)
- **`max_tokens`** (`integer`, опционально) — Максимум токенов ответа
- **`temperature`** (`float`, опционально) — Температура генерации
- **`json_mode`** (`string`, опционально, значения: [`json_object`, `json_schema`]) — Режим JSON: json_object или json_schema
- **`json_schema`** (`object`, опционально) — JSON-схема при json_mode=json_schema
- **`tools`** (`array`, опционально) — Определения инструментов (первый ход). Формат OpenAI: [{ type: 'function', function: { name, description, parameters } }].
- **`tool_choice`** (`string`, опционально) — Выбор инструмента: none | auto | required | { type: 'function', function: { name } }
- **`tool_results`** (`array (of object)`, опционально) — Результаты выполнения сценариев-функций. Добавляются как блок <tool_results> в user-сообщение после RAG-чанков. Сортируются по timestamp (старый→новый), новые оказываются ближе к prompt = в фокусе модели.
  - **`name`** (`string`) — Имя функции/сценария — используется как метка блока в контексте
  - **`content`** (`string`) — Результат (строка или JSON-строка для сложных данных)
  - **`timestamp`** (`number`) (опционально) — Unix timestamp начала выполнения для сортировки. Без него — сохраняется порядок массива.

**Выходные параметры:**

- **`result`** (`string`) — success или error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`response_completion`** (`string`) — Текст ответа модели
  - **`response_meta`** (`object`) — Метаинформация об ответе — модель, токены. Передаётся в send_chat_message для хранения в сообщении и отображения в UI.
    - **`model`** (`string`) — Использованная модель
    - **`prompt_tokens`** (`integer`) — Токены на вход
    - **`completion_tokens`** (`integer`) — Токены ответа
    - **`total_tokens`** (`integer`) — Всего токенов
  - **`response_dict`** (`object`) (опционально) — Распарсенный JSON при json_mode
  - **`tool_calls`** (`array (of object)`) (опционально) — Вызовы обычных функций. Отсутствует, если вызовов нет.
    - **`name`** (`string`) — Имя функции (snake_case)
    - **`arguments`** (`object`) — Параметры вызова, уже распарсенный объект
  - **`response_calls`** (`array (of object)`) (опционально) — Вызовы response-тулзов (имя начинается с response_). Отсутствует, если вызовов нет.
    - **`name`** (`string`) — Имя response-тулза
    - **`arguments`** (`object`) — Параметры вызова, уже распарсенный объект


<a id="get_aggregators"></a>
### get_aggregators

**Описание:** Получить список доступных агрегаторов из конфига плагина

**Входные параметры:**


**Выходные параметры:**

- **`result`** (`string`) — 
- **`response_data`** (`object`) — 
  - **`aggregators`** (`array`) — Список конфигов агрегаторов


<a id="get_models"></a>
### get_models

**Описание:** Получить список доступных моделей агрегатора

**Входные параметры:**

- **`base_url`** (`string`) — URL агрегатора (нормализуется автоматически)
- **`api_key`** (`string`, опционально) — API-ключ агрегатора (опционально — некоторые эндпоинты публичны)

**Выходные параметры:**

- **`result`** (`string`) — success или error
- **`response_data`** (`object`) — 
  - **`models`** (`array`) — Список ID доступных моделей


<a id="validate_token"></a>
### validate_token

**Описание:** Проверить валидность API-ключа (запрос списка моделей)

**Входные параметры:**

- **`base_url`** (`string`) — URL агрегатора
- **`api_key`** (`string`) — API-ключ для проверки

**Выходные параметры:**

- **`result`** (`string`) — success или error
- **`response_data`** (`object`) — 
  - **`models_count`** (`integer`) — Количество доступных моделей


<a id="chats"></a>
## chats

**Описание:** Чаты: список, создание, история, сообщения, переименование, удаление; запись в storage и emit в UI (send_chat_message, clear_chat).

<a id="chat_claim_message"></a>
### chat_claim_message

**Описание:** Пометить сообщение как не новое и вернуть данные (один запрос для отображения по событию).

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)
- **`message_index`** (`integer`) — Индекс сообщения в чате

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`message`** (`object`) — { text, sender, timestamp, message_index, is_new }


<a id="chat_create"></a>
### chat_create

**Описание:** Создать чат. Опционально title; id выдаёт бэкенд (от 10)

**Входные параметры:**

- **`title`** (`string`, опционально) — Название чата

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`id`** (`integer`) — ID чата
  - **`title`** (`string`) — Название чата
  - **`created_at`** (`string`) — ISO 8601


<a id="chat_delete"></a>
### chat_delete

**Описание:** Удалить чат безвозвратно. Только пользовательские (id >= 10)

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="chat_get_history"></a>
### chat_get_history

**Описание:** Последние N сообщений чата с опциональной фильтрацией и обрезкой по символам. Удобно для передачи истории в completion.

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата (по умолчанию 0)
- **`limit`** (`integer`, опционально) — Максимум сообщений (по умолчанию 20)
- **`from_index`** (`integer`, опционально) — Вернуть сообщения с индексом ≤ указанному (по умолчанию — с самого нового)
- **`offset`** (`integer`, опционально) — Сдвиг от самого нового сообщения: 0 = включая текущее, 1 = без него (чтобы не дублировать промпт в истории). По умолчанию 0.
- **`max_chars`** (`integer`, опционально) — Ограничение суммарного объёма текста сообщений в символах. Сообщения берутся с самых новых, останавливаясь при превышении лимита.
- **`extra_roles`** (`array (of string)`, опционально) — Дополнительные роли (sender) для включения помимо user и assistant. Например: ["auto"] или ["auto", "system"]. По умолчанию только user и assistant.

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`messages`** (`array (of object)`) — Список сообщений (от старых к новым). Каждый объект: { text, sender, timestamp, message_index }
    - **`text`** (`string`) — Текст сообщения
    - **`sender`** (`string`) — Отправитель: user, assistant, auto, system
    - **`timestamp`** (`string`) — ISO 8601 время создания
    - **`message_index`** (`integer`) — Индекс сообщения в чате


<a id="chat_get_message"></a>
### chat_get_message

**Описание:** Одно сообщение чата по message_index (по событию — запрос конкретного сообщения).

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)
- **`message_index`** (`integer`) — Индекс сообщения в чате

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`message`** (`object`) — { text, sender, timestamp, message_index }


<a id="chat_get_messages"></a>
### chat_get_messages

**Описание:** Все сообщения чата (от старых к новым). Для одного нового — chat_get_message.

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`messages`** (`array`) — Массив { text, sender, timestamp, message_index }, от старых к новым


<a id="chat_list"></a>
### chat_list

**Описание:** Список чатов: id, title, created_at, отсортировано по дате создания (новые сверху)

**Входные параметры:**


**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`chats`** (`array`) — Массив { id, title, created_at, pinned }


<a id="chat_mark_message_drawn"></a>
### chat_mark_message_drawn

**Описание:** Пометить сообщение как отрисованное (is_new=False). Вызывать перед анимацией.

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)
- **`message_index`** (`integer`) — Индекс сообщения в чате

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="chat_set_pinned"></a>
### chat_set_pinned

**Описание:** Закрепить или открепить чат. Только пользовательские (id >= 10).

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)
- **`pinned`** (`boolean`, опционально) — true — закрепить, false — открепить

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="chat_set_title"></a>
### chat_set_title

**Описание:** Переименовать чат

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)
- **`title`** (`string`) — Название чата

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="chat_submit_message"></a>
### chat_submit_message

**Описание:** Отправка сообщения пользователя: сохранить в чат (storage), затем передать событие в сценарии. Вызывается с фронта при отправке сообщения. В payload события к сценарию добавляется app_message_index.

**Входные параметры:**

- **`event_type`** (`string`) — Тип события (message для UI чата)
- **`event_text`** (`string`) — Текст сообщения пользователя
- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)
- **`event_timestamp`** (`number`, опционально) — Метка времени события (Unix timestamp)
- **`event_source`** (`string`, опционально) — Источник события

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="clear_chat"></a>
### clear_chat

**Описание:** Очистить историю чата в UI (emit с app_chat_id)

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (app)

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="remove_chat_message"></a>
### remove_chat_message

**Описание:** Удалить одно сообщение из чата (storage и UI).

**Входные параметры:**

- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (по умолчанию 0)
- **`message_index`** (`integer`) — Индекс удаляемого сообщения

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="send_chat_message"></a>
### send_chat_message

**Описание:** Записать или заменить сообщение в чате и отобразить в UI. Если передан message_index и сообщение есть — заменяется (chat:message_changed), иначе добавляется новое (chat:new_message). Всегда возвращает message_index.

**Входные параметры:**

- **`text`** (`string`, опционально) — Текст сообщения. Обязателен при добавлении нового; при замене опционален (частичное обновление).
- **`sender`** (`string`, опционально) — Отправитель: user, assistant, auto, system
- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (по умолчанию 0)
- **`message_index`** (`integer`, опционально) — Индекс сообщения для замены. Если указан и сообщение есть — заменяется, иначе добавляется новое.
- **`meta`** (`object`, опционально) — Метаданные сообщения — отображаются в тултипе иконки инфо (модель, токены и т.п.). Не для эффектов.
- **`effect`** (`object`, опционально) — Эффект на фронте. При замене: указан — применить; не указан — предыдущий эффект снимается. См. блок «Дополнительная информация».
- **`transition_effect`** (`string`, опционально) — Эффект перехода при замене (только при указанном message_index).

**Выходные параметры:**

- **`result`** (`string`) — success | error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`message_index`** (`integer`) — Индекс сообщения в чате (при замене — тот же, при добавлении — новый)

<details>
<summary>📖 Дополнительная информация</summary>

#### Замена по индексу

При указании **message_index**: если сообщение с таким индексом есть — обновляется (текст, sender, meta, effect), UI получает chat:message_changed; если сообщение удалено или отсутствует — добавляется новое. При добавлении нового текст обязателен.

#### Эффекты (effect)

Передаётся объект. Поддерживаемые типы:

- **loading** — индикатор загрузки (шиммер, текст «Идёт обработка…»).
  - Поля: `type` (строка, обязательно `"loading"`), `duration_sec` (число, опционально) — длительность анимации в секундах; на фронте по умолчанию 30. Бэкенд по истечении времени ничего не делает, таймер только для анимации.
  - Пример: `{ "type": "loading", "duration_sec": 60 }`

При **замене** (message_index указан): если effect не передан — предыдущий эффект снимается; если передан объект — применяется.

#### Эффект перехода (transition_effect)

Только при замене (указан message_index). Строка; в сообщение не записывается. Значение **replace** (по умолчанию) — плавная замена текста/блока на фронте.

</details>


<a id="condition_parser"></a>
## condition_parser

**Описание:** Универсальный парсер условий с компиляцией в функции и search tree для быстрого поиска

<a id="add_to_tree"></a>
### add_to_tree

**Описание:** Добавление элемента в search tree с условиями в листьях

**Входные параметры:**

- **`search_tree`** (`object`) — Search tree для добавления элемента
- **`parsed_condition`** (`object`) — Распарсенное условие (результат parse_condition)
- **`item_name`** (`string`) — Название поля для сохранения значения в листе (например: 'scenario_id')
- **`item_value`** (`any`) — Значение для сохранения в листе

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`added`** (`boolean`) — True если элемент добавлен, False если это дубликат


<a id="build_condition"></a>
### build_condition

**Описание:** Построение условия из массива конфигов с простыми полями и custom условиями

**Входные параметры:**

- **`configs`** (`array (of object)`) — Массив конфигураций триггеров (каждый элемент - объект с полями и опциональным 'condition')

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`condition_string`** (`string`) — Построенная строка условия (пустая строка если configs пустой)


<a id="check_match"></a>
### check_match

**Описание:** Проверка соответствия данных условию

**Входные параметры:**

- **`condition`** (`string|object`) — Условие: строка для парсинга или объект (результат parse_condition)
- **`data`** (`object`) — Данные для проверки соответствия условию

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`matched`** (`boolean`) — True если данные соответствуют условию, False если нет


<a id="parse_condition"></a>
### parse_condition

**Описание:** Парсинг условия в compiled function + search tree

**Входные параметры:**

- **`condition`** (`string`, обязательное, мин. длина: 1) — Строка условия для парсинга (например: $event_type == 'message' and $user_id > 100)

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки (VALIDATION_ERROR, SYNTAX_ERROR, INTERNAL_ERROR)
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`search_path`** (`object`) — Путь для поиска в search tree (только == условия для плоских полей)
  - **`compiled_function`** (`object`) — Скомпилированная функция для проверки условия
  - **`condition_hash`** (`integer`) — Хэш условия для сравнения дубликатов


<a id="search_in_tree"></a>
### search_in_tree

**Описание:** Быстрый поиск значений в search tree по данным события — O(m) где m - глубина дерева

**Входные параметры:**

- **`search_tree`** (`object`) — Search tree для поиска
- **`data`** (`object`) — Данные события для поиска в дереве

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`found_values`** (`array`) — Массив найденных значений из листьев дерева


<a id="database"></a>
## database

**Описание:** Работа с SQLite: таблица storage (group_key + key -> value), возможность расширения другими таблицами

<a id="delete_storage"></a>
### delete_storage

**Описание:** Удалить значение или всю группу из таблицы storage

**Входные параметры:**

- **`group_key`** (`string`) — Ключ группы (обязательно)
- **`key`** (`string`, опционально) — Ключ значения (если не указан — удаляется вся группа)

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`deleted_count`** (`integer`) — Количество удалённых записей (0 если нечего было удалять)


<a id="get_storage"></a>
### get_storage

**Описание:** Получить значение, группу или данные по паттернам из таблицы storage. Точные group_key/key имеют приоритет над паттернами

**Входные параметры:**

- **`group_key`** (`string`, опционально) — Ключ группы (точное совпадение, приоритет над group_key_pattern)
- **`group_key_pattern`** (`string`, опционально) — Паттерн LIKE для группы (%, _). Используется, если group_key не указан
- **`key`** (`string`, опционально) — Ключ значения (точное совпадение, приоритет над key_pattern). Вместе с group_key — одно значение
- **`key_pattern`** (`string`, опционально) — Паттерн LIKE для ключа (%, _). Используется, если key не указан (в рамках группы или при поиске)

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`storage_values`** (`any`) — Одно значение, группа {key: value} или все группы {group_key: {key: value}}. При отсутствии записи — None
  - **`storage_processed_at`** (`any`) — Дата последнего изменения записи (ISO 8601). Та же структура, что и storage_values, но значения — строки дат или null


<a id="set_storage"></a>
### set_storage

**Описание:** Записать значение или группу в таблицу storage

**Входные параметры:**

- **`group_key`** (`string`, опционально) — Ключ группы (для одной записи или группы)
- **`key`** (`string`, опционально) — Ключ значения (вместе с group_key и value — одна запись)
- **`value`** (`any`, опционально) — Значение (вместе с group_key и key)
- **`values`** (`object`, опционально) — Группа {key: value} при указанном group_key или полная структура {group_key: {key: value}}

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`storage_values`** (`any`) — Записанные данные (одно значение, группа или полная структура)
  - **`storage_processed_at`** (`any`) — Дата последнего изменения (ISO 8601). Та же структура, что и storage_values


<a id="sync_storage"></a>
### sync_storage

**Описание:** Синхронизация storage из YAML (папка storage_config_dir): удалить группы из конфига в БД и загрузить данные из файлов

**Входные параметры:**

- **`type`** — object
- **`optional`** — True
- **`description`** — Параметры не требуются; вызов без payload — полная синхронизация

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`synced_groups`** (`integer`) — Количество синхронизированных групп (0 если папка пуста или отсутствует)


<a id="download_service"></a>
## download_service

**Описание:** Сервис загрузки файлов по URL и извлечения текста (PDF, DOCX, TXT, MD, HTML, CSV)

<a id="download_and_extract"></a>
### download_and_extract

**Описание:** Загрузить файл по URL и извлечь текст. Автоопределение типа по magic bytes, Content-Type или расширению

**Входные параметры:**

- **`url`** (`string`) — URL для загрузки (прямая ссылка, Google Drive, Google Docs/Sheets и т.д.)
- **`file_type`** (`string`, опционально, значения: [`pdf`, `docx`, `txt`, `md`, `html`, `csv`]) — Подсказка типа файла; если не указан — автоопределение
- **`keep_file`** (`boolean`, опционально) — Сохранить файл после извлечения (по умолчанию удаляется)
- **`max_file_size_mb`** (`integer`, опционально, диапазон: 1-500) — Макс. размер в МБ для этого вызова (переопределяет настройку)
- **`download_timeout_seconds`** (`integer`, опционально, диапазон: 10-3600) — Таймаут загрузки в секундах для этого вызова

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) (опционально) — 
  - **`code`** (`string`) — VALIDATION_ERROR, FILE_TOO_LARGE, DOWNLOAD_FAILED, UNSUPPORTED_FORMAT, EXTRACTION_FAILED, TIMEOUT, INTERNAL_ERROR
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`file_text`** (`string`) — Извлечённый текст
  - **`file_path`** (`string`) (опционально) — Путь к файлу (если keep_file=true)
  - **`file_metadata`** (`object`) — Метаданные (source_url, file_type, file_size_bytes, download_timestamp и др.)


<a id="placeholder_processor"></a>
## placeholder_processor

**Описание:** Процессор плейсхолдеров: модификаторы, вложенные поля, литералы, expand; API Bus async

<a id="process_placeholders"></a>
### process_placeholders

**Описание:** Обработка плейсхолдеров в структуре (dict/list/str)

**Входные параметры:**

- **`data`** (`object`) — Данные с плейсхолдерами (dict, list или str)
- **`values`** (`object`) — Словарь значений для подстановки
- **`max_depth`** (`integer`, опционально) — Максимальная глубина вложенности (по умолчанию из настройки)

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`data`** (`object`) — Данные с подставленными значениями


<a id="process_placeholders_full"></a>
### process_placeholders_full

**Описание:** Обработка плейсхолдеров в структуре с сохранением всех полей (полный объект)

**Входные параметры:**

- **`data`** (`object`) — Данные с плейсхолдерами
- **`values`** (`object`) — Словарь значений для подстановки
- **`max_depth`** (`integer`, опционально) — Максимальная глубина вложенности

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`data`** (`object`) — Полный объект с подставленными значениями


<a id="process_text_placeholders"></a>
### process_text_placeholders

**Описание:** Обработка плейсхолдеров в строке

**Входные параметры:**

- **`text`** (`string`) — Строка с плейсхолдерами {key}
- **`values`** (`object`) — Словарь значений для подстановки
- **`max_depth`** (`integer`, опционально) — Максимальная глубина вложенности (по умолчанию из настройки)

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`text`** (`string`) — Строка с подставленными значениями


<a id="scenario_processor"></a>
## scenario_processor

**Описание:** Движок обработки сценариев: триггеры, шаги, переходы, scheduled-сценарии

<a id="delete_cache"></a>
### delete_cache

**Описание:** Удаление неймспейса или вложенного пути из _cache сценария для очистки контекста

**Входные параметры:**

- **`namespace`** (`string`) — Путь в _cache для удаления. Вложенность через точку (например tools или tools.ai_agent). Если указано _cache.tools — префикс _cache. игнорируется, удаление всегда только из кэша

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — 
  - **`message`** (`string`) — 


<a id="execute_scenario"></a>
### execute_scenario

**Описание:** Выполнение сценария или массива сценариев по имени

**Входные параметры:**

- **`scenario`** (`string|array`) — Название сценария (строка) или массив названий сценариев
- **`return_cache`** (`boolean`, опционально) — Возвращать ли _cache из выполненного сценария (по умолчанию true). Работает только для одиночных сценариев

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`scenario_result`** (`string`) — Результат выполнения сценария: success, error, abort, break


<a id="process_scenario_event"></a>
### process_scenario_event

**Описание:** Обработка события по сценариям (поиск и выполнение подходящих сценариев)

**Входные параметры:**

- **`event_type`** (`string`, обязательное, мин. длина: 1) — Тип события для поиска сценариев
- **`event_text`** (`string`, опционально) — Текст события (например текст сообщения чата); имя не конфликтует с полями шагов сценария при мерже во flat
- **`app_chat_id`** (`integer`, опционально) — ID чата приложения (event_source: app)
- **`event_timestamp`** (`number`, опционально) — Метка времени события: Unix timestamp (секунды от эпохи UTC, целое или float). Для отображения форматируют локально
- **`_any`** (`any`, опционально) — Допускаются любые другие поля в payload; рекомендуется плоская структура (flat) для плейсхолдеров и мержа в шагах сценария

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке


<a id="set_cache"></a>
### set_cache

**Описание:** Запись данных в _cache сценария (с учётом _namespace). Данные из params.cache мержатся в _cache

**Входные параметры:**

- **`cache`** (`object`, опционально) — Данные для записи в _cache (объект). При _namespace сохраняются в _cache[_namespace]

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — 
  - **`message`** (`string`) — 
- **`response_data`** (`object`) — Данные для мержа в _cache


<a id="sync_scenarios"></a>
### sync_scenarios

**Описание:** Синхронизация сценариев: загрузка из YAML + обновление кэша

**Входные параметры:**

- **`force_reload`** (`boolean`, опционально) — Принудительная перезагрузка всех сценариев (по умолчанию false)

**Выходные параметры:**

- **`result`** (`string`) — success / error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - **`loaded_count`** (`integer`) — Количество загруженных сценариев


<a id="wait_for_action"></a>
### wait_for_action

**Описание:** Ожидание завершения асинхронного действия по action_id

**Входные параметры:**

- **`action_id`** (`string`, обязательное, мин. длина: 1) — Уникальный ID асинхронного действия для ожидания
- **`timeout`** (`number`, опционально, мин: 0.0) — Таймаут ожидания в секундах (опционально)

**Выходные параметры:**

- **`result`** (`string`) — Результат основного действия или ошибка ожидания (timeout/error)
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — Данные ответа от основного действия (если успешно)


<a id="validator"></a>
## validator

**Описание:** Сервис валидации условий в сценариях (через condition_parser)

<a id="validate"></a>
### validate

**Описание:** Валидация условия по данным контекста; результат success / failed / error

**Входные параметры:**

- **`condition`** (`string`, обязательное, мин. длина: 1) — Условие для проверки (операторы condition_parser: ==, !=, >, <, in, is_null и др.)

**Выходные параметры:**

- **`result`** (`string`) — success — условие выполнено, failed — не выполнено, error — ошибка проверки
- **`error`** (`object`) (опционально) — 
  - **`code`** (`string`) — Код ошибки (VALIDATION_ERROR, INTERNAL_ERROR)
  - **`message`** (`string`) — Сообщение об ошибке


<a id="vector_store"></a>
## vector_store

**Описание:** Локальный RAG с BGE-M3 ONNX INT8 и Qdrant: индексация и семантический поиск с гибридным поиском (dense + learned sparse + RRF)

<a id="add_chunks"></a>
### add_chunks

**Описание:** Добавление текста с автоматическим разбиением на чанки и генерацией эмбеддингов

**Входные параметры:**

- **`text`** (`string`) — Текст для индексации (будет очищен и разбит на чанки)
- **`collection`** (`string`, опционально) — Имя коллекции Qdrant. Если не указано — используется коллекция по умолчанию из настроек. Коллекция создаётся автоматически при первом обращении.
- **`document_id`** (`string`, опционально) — Уникальный ID документа (если не указан, генерируется автоматически из хеша текста)
- **`metadata`** (`object`, опционально) — Метаданные для всех чанков документа (chat_id, timestamp, role, type и др.)
- **`chunk_size`** (`integer`, опционально, диапазон: 100-2048) — Размер чанка в токенах (по умолчанию из настроек: 512)
- **`chunk_overlap`** (`integer`, опционально, диапазон: 0-512) — Перекрытие между чанками в токенах (по умолчанию из настроек: 100)
- **`min_chunk_size`** (`integer`, опционально, диапазон: 10-512) — Минимальный размер чанка в токенах (по умолчанию из настроек: 50)
- **`replace_document`** (`boolean`, опционально) — Если true, перед добавлением чанков удаляются существующие чанки документа с данным document_id (по умолчанию false)

**Выходные параметры:**

- **`result`** (`string`) — success или error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`document_id`** (`string`) — ID документа (переданный или сгенерированный)
  - **`chunks_count`** (`integer`) — Количество созданных чанков
  - **`total_tokens`** (`integer`) — Общее количество токенов во всех чанках


<a id="delete_chunks"></a>
### delete_chunks

**Описание:** Удаление чанков по document_id или по фильтрам метаданных

**Входные параметры:**

- **`collection`** (`string | array`, опционально) — Имя коллекции или массив имён. Если не указано — используется коллекция по умолчанию из настроек. Массив — удаление выполняется в каждой из перечисленных коллекций.
- **`document_ids`** (`array (of string)`, опционально) — Список ID документов для удаления (удаляет все чанки этих документов)
- **`filters`** (`object`, опционально) — Фильтры по метаданным для удаления (например: {"chat_id": "old_chat"})

**Выходные параметры:**

- **`result`** (`string`) — success или error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`deleted_count`** (`integer`) — Количество удалённых документов/чанков


<a id="list_chunks"></a>
### list_chunks

**Описание:** Список чанков в коллекции (постранично) для просмотра и управления

**Входные параметры:**

- **`collection`** (`string | array`, опционально) — Имя коллекции или массив имён. Если не указано — возвращаются чанки из всех коллекций (каждая точка содержит поле collection). Пагинация работает только при указании одной коллекции.
- **`limit`** (`integer`, опционально) — Максимум записей на странице (для мультиколлекционного режима — на каждую коллекцию)
- **`offset`** (`string`, опционально) — Курсор следующей страницы (из предыдущего ответа)

**Выходные параметры:**

- **`result`** (`string`) — success или error
- **`error`** (`object`) — 
  - **`code`** (`string`) — 
  - **`message`** (`string`) — 
- **`response_data`** (`object`) — 
  - **`info`** (`object`) — Информация о коллекции (points_count и др.)
  - **`points`** (`array`) — Список точек (point_id, payload с text, original_id, document_id)
  - **`next_offset`** (`string`) — Курсор для следующей страницы или null


<a id="search_chunks"></a>
### search_chunks

**Описание:** Семантический поиск чанков с гибридным поиском (dense + sparse + RRF)

**Входные параметры:**

- **`query`** (`string`) — Поисковый запрос (текст для семантического поиска)
- **`collection`** (`string | array`, опционально) — Имя коллекции или массив имён для поиска. Если не указано — сквозной поиск по всем коллекциям (результаты объединяются и пересортируются по score).
- **`top_k`** (`integer`, опционально, диапазон: 1-100) — Максимальное количество результатов (по умолчанию из настроек: 10)
- **`score_threshold`** (`number`, опционально, диапазон: 0.0-1.0) — Минимальный порог релевантности для фильтрации (по умолчанию из настроек: 0.7)
- **`filters`** (`object`, опционально) — Фильтры по метаданным (например: {"chat_id": "main", "type": "message"})
- **`max_chars`** (`integer`, опционально) — Ограничение суммарного объёма текста чанков в символах. Чанки берутся по убыванию релевантности до достижения лимита. Позволяет запросить большой top_k и гибко резать по объёму, а не только по количеству.

**Выходные параметры:**

- **`result`** (`string`) — success или error
- **`error`** (`object`) — 
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — 
  - 🔀 **`search_chunks`** (`array (of object)`) — Список найденных чанков (отсортированы по релевантности)
    - **`chunk_id`** (`string`) — ID чанка (document_id + индекс)
    - **`document_id`** (`string`) — ID документа
    - **`chunk_index`** (`integer`) — Индекс чанка в документе (начиная с 0)
    - **`text`** (`string`) — Текст чанка
    - **`score`** (`number`) — Релевантность (0-1, выше = лучше, гибридный score после RRF)
    - **`metadata`** (`object`) — Метаданные чанка
    - **`collection`** (`string`) — Имя коллекции (присутствует при сквозном поиске по всем коллекциям)
  - **`chunks_count`** (`integer`) — Количество найденных чанков

