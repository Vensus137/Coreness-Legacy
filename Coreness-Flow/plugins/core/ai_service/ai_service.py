"""Плагин AI Service: комплишн через агрегатор (OpenAI-совместимый API). Управление профилями."""

import asyncio
from typing import Any, Dict

from .modules.client import AIClient


class AiService:
    """Комплишн через агрегатор. Профили (api_key, base_url, default_model) управляются через UI настроек AI."""

    def __init__(self, config: dict, context: Any) -> None:
        self.config = config
        self.logger = context.logger
        self._client = AIClient(config=config, logger=self.logger)
        self._plugin_id = (config.get("metadata") or {}).get("name")
        context.api_bus.subscribe(f"plugin:settings_changed:{self._plugin_id}", self._on_settings_changed)
        self.logger.info("AiService плагин инициализирован")

    def _on_settings_changed(self, data: dict) -> None:
        """Обновляет клиент при изменении профилей из UI."""
        settings = data.get("settings") or {}
        self.config["settings"] = dict(settings)
        self._client = AIClient(config=self.config, logger=self.logger)
        self.logger.info("Настройки ai_service обновлены (профили)")

    async def completion(self, payload: dict) -> Dict[str, Any]:
        """Комплишн через агрегатор. Инициализация клиента — в потоке, чтобы не блокировать UI."""
        prompt = payload.get("prompt", "")
        if not prompt:
            return {"result": "error", "error": {"code": "VALIDATION_ERROR", "message": "Параметр prompt обязателен."}}
        ready = await asyncio.to_thread(self._client._ensure_client)
        if not ready:
            return {"result": "error", "error": {"code": "CONFIG_ERROR", "message": "Активный профиль AI не настроен. Откройте раздел AI и добавьте профиль."}}
        return await self._client.completion(
            prompt=payload.get("prompt", ""),
            system_prompt=payload.get("system_prompt", ""),
            model=payload.get("model"),
            max_tokens=payload.get("max_tokens"),
            temperature=payload.get("temperature"),
            messages=payload.get("messages"),
            chunks=payload.get("chunks"),
            tool_results=payload.get("tool_results"),
            context=payload.get("context", ""),
            json_mode=payload.get("json_mode"),
            json_schema=payload.get("json_schema"),
            tools=payload.get("tools"),
            tool_choice=payload.get("tool_choice"),
        )

    async def get_aggregators(self, payload: dict) -> Dict[str, Any]:
        """Возвращает список агрегаторов из settings плагина."""
        aggregators = (self.config.get("settings") or {}).get("aggregators") or []
        return {"result": "success", "response_data": {"aggregators": aggregators}}

    async def get_models(self, payload: dict) -> Dict[str, Any]:
        """Получает список доступных моделей агрегатора. api_key опционален."""
        base_url = payload.get("base_url", "")
        api_key = payload.get("api_key", "")
        return await self._client.get_models(base_url=base_url, api_key=api_key)

    async def validate_token(self, payload: dict) -> Dict[str, Any]:
        """Проверяет API-ключ через запрос списка моделей агрегатора."""
        base_url = payload.get("base_url", "")
        api_key = payload.get("api_key", "")
        return await self._client.validate_token(base_url=base_url, api_key=api_key)
