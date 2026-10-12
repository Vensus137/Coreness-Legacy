# Тестирование

Краткий гайд: где тесты, как запускать, как писать.

## Где что лежит

- **Корень:** `tests/conftest.py` — базовые фикстуры (`event_loop`, `project_root`); `tests/utils.py` — утилиты.
- **Плагины:** тесты рядом с кодом — `plugins/core/<plugin>/tests/`, свой `conftest.py` в каждой такой папке (моки, фикстуры плагина, хелперы вроде `check_match`, `process_text`). Плагинные тесты не опираются на корневой `conftest` — всё своё в локальном.

## Запуск

Из корня проекта:

```bash
pip install -r requirements.txt && pip install -r tests/requirements.txt
pytest
pytest plugins/core/condition_parser/tests/   # один плагин
pytest path/to/test_file.py::test_name        # один тест
pytest --cov=plugins --cov=app                # с покрытием
```

Конфиг pytest в `pyproject.toml`: `testpaths = ["tests", "plugins", "tools"]`, `pythonpath = ["."]`. Запускать именно **pytest**, не `python test_*.py`.

## Как писать тесты

- Файлы: `test_*.py` или `*_test.py`; функции: `test_*`.
- Async-тесты: декоратор `@pytest.mark.asyncio`, фикстуры из локального `conftest.py` (например `parser`, `processor`, `mock_logger`, `api_bus`).
- Использовать хелперы из того же `conftest` (например `check_match`, `process_text`), не дублировать логику инициализации.

Пример (unit в плагине):

```python
import pytest
from plugins.core.condition_parser.tests.conftest import check_match

@pytest.mark.asyncio
async def test_eq_integer(parser):
    result = await check_match(parser, "$x == 1", {"x": 1})
    assert result is True
```

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| `ModuleNotFoundError: No module named 'plugins'` | Запускать `pytest` из корня, не `python test_*.py`. |
| Фикстура не найдена (`parser`, `processor` и т.д.) | Запускать так, чтобы подхватывался локальный `conftest.py`: например `pytest plugins/core/<plugin>/tests/` или `pytest` из корня. |

Маркеры в `pyproject.toml`: `unit`, `integration`, `asyncio` (режим `asyncio_mode = "auto"`). Остальные опции pytest (`-k`, `-x`, `-s`, `--lf`) — по необходимости.
