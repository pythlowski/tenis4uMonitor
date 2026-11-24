import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from models.court_availability import CourtAvailability
from models.free_window import FreeWindow

ALL_WEEKDAYS: tuple[str, ...] = tuple(calendar.day_name)


@dataclass(frozen=True)
class AvailabilityFilters:
    begin_time: time = time(16, 30)
    end_time: time = time(22, 30)
    min_duration_minutes: int = 60
    weekdays: tuple[str, ...] = field(default=ALL_WEEKDAYS)


class AvailabilityComputer:
    def __init__(self, filters: AvailabilityFilters):
        self.filters = filters

    def compute(self, courts: list[CourtAvailability]) -> list[FreeWindow]:
        intervals: dict[tuple[str, object], list[tuple[datetime, datetime]]] = defaultdict(list)
        names: dict[str, str] = {}

        for court in courts:
            day = court.start.date()
            if calendar.day_name[day.weekday()] not in self.filters.weekdays:
                continue
            start = max(court.start, datetime.combine(day, self.filters.begin_time))
            end = min(court.end, datetime.combine(day, self.filters.end_time))
            if start >= end:
                continue
            intervals[(court.court_id, day)].append((start, end))
            names[court.court_id] = court.court_name

        min_duration = timedelta(minutes=self.filters.min_duration_minutes)
        windows = [
            FreeWindow(start=start, end=end, court_id=court_id, court_name=names[court_id])
            for (court_id, _), spans in intervals.items()
            for start, end in merge_intervals(spans)
            if end - start >= min_duration
        ]
        return sorted(windows)


def merge_intervals(spans: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Union overlapping or touching intervals."""
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged

