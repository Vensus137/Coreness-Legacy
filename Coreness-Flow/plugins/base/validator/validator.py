"""Плагин валидации условий в сценариях через condition_parser (API Bus)."""

from typing import Any, Dict


class Validator:
    """
    Сервис валидации условий: принимает условие и данные контекста,
    вызывает check_match через ApiBus, возвращает result success/failed/error.
    """

    def __init__(self, config: dict, context) -> None:
        self.config = config
        self.api_bus = context.api_bus
        self.logger = context.logger
        self.logger.info("Validator плагин инициализирован")

    async def validate(self, payload: dict) -> Dict[str, Any]:
        """Валидация условия: condition + контекст в payload, результат success/failed/error."""
        try:
            condition = payload.get("condition")
            if condition is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Поле 'condition' обязательно",
                    },
                }

            # Остальные ключи payload — данные для проверки условия
            context_data = {k: v for k, v in payload.items() if k != "condition"}

            check_result = await self.api_bus.call(
                "check_match",
                {"condition": condition, "data": context_data},
            )

            if check_result.get("result") == "error":
                return check_result

            matched = (check_result.get("response_data") or {}).get("matched")
            if matched is True:
                return {"result": "success"}
            if matched is False:
                return {"result": "failed"}

            self.logger.error(
                "Некорректный ответ check_match: matched=%s (type=%s)",
                matched,
                type(matched).__name__,
            )
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Некорректный результат проверки: {matched}",
                },
            }
        except Exception as e:
            self.logger.exception("Ошибка валидации условия: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                },
            }
