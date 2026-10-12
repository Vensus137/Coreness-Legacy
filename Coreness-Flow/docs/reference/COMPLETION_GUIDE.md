# Completion — руководство по использованию

Действие `completion` — точка входа для всех запросов к LLM. Принимает любую комбинацию компонентов и самостоятельно собирает корректный массив `messages` для API.

---

## Из чего состоит запрос

```
[system]      ← system_prompt (если задан)
[user]        ← история[0].text
[assistant]   ← история[1].text
...           ← история (N предыдущих turns)
[user]        ← <context>RAG-чанки</context>
                <tool_results>результаты функций</tool_results>
                <env>кастомный контекст сценария</env>
                <message>prompt</message>
```

Все компоненты опциональны и независимы. Минимальный запрос — только `prompt`.

| Компонент | Параметр | Роль в API |
|-----------|----------|------------|
| Системный промпт | `system_prompt` | `system` — первым |
| История чата | `messages` | `user` / `assistant` — после system |
| RAG-контекст | `chunks` | Блок `<context>` в последнем `user`, лучший чанк — последним |
| Результаты функций | `tool_results` | Блок `<tool_results>` после RAG, новый результат — последним |
| Кастомный контекст | `context` | Блок `<env>` после RAG и tool_results (дата, пользователь и т.п.) |
| Запрос пользователя | `prompt` | Блок `<message>` в конце последнего `user`-сообщения |
| Инструменты | `tools` / `tool_choice` | Передаются отдельным параметром API, не в `messages` |

---

## Системный промпт

```yaml
- action: completion
  params:
    prompt: "{{ event.text }}"
    system_prompt: "Ты полезный ассистент. Отвечай кратко и по делу."
```

Задаёт роль и поведение модели. Задаётся в сценарии — плагин ничего не добавляет от себя.

---

## История сообщений

Получить историю через `chat_get_history`, передать в `completion.messages`:

```yaml
- action: chat_get_history
  _response_key: history
  params:
    limit: 20
    max_chars: 8000

- action: completion
  params:
    prompt: "{{ event.text }}"
    messages: "{{ history }}"
```

**Маппинг ролей:** `user` → `user`, `assistant` → `assistant`, всё остальное (`auto`, `system` и др.) → `user`. Дополнительные роли включаются через `extra_roles: ["auto"]` в `chat_get_history`.

**Рекомендации:**
- Ограничивай `max_chars` (~8000–16000) чтобы не переполнить контекстное окно
- RAG-чанки из предыдущих ответов **не** хранятся в истории — это расточительство токенов; RAG инжектируется только для текущего запроса

---

## RAG-контекст

Найти чанки через `search_chunks`, передать в `completion.chunks`:

```yaml
- action: search_chunks
  _response_key: rag_chunks
  params:
    query: "{{ event.text }}"
    collection: "knowledge_base"
    top_k: 10
    max_chars: 4000

- action: completion
  params:
    prompt: "{{ event.text }}"
    chunks: "{{ rag_chunks }}"
```

Плагин оборачивает чанки в `<context>...</context>` и добавляет перед `prompt` в последнем `user`-сообщении. Это обеспечивает:
- Семантическое разделение «данных» и «вопроса»
- Низкий риск prompt injection (чанки в user-роли, не в system)
- Хорошее внимание модели (контекст непосредственно перед ответом)

---

## Кастомный контекст (context)

Параметр `context` — произвольная строка, которая подставляется в последнее user-сообщение в блоке `<env>...</env>` **после** RAG и tool_results, **перед** `<message>`. Удобно для даты, времени, пользователя, локали и других данных из хранилища или плейсхолдеров.

```yaml
- action: get_storage
  params:
    group_key: "system"
  _response_key: system

- action: completion
  params:
    prompt: "{{ event.text }}"
    context: "Текущая дата и время: {{ system.context.current_date }}"
```

В `config/storage/system.yaml` можно задать, например: `context.current_date: "{now|format:pg_datetime}"` и подставлять в сценариях.

---

## Полный пример: история + RAG + системный промпт

```yaml
- action: chat_get_history
  _response_key: history
  params:
    limit: 15
    max_chars: 6000

- action: search_chunks
  _response_key: rag_chunks
  params:
    query: "{{ event.text }}"
    collection: "knowledge_base"
    top_k: 8
    max_chars: 3000
    score_threshold: 0.65

- action: completion
  _response_key: ai_response
  params:
    prompt: "{{ event.text }}"
    system_prompt: "Ты ассистент компании. Отвечай только на основе предоставленного контекста."
    messages: "{{ history }}"
    chunks: "{{ rag_chunks }}"

- action: send_chat_message
  params:
    text: "{{ ai_response }}"
    sender: assistant
```

---

## Tool calling

Tools позволяют модели указать что нужно выполнить — по сути запрос к нашим сценариям. Это двухходовой процесс: первый запрос возвращает что вызвать, сценарии выполняются, второй запрос получает финальный ответ с результатами как контекстом.

---

### Шаблон определения инструмента

