import calendar
import datetime


class DatetimeUtils:
    @staticmethod
    def get_current_datetime() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    @staticmethod
    def get_weekday(date: datetime) -> str:
        return calendar.day_name[date.weekday()]