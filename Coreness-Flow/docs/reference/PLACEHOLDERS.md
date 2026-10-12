# Плейсхолдеры

**Назначение:** Динамическая подстановка значений в параметры действий сценариев.

Обработку выполняет плагин **placeholder_processor**. В сценариях подстановка в `params` выполняется автоматически перед выполнением действия.

## Механика работы:

**Все атрибуты в `params` автоматически обрабатываются плейсхолдерами** перед выполнением действия. Это означает:

- **Все значения в `params`** — строки, числа, массивы, объекты — проходят через обработку плейсхолдеров
- **Все уровни вложенности** — плейсхолдеры работают на любом уровне структуры `params` (в строках, элементах массивов, значениях объектов)
- **Автоматическая обработка** — происходит для каждого шага сценария перед выполнением действия
- **Источник данных** — система использует накопленные данные события и результаты предыдущих действий как источник значений для подстановки

## Синтаксис плейсхолдеров:

**Простая замена:**
```yaml
params:
  text: "Привет: {event_text}"
  app_chat_id: "{app_chat_id}"
```

**С модификаторами:**
```yaml
params:
  text: "Привет, {username|fallback:Гость}!"
  price: "{amount|*0.9|format:currency}"
```

**Литеральные значения в кавычках:**
```yaml
params:
  text: "{'hello'|upper}"                      # HELLO (без передачи через словарь)
  duration: "{'1d 2w'|seconds}"                # 1296000 (литеральное время)
  calculation: "{'100'|+50}"                   # 150 (литеральная арифметика)
  date_shift: "{'2024-12-25'|shift:+1 day}"   # 2024-12-26 (литеральная дата)
  # Двойные кавычки для строк с одинарными кавычками
  text: "{"it's working"}"                     # it's working
  # Экранированные кавычки
  text: "{'it\'s working'}"                    # it's working
```

**Вложенные плейсхолдеры:**
```yaml
params:
  text: "Ответ: {status|equals:{expected}|value:OK|fallback:BAD}"
```

### ⚠️ Важно: Кавычки в YAML для плейсхолдеров с regex

**Проблема:** YAML по-разному обрабатывает escape-последовательности в одинарных и двойных кавычках, что критично для regex паттернов с обратными слешами.

**Решение:** Используйте **двойные кавычки** для regex паттернов с обратными слешами (`\s`, `\d`, `\w` и т.д.).

**Примеры:**

```yaml
# ❌ ОШИБКА - в одинарных кавычках \\s не экранируется правильно
params:
  value: '{event_text|regex:^([^\\s]+)|lower}'  # \\s становится \s (обратный слеш + s), а не пробел!

# ✅ ПРАВИЛЬНО - двойные кавычки правильно экранируют обратные слеши
params:
  value: "{event_text|regex:^([^\\s]+)|lower}"  # \\s становится \s (пробел в regex)

# ✅ ПРАВИЛЬНО - для regex без обратных слешей можно использовать одинарные кавычки
params:
  value: '{event_text|regex:item_(\d+)}'  # Работает, так как \d не требует двойного экранирования

# ✅ ПРАВИЛЬНО - для простых regex с одним обратным слешем тоже двойные кавычки
params:
  value: "{event_text|regex:\\s+([^\\s]+)$|lower}"  # \\s для пробела, \\s для пробела

# ✅ ОБЫЧНЫЕ ПЛЕЙСХОЛДЕРЫ - без разницы
params:
  text: "Привет, {username}!"     # Работает
  text: 'Привет, {username}!'    # Тоже работает
```

**Когда использовать двойные кавычки:**
- **Regex паттерны с обратными слешами** — `{field|regex:pattern}` где pattern содержит `\s`, `\d`, `\w`, `\n`, `\t` и т.д.
- **Важно:** В двойных кавычках нужно использовать двойное экранирование: `\\s` для пробела, `\\d` для цифры
- **Пример:** `"{event_text|regex:^([^\\s]+)|lower}"` — `\\s` становится `\s` (пробел в regex)