```yaml
tools:
  - type: function          # обязательно, всегда "function"
    function:
      name: get_weather     # snake_case, уникальное имя — по нему находим сценарий
      description: "Получить текущую погоду по названию города"   # ключевое поле: модель решает когда вызывать
      strict: true          # опционально: строгое следование схеме параметров
      parameters:
        type: object
        properties:
          city:
            type: string    # string | integer | number | boolean | array | object
            description: "Название города, например: Москва"
          unit:
            type: string
            enum: ["celsius", "fahrenheit"]   # допустимые значения
          days:
            type: integer
            minimum: 1
            maximum: 7
        required: ["city"]                    # обязательные параметры
        additionalProperties: false           # рекомендуется при strict: true
```

`tool_choice`: `auto` (модель решает), `required` (всегда вызвать), `none` (запрет), `{ type: function, function: { name: "имя" } }` (конкретная функция).

---

### Первый ход: модель запрашивает вызов

```yaml
- action: completion
  _response_key: routing
  params:
    prompt: "Какая погода в Москве?"
    tool_choice: auto
    tools:
      - type: function
        function:
          name: get_weather
          description: "Получить текущую погоду по названию города"
          parameters:
            type: object
            properties:
              city: { type: string, description: "Название города" }
            required: ["city"]
```

Ответ когда модель решила вызвать функцию:

```json
{
  "response_data": {
    "response_completion": "",
    "response_meta": { ... },
    "tool_calls": [
      { "name": "get_weather", "arguments": { "city": "Москва" } }
    ]
  }
}
```

Если модель выбрала ответ пользователю (response-тулз с именем на `response_`), вызовы попадают в `response_calls`; пустые массивы не возвращаются:

```json
{
  "response_data": {
    "response_completion": "",
    "response_meta": { ... },
    "response_calls": [
      { "name": "response_general", "arguments": {} }
    ]
  }
}
```

- `response_completion` пустой — модель запрашивает вызов(ы), финального текста нет
- `tool_calls` — вызовы обычных функций (имя + аргументы объектом); только если есть хотя бы один
- `response_calls` — вызовы response-тулзов (имя на `response_`); только если есть хотя бы один
- `arguments` приходит уже распарсенным объектом, в сценарии доступны как `{_cache....arguments.city}` и т.п.

---

### Второй ход: результаты как контекст

Результаты выполненных сценариев передаются через `tool_results`. Они добавляются как блок `<tool_results>` в user-сообщение — после RAG-чанков, перед `<message>`. Сортируются по `timestamp` (старый → новый), чтобы новые результаты оказывались ближе к сообщению пользователя и получали больше внимания модели.

```yaml
# Шаг 1: routing — узнаём что вызвать
- action: completion
  _response_key: routing
  params:
    prompt: "{{ event.text }}"
    tool_choice: auto
    tools: [...]

# Шаг 2: в сценарии по routing: если есть response_calls — переход к ответу пользователю; иначе по routing.tool_calls выполняем сценарии
- action: get_weather
  _response_key: weather
  params:
    city: "Москва"

# Шаг 3: финальный completion с результатами как контекстом
- action: completion
  _response_key: answer
  params:
    prompt: "{{ event.text }}"
    tool_results:
      - name: get_weather
        content: "{{ weather }}"
        timestamp: 1735689600
```

Итоговый user-message который видит модель в финальном запросе:

```
<tool_results>
[get_weather]
Москва, +18°C, ясно
</tool_results>

<message>
Какая погода в Москве?
</message>
```

Если используются и RAG-чанки, и tool_results:

```
<context>
[1] менее релевантный чанк
[2] более релевантный чанк  ← лучший последним = ближе к промпту
</context>

<tool_results>
[older_function]
результат старого вызова
[newer_function]
результат нового вызова  ← новый последним = ближе к сообщению
</tool_results>

<env>
Дата: 2026-02-24
Пользователь: ...
(любой кастомный контекст сценария)  ← опционально
</env>

<message>
{prompt}
</message>
```

`system_prompt`, `messages` (история) и `chunks` (RAG) совместимы со вторым ходом и добавляются в начало по стандартной схеме.

---

## Метаинформация в ответе

Все запросы возвращают объект `response_meta` внутри `response_data`:

```json
{
  "response_data": {
    "response_completion": "Текст ответа",
    "response_meta": {
      "model": "google/gemini-2.5-flash",
      "prompt_tokens": 1240,
      "completion_tokens": 87,
      "total_tokens": 1327
    }
  }
}
```

`response_meta` передаётся в `send_chat_message` вместе с ответом и хранится в сообщении — затем отображается в UI (тултип с моделью и токенами).

---

## JSON-режим

```yaml
- action: completion
  _response_key: parsed
  params:
    prompt: "Извлеки имя и возраст из текста: Иван, 32 года"
    json_mode: json_object
```

При `json_mode: json_schema` нужно передать схему:

```yaml
- action: completion
  _response_key: parsed
  params:
    prompt: "Извлеки имя и возраст из текста: Иван, 32 года"
    json_mode: json_schema
    json_schema:
      name: person_schema
      strict: true
      schema:
        type: object
        properties:
          name: { type: string }
          age: { type: integer }
        required: [name, age]
```

Результат доступен в `response_dict` (распарсенный объект).
