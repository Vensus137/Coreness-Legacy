"""Менеджер scheduled-сценариев"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from croniter import croniter


class ScheduledScenarioManager:
    """
    Менеджер scheduled-сценариев
    - Кэширование метаданных scheduled-сценариев
    - Проверка расписания и запуск сценариев
    - Обновление метаданных после выполнения
    """
    
    def __init__(self, logger, scenario_engine, scheduled_timeout: float = 0):
        self.logger = logger
        self.scenario_engine = scenario_engine
        self.scheduled_timeout = scheduled_timeout  # 0 — без таймаута
        
        # Кэш метаданных scheduled-сценариев
        # {scenario_id: {'cron': str, 'last_run': datetime | None, 'next_run': datetime, 'scenario_name': str, 'is_running': bool}}
        self._scheduled_metadata: Dict[int, Dict[str, Any]] = {}
        
        # Состояние сервиса
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None
    
    async def run(self):
        """Главный цикл менеджера scheduled-сценариев"""
        try:
            self.is_running = True
            
            # Загрузка всех scheduled-сценариев при старте
            await self.load_scheduled_scenarios()
            
            # Запуск фонового цикла проверки scheduled-сценариев
            self._scheduler_task = asyncio.create_task(self._run_scheduler_loop())
            await self._scheduler_task
            
        except asyncio.CancelledError:
            self.logger.info("ScheduledScenarioManager остановлен")
        except Exception as e:
            self.logger.error(f"Ошибка в главном цикле ScheduledScenarioManager: {e}")
        finally:
            self.is_running = False
    
    def shutdown(self):
        """Синхронное корректное завершение менеджера"""
        if not self.is_running:
            return
        
        self.logger.info("Остановка ScheduledScenarioManager...")
        self.is_running = False
        
        # Отмена фонового цикла если запущен
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
        
        self.logger.info("ScheduledScenarioManager остановлен")
    
    async def load_scheduled_scenarios(self):
        """Загрузка всех scheduled-сценариев при старте сервиса"""
        try:
            # Получение списка scheduled-сценариев из движка
            scheduled_scenarios = self.scenario_engine.get_scheduled_scenarios()
            
            loaded_count = 0
            
            for scenario in scheduled_scenarios:
                scenario_id = scenario['id']
                cron = scenario['schedule']
                scenario_name = scenario['scenario_name']
                
                # last_run не персистим — пропущенные слоты после рестарта не догоняем
                last_run = None
                now = datetime.now()
                if last_run:
                    next_run = self._get_next_run_time(cron, last_run)
                else:
                    # Если ещё не запускался - от текущего времени
                    next_run = self._get_next_run_time(cron, now)
                
                if next_run is None:
                    self.logger.warning(f"Не удалось вычислить next_run для сценария {scenario_id} с cron '{cron}'")
                    continue
                
                # Обновление кэша
                self._scheduled_metadata[scenario_id] = {
                    'cron': cron,
                    'last_run': last_run,
                    'next_run': next_run,
                    'scenario_name': scenario_name,
                    'is_running': False
                }
                loaded_count += 1
            
            if loaded_count > 0:
                self.logger.info(f"Загружено {loaded_count} scheduled-сценариев")
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки scheduled-сценариев при старте: {e}")
    
    async def reload_scheduled_metadata(self) -> bool:
        """Перезагрузка метаданных scheduled-сценариев"""
        try:
            # Очистка старого кэша
            self._scheduled_metadata.clear()
            
            # Загрузка заново
            await self.load_scheduled_scenarios()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка перезагрузки метаданных scheduled-сценариев: {e}")
            return False
    
    async def _run_scheduler_loop(self):
        """Фоновый цикл проверки scheduled-сценариев"""
        while self.is_running:
            try:
                await self._check_scheduled_scenarios()
                
                # Ожидание до начала следующей минуты
                now = datetime.now()
                seconds_to_wait = 60 - now.second
                await asyncio.sleep(seconds_to_wait)
                
            except asyncio.CancelledError:
                self.logger.info("Цикл планировщика остановлен")
                break
            except Exception as e:
                self.logger.error(f"Ошибка в цикле планировщика: {e}")
                await asyncio.sleep(60)
    
    async def _check_scheduled_scenarios(self):
        """Проверка и запуск scheduled-сценариев"""
        try:
            # Получение текущего времени
            now = datetime.now()
            
            # Округление до начала минуты для точности
            now = now.replace(second=0, microsecond=0)
            
            # Фильтрация сценариев которые нужно запустить
            scenarios_to_run = []
            
            for scenario_id, metadata in self._scheduled_metadata.items():
                # Проверка по next_run (быстрее чем проверять cron каждый раз)
                # И проверка что сценарий не запущен уже
                if metadata['next_run'] <= now and not metadata.get('is_running', False):
                    scenarios_to_run.append({
                        'scenario_id': scenario_id,
                        **metadata
                    })
            
            # Запуск найденных сценариев
            for scenario_info in scenarios_to_run:
                asyncio.create_task(self._run_scheduled_scenario(scenario_info))
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки scheduled-сценариев: {e}")
    
    async def _run_scheduled_scenario(self, scenario_info: Dict[str, Any]):
        """Запуск scheduled-сценария"""
        scenario_id = scenario_info['scenario_id']
        scenario_name = scenario_info['scenario_name']
        cron = scenario_info['cron']
        
        # Проверка снова что сценарий не запущен (защита от race condition)
        if self._scheduled_metadata.get(scenario_id, {}).get('is_running', False):
            return
        
        # Отметка сценария как запущенного
        self._scheduled_metadata[scenario_id]['is_running'] = True
        
        try:
            # Создание синтетического события для scheduled-сценария
            scheduled_at = datetime.now()
            synthetic_event = {
                'event_type': 'scheduled',
                'event_source': 'schedule',
                'event_timestamp': int(scheduled_at.timestamp()),
                'scheduled_at': scheduled_at.isoformat(),
                'scheduled_scenario_id': scenario_id,
                'scheduled_scenario_name': scenario_name,
            }
            
            # Запуск через scenario_engine.execute_scenario_by_name (с таймаутом при необходимости)
            if self.scheduled_timeout > 0:
                result, _ = await asyncio.wait_for(
                    self.scenario_engine.execute_scenario_by_name(
                        scenario_name=scenario_name,
                        data=synthetic_event
                    ),
                    timeout=self.scheduled_timeout
                )
            else:
                result, _ = await self.scenario_engine.execute_scenario_by_name(
                    scenario_name=scenario_name,
                    data=synthetic_event
                )
            
            # Получение времени завершения
            completion_time = datetime.now()
            
            # Логирование ошибки если есть, но продолжить обновление метаданных
            if result == 'error':
                self.logger.warning(f"Ошибка выполнения scheduled-сценария '{scenario_name}' (ID: {scenario_id})")
            
            # Обновление last_run в памяти (для расчёта next_run), без персиста
            self._scheduled_metadata[scenario_id]['last_run'] = scheduled_at
            
            # Вычисление next_run от времени завершения (стандартное поведение cron)
            # Пропущенные запуски просто пропускаются, следующий будет в будущем
            next_run = self._get_next_run_time(cron, completion_time)
            if next_run:
                self._scheduled_metadata[scenario_id]['next_run'] = next_run
            else:
                self.logger.warning(f"Не удалось вычислить next_run для сценария {scenario_id}")
                
        except Exception as e:
            self.logger.error(f"Ошибка запуска scheduled-сценария {scenario_id}: {e}")
        finally:
            # Очистка флага запуска
            self._scheduled_metadata[scenario_id]['is_running'] = False
    
    def _get_next_run_time(self, cron: str, base_time: datetime) -> Optional[datetime]:
        """Вычисление следующего времени запуска по cron выражению"""
        try:
            cron_iter = croniter(cron, base_time)
            next_run = cron_iter.get_next(datetime)
            return next_run
        except Exception as e:
            self.logger.error(f"Ошибка вычисления next_run для cron '{cron}': {e}")
            return None
    
    def _is_valid_cron(self, cron: str) -> bool:
        """Проверка валидности cron выражения"""
        try:
            croniter(cron)
            return True
        except Exception:
            return False
