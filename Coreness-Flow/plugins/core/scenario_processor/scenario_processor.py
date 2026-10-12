"""Плагин обработки сценариев"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from .modules.scenario_engine import ScenarioEngine
from .modules.scheduled_scenario_manager import ScheduledScenarioManager
from .modules.actions.execute_scenario import run_execute_scenario
from .modules.actions.wait_for_action import run_wait_for_action
from .modules.actions.cache_actions import run_set_cache, run_delete_cache


class ScenarioProcessor:
    """
    Плагин обработки сценариев
    - Загрузка сценариев из YAML
    - Обработка событий по триггерам
    - Выполнение шагов и переходов
    - Scheduled-сценарии
    """
    
    def __init__(self, config: dict, context):
        self.config = config
        self.api_bus = context.api_bus
        self.logger = context.logger
        settings = config.get("settings") or {}
        app_meta = config.get("app_metadata") or {}

        self._project_root = Path(app_meta["project_root"]) if app_meta.get("project_root") else Path.cwd()
        scenarios_path = settings.get("scenarios_path", "config/scenarios")
        if not Path(scenarios_path).is_absolute():
            scenarios_path = self._project_root / scenarios_path

        step_timeout = float(settings.get("step_timeout", 60) or 0)
        scenario_timeout = float(settings.get("scenario_timeout", 300) or 0)
        scheduled_timeout = float(settings.get("scheduled_timeout", 300) or 0)

        self._plugin_id = (config.get("metadata") or {}).get("name")
        context.api_bus.subscribe(f"plugin:settings_changed:{self._plugin_id}", self._on_settings_changed)

        # Создание движка сценариев
        self.scenario_engine = ScenarioEngine(
            logger=self.logger,
            api_bus=self.api_bus,
            scenarios_path=str(scenarios_path),
            step_timeout=step_timeout,
            scenario_timeout=scenario_timeout
        )
        
        # Создание менеджера scheduled-сценариев (проверка cron каждую минуту)
        self.scheduled_manager = ScheduledScenarioManager(
            logger=self.logger,
            scenario_engine=self.scenario_engine,
            scheduled_timeout=scheduled_timeout
        )
        
        # Действия регистрируются в API Bus по config (register_plugin)
        # Состояние сервиса
        self.is_running = False
        self._run_task: Optional[asyncio.Task] = None
        self.logger.info("ScenarioProcessor плагин инициализирован")

    def _on_settings_changed(self, data: dict) -> None:
        """Обновляет атрибуты при изменении настроек из UI (событие plugin:settings_changed:{plugin_id})."""
        settings = data.get("settings") or {}
        if "scenarios_path" in settings:
            path = Path(settings["scenarios_path"])
            self.scenario_engine.loader.scenarios_path = path if path.is_absolute() else self._project_root / path
        if "step_timeout" in settings:
            self.scenario_engine.step_executor.step_timeout = float(settings["step_timeout"] or 0)
        if "scenario_timeout" in settings:
            self.scenario_engine.executor.scenario_timeout = float(settings["scenario_timeout"] or 0)
        if "scheduled_timeout" in settings:
            self.scheduled_manager.scheduled_timeout = float(settings["scheduled_timeout"] or 0)
        self.logger.info("Настройки scenario_processor обновлены из UI")

    async def run(self):
        """Главный цикл сервиса"""
        try:
            self.is_running = True
            
            # Запуск менеджера scheduled-сценариев
            await self.scheduled_manager.run()
            
        except asyncio.CancelledError:
            self.logger.info("ScenarioProcessor остановлен")
        except Exception as e:
            self.logger.error(f"Ошибка в главном цикле ScenarioProcessor: {e}")
        finally:
            self.is_running = False
    
    def shutdown(self):
        """Синхронное корректное завершение сервиса"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Остановка менеджера scheduled-сценариев
        self.scheduled_manager.shutdown()
    
    # === Действия для API Bus ===
    
    async def sync_scenarios(self, payload: dict) -> Dict[str, Any]:
        """
        Синхронизация сценариев: загрузка из YAML + обновление кэша
        """
        try:
            force_reload = payload.get('force_reload', False)
            
            # Перезагрузка сценариев
            if force_reload or not self.scenario_engine.cache.has_cache():
                success = await self.scenario_engine.reload_scenarios()
                if not success:
                    return {
                        "result": "error",
                        "error": {
                            "code": "RELOAD_ERROR",
                            "message": "Не удалось перезагрузить сценарии"
                        }
                    }
                
                # Перезагрузка метаданных scheduled-сценариев
                scheduled_success = await self.scheduled_manager.reload_scheduled_metadata()
                if not scheduled_success:
                    self.logger.warning("Не удалось перезагрузить метаданные scheduled-сценариев")
            
            # Подсчёт загруженных сценариев
            cache = self.scenario_engine.cache.get_cache()
            loaded_count = len(cache.get('scenario_index', {})) if cache else 0
            
            return {
                "result": "success",
                "response_data": {
                    "loaded_count": loaded_count
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации сценариев: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }

    async def set_cache(self, payload: dict) -> Dict[str, Any]:
        """Запись данных в _cache сценария: возвращает cache из payload для мержа через merge_response_data (с учётом _namespace)."""
        return await run_set_cache(payload)

    async def delete_cache(self, payload: dict) -> Dict[str, Any]:
        """Удаление неймспейса/пути из _cache. Поддержка вложенности через точку (tools.ai_agent). Префикс _cache. в значении отбрасывается."""
        try:
            return await run_delete_cache(payload)
        except Exception as e:
            self.logger.error(f"Ошибка delete_cache: {e}")
            return {"result": "error", "error": {"code": "INTERNAL_ERROR", "message": str(e)}}

    async def process_scenario_event(self, payload: dict) -> Dict[str, Any]:
        """
        Обработка события по сценариям
        """
        try:
            # Обработка события через scenario_engine
            success = await self.scenario_engine.process_event(payload)
            
            if success:
                return {"result": "success"}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось обработать событие по сценариям"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки события: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def execute_scenario(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение сценария или массива сценариев по имени."""
        try:
            return await run_execute_scenario(self.scenario_engine, payload)
        except Exception as e:
            self.logger.error(f"Ошибка выполнения сценария: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            }
    
    async def wait_for_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ожидание завершения асинхронного действия по action_id. Возвращает результат основного действия AS IS."""
        try:
            return await run_wait_for_action(payload)
        except Exception as e:
            self.logger.error(f"Ошибка ожидания async-действия: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            }
