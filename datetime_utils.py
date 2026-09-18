import calendar
from datetime import datetime, time, timezone


class DatetimeUtils:
    @staticmethod
    def get_current_datetime() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def get_weekday(date: datetime) -> str:
        return calendar.day_name[date.weekday()]

    @staticmethod
    def set_time_for_datetime(dt: datetime, t: time) -> datetime:
        return datetime.combine(dt.date(), t)