**Когда можно использовать одинарные кавычки:**
- **Regex паттерны без обратных слешей** — простые паттерны без `\s`, `\d`, `\w` и т.д.
- **Обычные плейсхолдеры** — `{username}`, `{user_id}`
- **Простые модификаторы** — `{name|upper}`, `{price|format:currency}`
- **Текстовые значения** — без специальных символов

**Правило:** Если в regex паттерне есть обратные слеши (`\s`, `\d`, `\w` и т.д.) — **всегда используйте двойные кавычки** с двойным экранированием (`\\s`, `\\d`, `\\w`).

**Доступ к вложенным данным:**
```yaml
params:
  # Точечная нотация для объектов
  text: "Пользователь: {user.profile.name|fallback:Неизвестный}"
  text: "Сообщение: {message.text}"
  
  # Индексы для массивов
  text: "Первый файл: {attachment[0].file_id}"
  text: "Последний пользователь: {users[-1].name}"
  
  # Комбинированный доступ
  text: "Событие: {event.attachment[0].type}"
  text: "Данные: {response.data.items[0].value}"
```

## Доступные данные

**Источник данных для плейсхолдеров:**

1. **Атрибуты события** — поля, пришедшие в сценарий с событием. Актуальный список по типам и источникам см. в [Справочнике по событиям](EVENT_GUIDE.md) (например для источника `app`: `event_type`, `event_source`, `event_text`, `event_timestamp`, `app_chat_id`).

