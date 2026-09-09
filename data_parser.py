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
                date = day["date"].replace("/", "-")

                for free_slot in day.get("free_hours", []):
                    begin_date = self.parse_time(date, free_slot['begin_time'])
                    end_date = self.parse_time(date, free_slot['end_time'])

                    results += [
                        EmptySlot(courtName=station["name"], date=date) 
                        for date in self.get_acceptable_slots(begin_date, end_date)
                        ]

        return results


    def parse_time(self, time_str: str) -> time:
        return datetime.strptime(time_str, "%H:%M:%S").time()


    def get_acceptable_slots(self, begin_time: time, end_time: time, duration_hours: int = 1) -> list[time]:
        slots = []
        current_begin_time = max(self.BEGIN_TIME, begin_time)
        max_end_time = min(end_time, self.END_TIME)
        
        while current_begin_time + timedelta(hours=duration_hours) <= max_end_time:
            slots.append(current_begin_time)
            current_begin_time += timedelta(minutes=30)

        return slots

