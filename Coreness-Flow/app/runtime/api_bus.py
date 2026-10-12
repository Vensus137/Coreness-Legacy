"""In-process роутер действий и событий: actions (request-response) и events (fire-and-forget)."""

import asyncio
import logging
from concurrent.futures import Future as ConcurrentFuture, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

_log = logging.getLogger(__name__)


def _run_async_in_worker(handler: Callable, payload: dict) -> dict:
    """Выполняет async-обработчик в потоке с отдельным event loop (не блокирует UI)."""
    coro = handler(payload)
    if not asyncio.iscoroutine(coro):
        return coro if isinstance(coro, dict) else {}
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class ApiBus:
    """Роутер вызовов действий и событий. Actions — async call(), Events — emit/subscribe (синхронные)."""

    def __init__(self, max_workers: int = 5) -> None:
        self._handlers: Dict[str, Callable[..., dict]] = {}
        self._action_configs: Dict[str, dict] = {}
        self._event_subscribers: Dict[str, List[Callable]] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ApiBus")
        self._max_workers = max_workers

    def register(self, action_name: str, handler: Callable[..., dict]) -> None:
        """Регистрирует обработчик для указанного имени действия."""
        if not action_name or not callable(handler):
            raise ValueError("action_name не должен быть пустым, handler должен быть вызываемым")
        self._handlers[action_name] = handler

    def register_plugin(self, instance: Any, actions: Dict[str, Any]) -> None:
        """Регистрирует действия плагина по конфигу: для каждого ключа в actions ищет метод с тем же именем у instance и регистрирует его."""
        for action_name, action_config in actions.items():
            if not action_name or not isinstance(action_config, dict):
                continue
            method = getattr(instance, action_name, None)
            if callable(method):
                self.register(action_name, method)
                self.set_action_config(action_name, action_config)

    def set_action_config(self, action_name: str, config: dict) -> None:
        """Регистрирует конфиг действия (input/output schema) для scenario_processor и т.п."""
        if action_name:
            self._action_configs[action_name] = config

    def get_action_config(self, action_name: str) -> Optional[Dict[str, Any]]:
        """Возвращает конфиг действия (input/output schema), если зарегистрирован."""
        return self._action_configs.get(action_name)

    def call_sync(self, action_name: str, payload: dict) -> dict:
        """Синхронный вызов действия (для __init__ плагинов и др.). Async-обработчики выполняются в текущем потоке с новым event loop."""
        if not isinstance(payload, dict):
            return self._error_result("INVALID_PAYLOAD", "payload должен быть словарём")
        handler = self._handlers.get(action_name)
        if handler is None:
            return self._error_result("NOT_FOUND", f"Действие '{action_name}' не зарегистрировано")
        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(result)
                finally:
                    loop.close()
            if not isinstance(result, dict):
                return self._error_result("INVALID_RESPONSE", "Обработчик должен возвращать словарь")
            return result
        except Exception as e:
            return self._error_result("ERROR", str(e), details=[repr(e)])

    async def call(self, action_name: str, payload: dict) -> dict:
        """Вызывает действие по имени. Async-обработчики выполняются в worker (отдельный event loop)."""
        if not isinstance(payload, dict):
            return self._error_result("INVALID_PAYLOAD", "payload должен быть словарём")
        handler = self._handlers.get(action_name)
        if handler is None:
            return self._error_result("NOT_FOUND", f"Действие '{action_name}' не зарегистрировано")

        current_loop = asyncio.get_event_loop()
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await current_loop.run_in_executor(
                    self._executor, _run_async_in_worker, handler, payload
                )
            else:
                result = await current_loop.run_in_executor(self._executor, handler, payload)
                if asyncio.iscoroutine(result):
                    result = await result

            if not isinstance(result, dict):
                return self._error_result("INVALID_RESPONSE", "Обработчик должен возвращать словарь")
            return result
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return self._error_result("ERROR", str(e), details=[repr(e)])

    async def call_nowait(self, action_name: str, payload: dict) -> dict:
        """Запускает действие без ожидания результата. Сразу возвращает успех (accepted); ошибки логируются."""
        if not isinstance(payload, dict):
            return self._error_result("INVALID_PAYLOAD", "payload должен быть словарём")
        handler = self._handlers.get(action_name)
        if handler is None:
            return self._error_result("NOT_FOUND", f"Действие '{action_name}' не зарегистрировано")
        current_loop = asyncio.get_event_loop()

        def _done_callback(fut: asyncio.Future) -> None:
            try:
                exc = fut.exception()
                if exc is not None:
                    _log.exception("call_nowait %s: %s", action_name, exc)
            except Exception:
                pass

        if asyncio.iscoroutinefunction(handler):
            future = current_loop.run_in_executor(
                self._executor, _run_async_in_worker, handler, payload
            )
        else:
            future = current_loop.run_in_executor(self._executor, handler, payload)
        future.add_done_callback(_done_callback)
        return {"result": "success"}

    def submit_action(self, action_name: str, payload: dict) -> ConcurrentFuture:
        """Запускает действие в executor и возвращает concurrent.futures.Future (можно ждать из любого event loop через asyncio.wrap_future)."""
        if not isinstance(payload, dict):
            f: ConcurrentFuture = ConcurrentFuture()
            f.set_exception(ValueError("payload должен быть словарём"))
            return f
        handler = self._handlers.get(action_name)
        if handler is None:
            f = ConcurrentFuture()
            f.set_exception(ValueError(f"Действие '{action_name}' не зарегистрировано"))
            return f

        def _run() -> dict:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = _run_async_in_worker(handler, payload)
                else:
                    result = handler(payload)
                    if asyncio.iscoroutine(result):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(result)
                        finally:
                            loop.close()
                if not isinstance(result, dict):
                    return self._error_result("INVALID_RESPONSE", "Обработчик должен возвращать словарь")
                return result
            except Exception as e:
                return self._error_result("ERROR", str(e), details=[repr(e)])

        return self._executor.submit(_run)

    def subscribe(self, event: str, handler: Callable) -> None:
        """Подписаться на событие."""
        if event not in self._event_subscribers:
            self._event_subscribers[event] = []
        self._event_subscribers[event].append(handler)

    def emit(self, event: str, data: dict) -> None:
        """Отправить событие подписчикам (fire-and-forget)."""
        subscribers = self._event_subscribers.get(event, [])
        for handler in subscribers:
            try:
                handler(data)
            except Exception:
                pass

    def shutdown(self) -> None:
        """Корректное завершение: остановка ThreadPoolExecutor."""
        self._executor.shutdown(wait=True)

    @staticmethod
    def _error_result(code: str, message: str, details: list | None = None) -> dict:
        return {
            "result": "error",
            "error": {
                "code": code,
                "message": message,
                **({"details": details} if details else {}),
            },
        }
