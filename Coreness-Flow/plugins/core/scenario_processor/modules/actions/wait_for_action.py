"""Ожидание завершения асинхронного действия по action_id."""

import asyncio
from concurrent.futures import Future as ConcurrentFuture
from typing import Any, Dict


async def run_wait_for_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ожидание завершения асинхронного действия по action_id.
    Возвращает результат основного действия AS IS. Поддержка concurrent.futures.Future и asyncio Future/Task.
    """
    action_id = payload.get("action_id")
    timeout = payload.get("timeout")
    async_action = payload.get("_async_action", {})

    if action_id not in async_action:
        return {
            "result": "error",
            "error": {
                "code": "NOT_FOUND",
                "message": f"Async-действие с action_id={action_id} не найдено",
            },
        }

    future = async_action[action_id]
    is_concurrent = isinstance(future, ConcurrentFuture)
    if not is_concurrent and not isinstance(future, (asyncio.Future, asyncio.Task)):
        return {
            "result": "error",
            "error": {
                "code": "INVALID_STATE",
                "message": f"Неверный тип Future для action_id={action_id}",
            },
        }

    awaitable = asyncio.wrap_future(future) if is_concurrent else future

    if awaitable.done():
        try:
            return awaitable.result()
        except Exception as e:
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            }

    try:
        if timeout:
            result = await asyncio.wait_for(awaitable, timeout=float(timeout))
        else:
            result = await awaitable
        return result
    except asyncio.TimeoutError:
        return {
            "result": "timeout",
            "error": {
                "code": "TIMEOUT",
                "message": f"Превышен таймаут для action_id={action_id}",
            },
        }
    except Exception as e:
        return {
            "result": "error",
            "error": {"code": "INTERNAL_ERROR", "message": str(e)},
        }
