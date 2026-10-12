"""OpenAI-совместимый клиент для агрегаторов (completion, models). Ленивый импорт openai в фоне."""

import json
import threading
from typing import Any, Dict, List, Optional, Union


class AIClient:
    """Запросы к агрегатору по OpenAI-совместимому API. AsyncOpenAI создаётся при первом использовании в потоке (не блокирует UI)."""

    def __init__(self, config: dict, logger: Any) -> None:
        self.logger = logger
        settings = config.get("settings") or config
        profile = self._resolve_active_profile(settings)
        self.api_key = profile.get("api_key", "")
        self.base_url = self._normalize_url(profile.get("base_url", ""))
        self.default_model = profile.get("default_model", "")
        self._client = None  # Будет создан при первом вызове completion (в потоке)
        self._client_lock = threading.Lock()

    def _resolve_active_profile(self, settings: dict) -> dict:
        """Возвращает активный профиль из списка. При отсутствии профилей — совместимость со старым форматом (api_key/base_url)."""
        profiles_raw = settings.get("profiles", "[]")
        active_id = settings.get("active_profile_id", "")
        try:
            profiles = json.loads(profiles_raw) if isinstance(profiles_raw, str) else profiles_raw
        except Exception:
            profiles = []
        if not profiles:
            return {
                "api_key": settings.get("api_key", ""),
                "base_url": settings.get("base_url", ""),
                "default_model": settings.get("default_model", ""),
            }
        if active_id:
            for p in profiles:
                if p.get("id") == active_id:
                    return p
        return profiles[0]

    def _normalize_url(self, url: str) -> str:
        """Нормализует URL: добавляет https:// если нет схемы, убирает www. без схемы."""
        if not url:
            return url
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            if url.startswith("www."):
                url = url[4:]
            url = "https://" + url
        return url

    def _ensure_client(self) -> bool:
        """Создаёт AsyncOpenAI при первом использовании. Вызывать через asyncio.to_thread(), чтобы не блокировать UI."""
        with self._client_lock:
            if self._client is not None:
                return True
            if not self.base_url or not self.api_key:
                return False
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
                return True
            except Exception as e:
                self.logger.error("Ошибка импорта openai: %s", e)
                return False

    async def completion(self, prompt: str, system_prompt: str = "", model: Optional[str] = None,
                         max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                         messages: Optional[List[Dict[str, Any]]] = None,
                         chunks: Optional[List[Dict[str, Any]]] = None,
                         tool_results: Optional[List[Dict[str, Any]]] = None,
                         context: Optional[str] = None,
                         json_mode: Optional[str] = None, json_schema: Optional[Dict[str, Any]] = None,
                         tools: Optional[List[Dict[str, Any]]] = None, tool_choice: Optional[Union[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Completion через агрегатор. Клиент создается при первом вызове."""
        if not self._ensure_client():
            return {"result": "error", "error": {"code": "CONFIG_ERROR", "message": "Активный профиль AI не настроен. Откройте раздел AI и добавьте профиль."}}
        model = model or self.default_model
        if not model:
            return {"result": "error", "error": {"code": "CONFIG_ERROR", "message": "Модель не задана (параметр запроса или настройка default_model в активном профиле)."}}
        try:
            response_format = self._build_response_format(json_mode, json_schema)
            api_messages = self._build_messages(
                prompt=prompt,
                system_prompt=system_prompt,
                history=messages,
                chunks=chunks,
                tool_results=tool_results,
                context=context or "",
            )
            api_params: Dict[str, Any] = {"model": model, "messages": api_messages}
            if max_tokens is not None:
                api_params["max_tokens"] = max_tokens
            if temperature is not None:
                api_params["temperature"] = temperature
            if response_format:
                api_params["response_format"] = response_format
            if tools:
                api_params["tools"] = tools
            if tool_choice is not None:
                api_params["tool_choice"] = tool_choice
            # Дебаг: что уходит в API (разложенный OpenAI-протокол)
            self.logger.debug(
                "completion request (openai protocol): %s",
                json.dumps(api_params, ensure_ascii=False, indent=2),
            )
            response = await self._client.chat.completions.create(**api_params)
            message = response.choices[0].message
            response_content = message.content or ""
            calls_functions: List[Dict[str, Any]] = []
            calls_response: List[Dict[str, Any]] = []
            tool_calls_debug: List[Dict[str, Any]] = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    name = tc.function.name or ""
                    raw_args = (tc.function.arguments or "").strip()
                    try:
                        arguments = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        arguments = {}
                    if not isinstance(arguments, dict):
                        arguments = {}
                    item = {"name": name, "arguments": arguments}
                    tool_calls_debug.append({"id": getattr(tc, "id", ""), "name": name, "arguments": arguments})
                    if name.startswith("response_"):
                        calls_response.append(item)
                    else:
                        calls_functions.append(item)
            response_debug = {
                "content": response_content,
                "tool_calls": tool_calls_debug,
                "usage": {"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens} if response.usage else None,
            }
            self.logger.debug("completion response: %s", json.dumps(response_debug, ensure_ascii=False, indent=2))
            result: Dict[str, Any] = {
                "result": "success",
                "response_data": {
                    "response_completion": response_content,
                    "response_meta": {
                        "model": model,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                },
            }
            if json_mode and response_content:
                parsed = self._parse_json_response(response_content)
                if parsed is not None:
                    result["response_data"]["response_dict"] = parsed
            if calls_functions:
                result["response_data"]["tool_calls"] = calls_functions
            if calls_response:
                result["response_data"]["response_calls"] = calls_response
            return result
        except Exception as e:
            self.logger.error("Ошибка completion: %s", e)
            return {"result": "error", "error": {"code": "API_ERROR", "message": str(e)}}

    async def get_models(self, base_url: str, api_key: str = "") -> Dict[str, Any]:
        """Получает список доступных моделей агрегатора. api_key опционален — некоторые эндпоинты публичны."""
        url = self._normalize_url(base_url)
        if not url:
            return {"result": "error", "error": {"code": "CONFIG_ERROR", "message": "base_url обязателен."}}
        try:
            from openai import AsyncOpenAI
            async with AsyncOpenAI(api_key=api_key or "no-key", base_url=url) as client:
                models_page = await client.models.list()
                model_ids = sorted([m.id for m in models_page.data])
            return {"result": "success", "response_data": {"models": model_ids}}
        except Exception as e:
            self.logger.error("Ошибка get_models: %s", e)
            return {"result": "error", "error": {"code": "API_ERROR", "message": str(e)}}

    async def validate_token(self, base_url: str, api_key: str) -> Dict[str, Any]:
        """Проверяет соединение с агрегатором через запрос списка моделей."""
        url = self._normalize_url(base_url)
        if not url or not api_key:
            return {"result": "error", "error": {"code": "CONFIG_ERROR", "message": "base_url и api_key обязательны."}}
        try:
            from openai import AsyncOpenAI
            async with AsyncOpenAI(api_key=api_key, base_url=url) as client:
                models_page = await client.models.list()
                count = len(models_page.data)
            return {"result": "success", "response_data": {"models_count": count}}
        except Exception as e:
            self.logger.error("Ошибка validate_token: %s", e)
            return {"result": "error", "error": {"code": "API_ERROR", "message": str(e)}}

    def _build_response_format(self, json_mode: Optional[str], json_schema: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not json_mode:
            return None
        if json_mode == "json_schema" and json_schema:
            return {"type": "json_schema", "json_schema": json_schema}
        return {"type": "json_object"}

    def _build_messages(self, prompt: str, system_prompt: str = "",
                        history: Optional[List[Dict[str, Any]]] = None,
                        chunks: Optional[List[Dict[str, Any]]] = None,
                        tool_results: Optional[List[Dict[str, Any]]] = None,
                        context: str = "") -> List[Dict[str, Any]]:
        """
        Сборка messages для API по схеме:
          1. system    → system_prompt (если задан)
          2. user/assistant → история (если передана, system/auto → user)
          3. user      → <context> чанки (худший→лучший) </context>
                         <tool_results> результаты (старый→новый по timestamp) </tool_results>
                         <env> кастомный контекст сценария (дата, пользователь и т.п.) </env>
                         <message> исходное сообщение пользователя </message>
        """
        result: List[Dict[str, Any]] = []

        if system_prompt:
            result.append({"role": "system", "content": system_prompt})

        # История: user→user, assistant→assistant, всё остальное (auto, system и др.) → user
        if history:
            for msg in history:
                sender = msg.get("sender") or msg.get("role") or ""
                text = msg.get("text") or msg.get("content") or ""
                if not text:
                    continue
                role = "assistant" if sender == "assistant" else "user"
                result.append({"role": role, "content": text})

        # Последнее user-сообщение: собираем блоки контекста перед промптом
        content_blocks: List[str] = []

        # RAG-чанки: переворачиваем чтобы лучший (высший score) шёл последним —
        # ближе к промпту = больше внимания модели
        if chunks:
            context_parts = []
            for i, chunk in enumerate(reversed(chunks), 1):
                chunk_text = chunk.get("text", "")
                if chunk_text:
                    context_parts.append(f"[{i}]\n{chunk_text}")
            if context_parts:
                content_blocks.append("<context>\n" + "\n\n".join(context_parts) + "\n</context>")

        # Результаты функций (tool_results): сортируем по timestamp (старый→новый),
        # новые результаты — ближе к промпту = в фокусе модели
        if tool_results:
            sorted_results = sorted(tool_results, key=lambda r: r.get("timestamp") or 0)
            result_parts = []
            for r in sorted_results:
                name = r.get("name", "function")
                content = str(r.get("content", ""))
                if content:
                    result_parts.append(f"[{name}]\n{content}")
            if result_parts:
                content_blocks.append("<tool_results>\n" + "\n\n".join(result_parts) + "\n</tool_results>")

        if context and context.strip():
            content_blocks.append("<env>\n" + context.strip() + "\n</env>")

        prompt_block = ("<message>\n" + prompt + "\n</message>") if prompt else ""
        parts = content_blocks + ([prompt_block] if prompt_block else [])
        user_content = "\n\n".join(parts) if parts else prompt
        result.append({"role": "user", "content": user_content})

        return result

    def _parse_json_response(self, content: str) -> Optional[Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        try:
            out = json.loads(cleaned)
            return out if isinstance(out, (dict, list)) else None
        except json.JSONDecodeError:
            return None
