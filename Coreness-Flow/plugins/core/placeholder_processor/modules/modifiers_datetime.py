"""Модификаторы для работы с датами и временем."""
from datetime import timedelta
from typing import Any, Union

from dateutil.relativedelta import relativedelta

from .datetime_parser import parse_datetime_value, parse_interval_string


class DatetimeModifiers:
    """Модификаторы для работы с датами."""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_shift(self, value: Any, param: str) -> Union[str, Any]:
        """
        Date shift by specified interval (PostgreSQL style)
        
        Syntax: shift:+interval or shift:-interval
        
        Supported units (case-insensitive):
        - year, years, y
        - month, months, mon
        - week, weeks, w
        - day, days, d
        - hour, hours, h
        - minute, minutes, min, m
        - second, seconds, sec, s
        
        Examples:
        - {date|shift:+1 day}
        - {date|shift:-2 hours}
        - {date|shift:+1 year 2 months}
        - {date|shift:+1 week 3 days 6 hours}
        
        Supported input formats:
        - Unix timestamp: 1735128000
        - PostgreSQL: 2024-12-25, 2024-12-25 15:30:45
        - Standard: 25.12.2024, 25.12.2024 15:30, 25.12.2024 15:30:45
        - ISO: 2024-12-25T15:30:45
        - Python datetime objects
        
        Возвращает строку в формате ISO (YYYY-MM-DD или YYYY-MM-DD HH:MM:SS).
        """
        if not value or not param:
            return value
        
        try:
            # 1. Check sign (+ or -)
            param_str = str(param).strip()
            if not param_str or param_str[0] not in ('+', '-'):
                self.logger.warning(f"Модификатор shift: в начале нужен знак + или -: '{param}'")
                return value
            
            sign = 1 if param_str[0] == '+' else -1
            interval_str = param_str[1:].strip()
            
            if not interval_str:
                self.logger.warning("Модификатор shift: пустой интервал после знака")
                return value
            
            # 2. Parse interval
            interval = parse_interval_string(interval_str)
            
            # Проверка, что хотя бы что-то распознано
            if all(v == 0 for v in interval.values()):
                self.logger.warning(f"Модификатор shift: не удалось разобрать интервал '{interval_str}'")
                return value
            
            # 3. Parse input date
            dt, has_time = parse_datetime_value(value)
            if dt is None:
                self.logger.warning(f"Модификатор shift: не удалось разобрать дату '{value}'")
                return value
            
            # 4. Apply shift
            # Для месяцев/лет — relativedelta (корректные границы месяцев)
            if interval['years'] or interval['months']:
                dt = dt + relativedelta(
                    years=sign * interval['years'],
                    months=sign * interval['months'],
                    weeks=sign * interval['weeks'],
                    days=sign * interval['days'],
                    hours=sign * interval['hours'],
                    minutes=sign * interval['minutes'],
                    seconds=sign * interval['seconds']
                )
            else:
                # Остальное — timedelta (быстрее)
                dt = dt + timedelta(
                    weeks=sign * interval['weeks'],
                    days=sign * interval['days'],
                    hours=sign * interval['hours'],
                    minutes=sign * interval['minutes'],
                    seconds=sign * interval['seconds']
                )
            
            # 5. Return in ISO format (without timezone and nanoseconds)
            if has_time:
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return dt.strftime('%Y-%m-%d')
        
        except Exception as e:
            self.logger.warning(f"Ошибка в модификаторе shift: {e}")
            return value
    
    def modifier_seconds(self, value: Any, param: str) -> Union[int, None]:
        """
        Convert time strings to seconds: {field|seconds}
        
        Supported format: Xw Yd Zh Km Ms
        (w - weeks, d - days, h - hours, m - minutes, s - seconds)
        
        Examples:
        - "2h 30m" → 9000
        - "1d 2w" → 1296000
        - "30m" → 1800
        """
        if not value:
            return None
        
        # Приводим к строке и разбираем
        time_string = str(value).strip()
        if not time_string:
            return None
        
        return self._parse_time_string(time_string)
    
    def _parse_time_string(self, time_string: str) -> Union[int, None]:
        """Разбор строки времени в секунды (например, '1w 5d 4h 30m 15s')."""
        import re
        
        if not time_string:
            return None
        
        # Шаблон для значений с единицами времени (цифры, пробелы, единицы)
        pattern = r"(\d+)\s*(w|d|h|m|s)\b"
        
        # Строка должна содержать только допустимые символы
        if not re.match(r"^[\d\s\w]+$", time_string.strip()):
            return None
        
        total_seconds = 0
        found_any = False
        
        for value, unit in re.findall(pattern, time_string):
            found_any = True
            value = int(value)
            if unit == 'w':
                total_seconds += value * 604800  # недели в секунды
            elif unit == 'd':
                total_seconds += value * 86400   # дни в секунды
            elif unit == 'h':
                total_seconds += value * 3600     # часы в секунды
            elif unit == 'm':
                total_seconds += value * 60       # минуты в секунды
            elif unit == 's':
                total_seconds += value            # секунды
        
        # Ничего не найдено или 0 — возвращаем None
        return total_seconds if found_any and total_seconds > 0 else None
    
    def modifier_to_date(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of day (00:00:00): {field|to_date}
        
        Examples:
        - {datetime|to_date} - start of day
        - {datetime|to_date|format:datetime} - start of day with formatting
        
        Возвращает формат ISO (YYYY-MM-DD HH:MM:SS), время 00:00:00.
        """
        return self._to_period_start(value, 'date')
    
    def modifier_to_hour(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of hour (minutes and seconds = 0): {field|to_hour}
        
        Examples:
        - {datetime|to_hour} - start of hour
        
        Возвращает формат ISO (YYYY-MM-DD HH:MM:SS).
        """
        return self._to_period_start(value, 'hour')
    
    def modifier_to_minute(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of minute (seconds = 0): {field|to_minute}
        
        Examples:
        - {datetime|to_minute} - start of minute
        
        Возвращает формат ISO (YYYY-MM-DD HH:MM:SS).
        """
        return self._to_period_start(value, 'minute')
    
    def modifier_to_second(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of second (microseconds = 0): {field|to_second}
        
        Examples:
        - {datetime|to_second} - start of second
        
        Возвращает формат ISO (YYYY-MM-DD HH:MM:SS).
        """
        return self._to_period_start(value, 'second')
    
    def modifier_to_week(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of week (Monday 00:00:00): {field|to_week}
        
        Examples:
        - {datetime|to_week} - start of week (Monday)
        
        Возвращает формат ISO (YYYY-MM-DD HH:MM:SS).
        """
        return self._to_period_start(value, 'week')
    
    def modifier_to_month(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of month (1st day, 00:00:00): {field|to_month}
        
        Examples:
        - {datetime|to_month} - start of month
        
        Возвращает формат ISO (YYYY-MM-DD HH:MM:SS).
        """
        return self._to_period_start(value, 'month')
    
    def modifier_to_year(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of year (January 1, 00:00:00): {field|to_year}
        
        Examples:
        - {datetime|to_year} - start of year
        
        Возвращает формат ISO (YYYY-MM-DD HH:MM:SS).
        """
        return self._to_period_start(value, 'year')
    
    def _to_period_start(self, value: Any, period: str) -> Union[str, Any]:
        """
        Internal method for converting date to period start
        
        Periods:
        - 'date' - start of day (00:00:00)
        - 'hour' - start of hour (minutes and seconds = 0)
        - 'minute' - start of minute (seconds = 0)
        - 'second' - start of second (microseconds = 0)
        - 'week' - start of week (Monday 00:00:00)
        - 'month' - start of month (1st day, 00:00:00)
        - 'year' - start of year (January 1, 00:00:00)
        """
        if not value:
            return value
        
        try:
            # Разбор входной даты
            dt, has_time = parse_datetime_value(value)
            if dt is None:
                self.logger.warning(f"Модификатор to_{period}: не удалось разобрать дату '{value}'")
                return value
            
            # Приведение к началу периода
            if period == 'date':
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'hour':
                dt = dt.replace(minute=0, second=0, microsecond=0)
            elif period == 'minute':
                dt = dt.replace(second=0, microsecond=0)
            elif period == 'second':
                dt = dt.replace(microsecond=0)
            elif period == 'week':
                # Начало недели (понедельник)
                days_since_monday = dt.weekday()  # 0 = понедельник, 6 = воскресенье
                dt = dt - timedelta(days=days_since_monday)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'month':
                dt = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'year':
                dt = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                self.logger.warning(f"Модификатор to_{period}: неизвестный период '{period}'")
                return value
            
            # Возврат в формате ISO (всегда с временем — начало периода)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        except Exception as e:
            self.logger.warning(f"Ошибка в модификаторе to_{period}: {e}")
            return value