2. **Системные атрибуты контекста выполнения** — дополняются движком по ходу сценария: `last_error` (объект с `code`, `message`), `last_result`, `scenario_chain`, `_cache`, `_async_action`. Подробнее см. [EVENT_GUIDE.md — Системные атрибуты контекста выполнения](EVENT_GUIDE.md#системные-атрибуты-контекста-выполнения).

3. **Данные предыдущих шагов** — результаты действий попадают в `_cache` (плоско или по `_namespace`). В плейсхолдерах доступны как `{_cache.key}`, `{_cache.namespace.field}` и т.д., либо по имени поля, если оно было сохранено в кэш без namespace.

## Доступ к вложенным элементам:

> **Универсальный доступ к данным!** Поддержка точечной нотации для объектов и индексов для массивов.

<table>
<thead>
<tr><th>Синтаксис</th><th>Описание</th><th>Пример</th><th>Результат</th></tr>
</thead>
<tbody>
<tr><td colspan="4"><strong>Объекты</strong></td></tr>
<tr><td><code>object.field</code></td><td>Доступ к полю объекта</td><td><code>{message.text}</code></td><td><code>Привет мир</code></td></tr>
<tr><td><code>object.field.subfield</code></td><td>Вложенные поля</td><td><code>{user.profile.name}</code></td><td><code>Иван Петров</code></td></tr>
<tr><td colspan="4"><strong>Массивы</strong></td></tr>
<tr><td><code>array[index]</code></td><td>Доступ к элементу массива</td><td><code>{attachment[0].file_id}</code></td><td><code>file_1</code> (первый файл)</td></tr>
<tr><td><code>array[-index]</code></td><td>Отрицательный индекс</td><td><code>{attachment[-1].file_id}</code></td><td><code>file_3</code> (последний файл)</td></tr>
<tr><td><code>array[index].field</code></td><td>Поле элемента массива</td><td><code>{users[1].name}</code></td><td><code>Боб</code> (имя второго пользователя)</td></tr>
<tr><td><code>array[index][index]</code></td><td>Вложенные массивы</td><td><code>{matrix[0][1]}</code></td><td><code>2</code> (элемент матрицы)</td></tr>
<tr><td colspan="4"><strong>Комбинированный</strong></td></tr>
<tr><td><code>object.array[index].field</code></td><td>Смешанный доступ</td><td><code>{event.attachment[0].file_id}</code></td><td><code>file_1</code></td></tr>
</tbody>
</table>

**Примеры использования:**
```yaml
params:
  # Объекты
  text: "Сообщение: {message.text}"
  text: "Пользователь: {user.profile.name|fallback:Неизвестный}"
  
  # Массивы
  text: "Первый файл: {attachment[0].file_id}"
  text: "Последний пользователь: {users[-1].name|upper}"
  text: "Файл: {attachment[0].file_id}, размер: {attachment[0].size}"
  
  # Комбинированный доступ
  text: "Событие: {event.attachment[0].type}"
  text: "Данные: {response.data.items[0].value}"
  
  # Данные из кэша предыдущих шагов
  text: "{_cache.response_completion|fallback:—}"
  
  # Безопасный доступ
  text: "{attachment[10].file_id|fallback:Файл не найден}"
```

**Обработка ошибок:**
- При обращении к несуществующему полю/индексу возвращается `None`
- Можно использовать модификатор `fallback` для значения по умолчанию
- Отрицательные индексы работают как в Python: `-1` = последний элемент
- Поддерживается неограниченная глубина вложенности

## Модификаторы:

<table>
<thead>
<tr><th>Модификатор</th><th>Описание</th><th>Пример</th><th>Результат</th></tr>
</thead>
<tbody>
<tr><td colspan="4"><strong>Арифметические операции</strong></td></tr>
<tr><td><code>+value</code></td><td>Сложение</td><td><code>{price|+100}</code></td><td><code>1500</code> (если price=1400)</td></tr>
<tr><td><code>-value</code></td><td>Вычитание</td><td><code>{price|-50}</code></td><td><code>1350</code> (если price=1400)</td></tr>
<tr><td><code>*value</code></td><td>Умножение</td><td><code>{price|*0.9}</code></td><td><code>1260</code> (если price=1400)</td></tr>
<tr><td><code>/value</code></td><td>Деление</td><td><code>{seconds|/3600}</code></td><td><code>2.5</code> (если seconds=9000)</td></tr>
<tr><td><code>%value</code></td><td>Остаток от деления</td><td><code>{number|%7}</code></td><td><code>3</code> (если number=10)</td></tr>
<tr><td colspan="4"><strong>Регистр</strong></td></tr>
<tr><td><code>upper</code></td><td>Верхний регистр</td><td><code>{name|upper}</code></td><td><code>ИВАН</code> (если name="Иван")</td></tr>
<tr><td><code>lower</code></td><td>Нижний регистр</td><td><code>{name|lower}</code></td><td><code>иван</code> (если name="Иван")</td></tr>
<tr><td><code>title</code></td><td>Заглавные буквы каждого слова</td><td><code>{name|title}</code></td><td><code>Иван Петров</code> (если name="иван петров")</td></tr>
<tr><td><code>capitalize</code></td><td>Первая заглавная буква</td><td><code>{name|capitalize}</code></td><td><code>Иван</code> (если name="иван")</td></tr>
<tr><td><code>case:type</code></td><td>Преобразование регистра</td><td><code>{name|case:upper}</code></td><td><code>ИВАН</code> (если name="Иван")</td></tr>
<tr><td colspan="4"><strong>Списки</strong></td></tr>
<tr><td><code>tags</code></td><td>Преобразование в теги</td><td><code>{users|tags}</code></td><td><code>@user1 @user2</code></td></tr>
<tr><td><code>list</code></td><td>Маркированный список</td><td><code>{items|list}</code></td><td><code>• item1\n• item2</code></td></tr>
<tr><td><code>comma</code></td><td>Через запятую</td><td><code>{items|comma}</code></td><td><code>item1, item2</code></td></tr>
<tr><td><code>expand</code></td><td>Разворачивание массива массивов на один уровень (только в массивах)</td><td><code>{keyboard|expand}</code></td><td><code>[[a, b], [c]]</code> → <code>[a, b], [c]</code> (в массиве)</td></tr>
<tr><td><code>keys</code></td><td>Извлечение ключей из объекта (словаря) в массив</td><td><code>{storage_values|keys}</code></td><td><code>["group1", "group2"]</code> (если storage_values={"group1": {...}, "group2": {...}})</td></tr>
<tr><td colspan="4"><strong>Преобразования</strong></td></tr>
<tr><td><code>code</code></td><td>Оборачивание значения в code блок</td><td><code>{field|code}</code></td><td><code>&lt;code&gt;value&lt;/code&gt;</code></td></tr>
<tr><td colspan="4"><strong>Форматирование строк</strong></td></tr>
<tr><td><code>truncate:length</code></td><td>Обрезка текста</td><td><code>{text|truncate:50}</code></td><td><code>Очень длинный текст...</code></td></tr>
<tr><td colspan="4"><strong>Операции с датами и временем</strong></td></tr>
<tr><td><code>now</code></td><td>Текущее время как Unix timestamp (число, секунды с эпохи UTC). Удобен для сортировки и JSON. Для отображения используйте модификаторы <code>format:date</code>, <code>format:time</code>, <code>format:datetime</code> и др.</td><td><code>{now}</code>, <code>{now|format:time}</code>, <code>{now|shift:-1 day|format:date}</code></td><td><code>1703512200</code> (timestamp); <code>14:30</code> с <code>format:time</code></td></tr>
<tr><td><code>shift:±интервал</code></td><td>Сдвиг даты на интервал (PostgreSQL: +1 day, -2 hours, +1 year 2 months). Поддержка всех форматов дат, включая ISO с таймзоной, корректная обработка месяцев/лет</td><td><code>{created|shift:+1 day}</code></td><td><code>2024-12-26</code> (если created="2024-12-25")</td></tr>
<tr><td><code>seconds</code></td><td>Преобразование временных строк в секунды (формат: Xw Yd Zh Km Ms)</td><td><code>{duration|seconds}</code></td><td><code>9000</code> (если duration="2h 30m")</td></tr>
<tr><td><code>to_date</code></td><td>Приведение даты к началу дня (00:00:00), возвращает ISO формат</td><td><code>{created|to_date}</code></td><td><code>2024-12-25 00:00:00</code></td></tr>
<tr><td><code>to_hour</code></td><td>Приведение даты к началу часа (минуты и секунды = 0), возвращает ISO формат</td><td><code>{created|to_hour}</code></td><td><code>2024-12-25 15:00:00</code> (если created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_minute</code></td><td>Приведение даты к началу минуты (секунды = 0), возвращает ISO формат</td><td><code>{created|to_minute}</code></td><td><code>2024-12-25 15:30:00</code> (если created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_second</code></td><td>Приведение даты к началу секунды (микросекунды = 0), возвращает ISO формат</td><td><code>{created|to_second}</code></td><td><code>2024-12-25 15:30:45</code></td></tr>
<tr><td><code>to_week</code></td><td>Приведение даты к началу недели (понедельник 00:00:00), возвращает ISO формат</td><td><code>{created|to_week}</code></td><td><code>2024-12-23 00:00:00</code> (если created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_month</code></td><td>Приведение даты к началу месяца (1 число, 00:00:00), возвращает ISO формат</td><td><code>{created|to_month}</code></td><td><code>2024-12-01 00:00:00</code> (если created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_year</code></td><td>Приведение даты к началу года (1 января, 00:00:00), возвращает ISO формат</td><td><code>{created|to_year}</code></td><td><code>2024-01-01 00:00:00</code> (если created="2024-12-25 15:30:45")</td></tr>
<tr><td colspan="4"><strong>Форматирование дат и времени</strong></td></tr>
<tr><td><code>format:timestamp</code></td><td>Преобразование в Unix timestamp</td><td><code>{date|format:timestamp}</code></td><td><code>1703512200</code></td></tr>
<tr><td><code>format:date</code></td><td>Формат даты (dd.mm.yyyy)</td><td><code>{timestamp|format:date}</code></td><td><code>25.12.2024</code></td></tr>
<tr><td><code>format:time</code></td><td>Формат времени (HH:MM)</td><td><code>{timestamp|format:time}</code></td><td><code>14:30</code></td></tr>
<tr><td><code>format:time_full</code></td><td>Формат времени с секундами (HH:MM:SS)</td><td><code>{timestamp|format:time_full}</code></td><td><code>14:30:45</code></td></tr>
<tr><td><code>format:datetime</code></td><td>Полный формат (dd.mm.yyyy HH:MM)</td><td><code>{timestamp|format:datetime}</code></td><td><code>25.12.2024 14:30</code></td></tr>
<tr><td><code>format:datetime_full</code></td><td>Полный формат с секундами (dd.mm.yyyy HH:MM:SS)</td><td><code>{timestamp|format:datetime_full}</code></td><td><code>25.12.2024 14:30:45</code></td></tr>
<tr><td><code>format:pg_date</code></td><td>Формат даты для PostgreSQL (YYYY-MM-DD)</td><td><code>{timestamp|format:pg_date}</code></td><td><code>2024-12-25</code></td></tr>
<tr><td><code>format:pg_datetime</code></td><td>Формат даты и времени для PostgreSQL (YYYY-MM-DD HH:MM:SS)</td><td><code>{timestamp|format:pg_datetime}</code></td><td><code>2024-12-25 14:30:45</code></td></tr>
<tr><td colspan="4"><strong>Форматирование чисел</strong></td></tr>
<tr><td><code>format:currency</code></td><td>Форматирование валюты</td><td><code>{amount|format:currency}</code></td><td><code>1000.00 ₽</code></td></tr>
<tr><td><code>format:percent</code></td><td>Форматирование процентов</td><td><code>{value|format:percent}</code></td><td><code>25.5%</code></td></tr>
<tr><td><code>format:number</code></td><td>Форматирование чисел</td><td><code>{value|format:number}</code></td><td><code>1234.56</code></td></tr>
<tr><td colspan="4"><strong>Условные</strong></td></tr>
<tr><td><code>equals:value</code></td><td>Проверка равенства (строковое сравнение)</td><td><code>{status|equals:active}</code></td><td><code>true</code> или <code>false</code></td></tr>
<tr><td><code>in_list:items</code></td><td>Проверка вхождения в список</td><td><code>{role|in_list:admin,moderator}</code></td><td><code>true</code> или <code>false</code></td></tr>
<tr><td><code>true</code></td><td>Проверка истинности (рекомендуется для boolean)</td><td><code>{is_active|true}</code></td><td><code>true</code> или <code>false</code></td></tr>
<tr><td><code>exists</code></td><td>Проверка существования значения (не None и не пустая строка)</td><td><code>{field|exists}</code></td><td><code>true</code> или <code>false</code></td></tr>
<tr><td><code>is_null</code></td><td>Проверка на null (None, пустая строка или строка "null")</td><td><code>{field|is_null}</code></td><td><code>true</code> или <code>false</code></td></tr>
<tr><td><code>value:result</code></td><td>Возврат значения при истинности</td><td><code>{status|equals:active|value:Активен}</code></td><td><code>Активен</code> или <code>null</code></td></tr>
<tr><td colspan="4"><strong>Служебные</strong></td></tr>
<tr><td><code>fallback:value</code></td><td>Значение по умолчанию</td><td><code>{username|fallback:Гость}</code></td><td><code>Иван</code> или <code>Гость</code></td></tr>
<tr><td><code>length</code></td><td>Подсчёт длины</td><td><code>{text|length}</code></td><td><code>15</code> (количество символов)</td></tr>
<tr><td><code>length</code></td><td>Подсчёт длины массива</td><td><code>{array|length}</code></td><td><code>3</code> (количество элементов)</td></tr>
<tr><td><code>regex:pattern</code></td><td>Извлечение по regex</td><td><code>{text|regex:(\d+)}</code></td><td><code>123</code> (первое число)</td></tr>
<tr><td colspan="4"><strong>Асинхронные действия</strong></td></tr>
<tr><td><code>ready</code></td><td>Проверка готовности async действия</td><td><code>{_async_action.ai_req_1|ready}</code></td><td><code>true</code> если завершено, <code>false</code> если выполняется</td></tr>
<tr><td><code>not_ready</code></td><td>Проверка что действие ещё выполняется</td><td><code>{_async_action.ai_req_1|not_ready}</code></td><td><code>true</code> если выполняется, <code>false</code> если готово</td></tr>
</tbody>
</table>

## Примеры использования:

```yaml
params:
  # Простые операции
  result: "{value|+100|format:currency}"
  
  # Условная логика
  status: "{user_status|equals:active|value:Активен|fallback:Неактивен}"
  
  # Цепочка модификаторов
  formatted: "{price|*0.9|format:currency|fallback:0.00 ₽}"
  
  # Извлечение по regex (для обратных слешей — двойные кавычки!)
  duration: "{event_text|regex:(\\d+)\\s*min|fallback:0}"
  
  # Точечная нотация
  name: "{user.profile.name|fallback:Неизвестный}"
  
  # Временные значения
  duration_seconds: "{duration|seconds}"
  duration_minutes: "{duration|seconds|/60}"
  duration_hours: "{duration|seconds|/3600}"
  formatted_time: "{duration|seconds|format:number}"
  
  # Сдвиг дат
  tomorrow: "{created|shift:+1 day}"
  next_month: "{created|shift:+1 month|format:date}"
  complex_shift: "{created|shift:+1 year 2 months|format:datetime}"
  
  # Приведение к началу периода
  start_of_day: "{created|to_date}"
  start_of_week: "{created|to_week}"
  formatted_month_start: "{created|to_month|format:date}"
  
  # Boolean поля (различать True/False/None)
  is_active: "{is_active|equals:True|value:✅ Включено|fallback:{is_active|equals:False|value:❌ Выключено|fallback:❓ Неизвестно}}"
  is_polling: "{is_polling|equals:True|value:✅ Активен|fallback:{is_polling|equals:False|value:❌ Неактивен|fallback:❓ Неизвестно}}"
  
  # Строковые поля (используйте equals:value)
  status: "{user_status|equals:active|value:Активен|fallback:Неактивен}"
  
  # Упрощённый вариант (если None не ожидается)
  is_simple: "{is_active|true|value:✅ Включено|fallback:❌ Выключено}"
  
  # Проверка существования значения (в условиях)
  # В условиях: {field|exists} == True или {field|exists} == False
  
  # Проверка на null (в условиях)
  # В условиях: {field|is_null} == True или {field|is_null} == False
```

**Пример использования exists в условиях:**

```yaml
step:
  - action: "validate"
    params:
      condition: "{response_value.feedback|exists} == True"
    transition:
      - action_result: "success"
        transition_action: "continue"  # Значение существует
      - action_result: "failed"
        transition_action: "jump_to_scenario"
        transition_value: "create_feedback"  # Значение не существует
```

## Важно: boolean и строковые поля

**Для boolean полей (True/False):**
- **Рекомендуется:** `{is_active|true|value:✅ Включено|fallback:❌ Выключено}`
- **Не работает:** `{is_active|equals:true|value:✅ Включено}` (сравнение строк)

**Для строковых полей:**
- **Используйте:** `{status|equals:active|value:Активен|fallback:Неактивен}`
- Модификатор `true` не подходит для строковых значений

## Практические примеры

#### **Пример 1: Ответ в чат приложения**
```yaml
step:
  - action: "send_chat_message"
    params:
      text: "Принято: {event_text}"
      app_chat_id: "{app_chat_id}"
      sender: "assistant"
```

#### **Пример 2: Обработка ошибок с fallback**
```yaml
step:
  - action: "send_chat_message"
    params:
      text: |
        Ошибка: {error_code|fallback:НЕИЗВЕСТЕН}
        Время: {event_timestamp|format:pg_datetime}
      app_chat_id: "{app_chat_id}"
      sender: "system"
```

#### **Пример 3: Математические расчёты**
```yaml
step:
  - action: "send_chat_message"
    params:
      text: "Цена: {base_price|format:currency}, скидка {discount_percent|fallback:0}%"
      app_chat_id: "{app_chat_id}"
      sender: "assistant"
```

#### **Пример 4: Извлечение данных из текста события**
```yaml
step:
  - action: "send_chat_message"
    params:
      text: |
        Номер: "{event_text|regex:order\\s*(\\d+)|fallback:—}"
        Время: "{event_text|regex:(\\d+)\\s*min|fallback:30}" мин
      app_chat_id: "{app_chat_id}"
      sender: "assistant"
```

**Модификатор `expand`** разворачивает массив массивов на один уровень при использовании в массиве (например в params действия, ожидающего список). В строке или обычном объекте значение не меняется.
