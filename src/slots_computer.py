import json
from datetime import datetime, time, timedelta

from datetime_utils import DatetimeUtils
from models.free_slot import FreeSlot


class SlotsComputer:

    def __init__(self, court_type: str, begin_time: time, end_time: time, days_of_week: list[str]):
        self.court_type = court_type
        self.begin_time = begin_time
        self.end_time = end_time
        self.days_of_week = days_of_week


    def compute(self, raw_data: str) -> list[FreeSlot]:
        data = json.loads(raw_data)

        results = []

        for station in data.get("stations", []):
            if station.get("type") != self.court_type:
                continue

            for day in station.get("days", []):

                for free_slot in day.get("free_hours", []):
                    begin_date = self._parse_date(day["date"], free_slot['begin_time'])
                    end_date = self._parse_date(day["date"], free_slot['end_time'])

                    results += [
                        FreeSlot(courtName=station["name"], date=date) 
                        for date in self._get_acceptable_slots(begin_date, end_date, duration_hours=1)
                    ]

        return results


    def _parse_date(self, date_str: str, time_str: str) -> datetime:
        return datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")


    def _get_acceptable_slots(self, begin_date: datetime, end_date: datetime, duration_hours: int = 1) -> list[datetime]:
        slots = []

        acceptable_begin_date = DatetimeUtils.set_time_for_datetime(begin_date, self.begin_time)
        acceptable_end_date = DatetimeUtils.set_time_for_datetime(end_date, self.end_time)

        current_begin_date = max(acceptable_begin_date, begin_date)
        max_end_date = min(acceptable_end_date, end_date)

        while current_begin_date + timedelta(hours=duration_hours) <= max_end_date:
            slots.append(current_begin_date)
            current_begin_date += timedelta(minutes=30)

        return slots

