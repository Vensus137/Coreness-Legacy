"""WebSocket-сервер для связи Electron frontend с API Bus (actions + events)."""

import asyncio
import json
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from app.runtime.container import Container
from app.runtime.context import AppContext

# События, которые пробрасываем во frontend по WebSocket.
# API Bus работает в процессе; фронт (Electron) подключён по сокету. Когда плагин или ядро
# вызывает api_bus.emit("chat:new_message", data), подписчики в Python получают событие, но
# фронт — нет. Проброс (bridge): подписываемся на эти имена и кладём событие в очередь,
# которую рассылаем всем подключённым клиентам. Фронт получает { event, data } и обрабатывает.
EVENTS_TO_BRIDGE = ("chat:new_message", "chat:clear", "chat:message_removed", "chat:message_changed", "ui:show_modal", "vector_store:chunks_changed")


def run_ws_server(context: AppContext, container: Container, app_config: dict, host: str = "127.0.0.1", port: int = 29773, connection_timeout: int = 60) -> None:
    """Запуск event loop с WebSocket-сервером и фоновыми задачами плагинов."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    connections: set[WebSocketServerProtocol] = set()
    event_queue: asyncio.Queue = asyncio.Queue()
    first_connection_event = asyncio.Event()

    def _push_event(event: str, data: dict) -> None:
        try:
            loop.call_soon_threadsafe(event_queue.put_nowait, {"event": event, "data": data})
        except Exception:
            pass

    for ev in EVENTS_TO_BRIDGE:
        context.api_bus.subscribe(ev, lambda d, e=ev: _push_event(e, d))

    async def broadcast_events() -> None:
        while True:
            msg = await event_queue.get()
            dead = set()
            for ws in connections:
                try:
                    await ws.send(json.dumps(msg, ensure_ascii=False))
                except Exception:
                    dead.add(ws)
            for ws in dead:
                connections.discard(ws)

    async def process_one(raw: bytes, ws: WebSocketServerProtocol, send_lock: asyncio.Lock) -> None:
        """Обработка одного сообщения; ответ отправляется под send_lock."""
        try:
            msg = json.loads(raw)
        except Exception:
            async with send_lock:
                await ws.send(json.dumps({"id": None, "result": {"result": "error", "error": {"code": "INVALID_JSON", "message": "Неверный JSON"}}}))
            return
        req_id = msg.get("id")
        action = msg.get("action")
        payload = msg.get("payload")
        if not action or not isinstance(payload, dict):
            async with send_lock:
                await ws.send(json.dumps({"id": req_id, "result": {"result": "error", "error": {"code": "INVALID_PAYLOAD", "message": "Нужны action и payload"}}}))
            return
        try:
            result = await context.api_bus.call(action, payload)
        except Exception as e:
            result = {"result": "error", "error": {"code": "ERROR", "message": str(e)}}
        async with send_lock:
            await ws.send(json.dumps({"id": req_id, "result": result}, ensure_ascii=False))

    async def wait_for_first_connection() -> None:
        """Ожидает первое подключение в течение connection_timeout секунд."""
        try:
            await asyncio.wait_for(first_connection_event.wait(), timeout=connection_timeout)
        except asyncio.TimeoutError:
            context.logger.error(f"Таймаут: фронт не подключился за {connection_timeout} секунд")
            raise TimeoutError(f"Таймаут подключения: фронт не подключился за {connection_timeout} секунд")

    async def handler(ws: WebSocketServerProtocol) -> None:
        connections.add(ws)
        if not first_connection_event.is_set():
            first_connection_event.set()
            context.logger.info("Первое подключение фронта установлено")
        send_lock = asyncio.Lock()
        try:
            async for raw in ws:
                asyncio.create_task(process_one(raw, ws, send_lock))
        finally:
            connections.discard(ws)

    async def main() -> None:
        container.run()
        # Фоновая задача для рассылки событий всем подключенным клиентам
        broadcast_task = asyncio.create_task(broadcast_events())
        connection_timeout_task = asyncio.create_task(wait_for_first_connection())
        async with websockets.serve(handler, host, port, ping_interval=20, ping_timeout=20) as server:
            context.logger.info(f"WebSocket сервер: ws://{host}:{port}")
            print(f"ws://{host}:{port}", flush=True)
            try:
                await connection_timeout_task
            except TimeoutError:
                context.logger.warning("Завершение работы из-за таймаута подключения")
                broadcast_task.cancel()
                try:
                    await broadcast_task
                except asyncio.CancelledError:
                    pass
                return
            except asyncio.CancelledError:
                pass
            await asyncio.Future()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(container.shutdown())
        loop.close()
