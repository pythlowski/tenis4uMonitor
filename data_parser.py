import json
from datetime import datetime, time, timedelta

from models.empty_slot import EmptySlot


class DataParser:

    def __init__(self):
        self.BEGIN_TIME: time = time(17, 0, 0)
        self.END_TIME: time = time(22, 30, 0)


    def parse_occupancy(self, raw_data: str, court_type: str) -> list[EmptySlot]:
        data = json.loads(raw_data)

        results = []

        for station in data.get("stations", []):
            if station.get("type") != court_type:
                continue

            for day in station.get("days", []):

                for free_slot in day.get("free_hours", []):
                    begin_date = self.parse_date(day["date"], free_slot['begin_time'])
                    end_date = self.parse_date(day["date"], free_slot['end_time'])

                    results += [
                        EmptySlot(courtName=station["name"], date=date) 
                        for date in self.get_acceptable_slots(begin_date, end_date)
                        ]

        return results


    def parse_date(self, date_str: str, time_str: str) -> datetime:
        return datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")


    def set_time_for_datetime(self, dt: datetime, t: time) -> datetime:
        return datetime.combine(dt.date(), t)


    def get_acceptable_slots(self, begin_date: datetime, end_date: datetime, duration_hours: int = 1) -> list[datetime]:
        slots = []

        acceptable_begin_date = self.set_time_for_datetime(begin_date, self.BEGIN_TIME)
        acceptable_end_date = self.set_time_for_datetime(end_date, self.END_TIME)

        current_begin_date = max(acceptable_begin_date, begin_date)
        max_end_date = min(acceptable_end_date, end_date)

        while current_begin_date + timedelta(hours=duration_hours) <= max_end_date:
            slots.append(current_begin_date)
            current_begin_date += timedelta(minutes=30)

        return slots

