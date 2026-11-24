import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from models.court_availability import CourtAvailability
from models.free_window import FreeWindow

ALL_WEEKDAYS: tuple[str, ...] = tuple(calendar.day_name)
WINDOW_STEP = timedelta(minutes=30)  # windows start every 30 minutes within a free span


@dataclass(frozen=True)
class AvailabilityFilters:
    begin_time: time = time(16, 30)
    end_time: time = time(22, 30)
    duration_minutes: int = 60  # every window is exactly this long
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

        duration = timedelta(minutes=self.filters.duration_minutes)
        windows = [
            FreeWindow(start=start, end=end, court_id=court_id, court_name=names[court_id])
            for (court_id, _), spans in intervals.items()
            for span in merge_intervals(spans)
            for start, end in split_into_windows(span, duration)
        ]
        return sorted(windows)


def split_into_windows(
    span: tuple[datetime, datetime], duration: timedelta, step: timedelta = WINDOW_STEP
) -> list[tuple[datetime, datetime]]:
    """Every window of exactly `duration` inside the span, starting at the span start and then every `step`.

    16:00–18:00 with 60 minutes -> 16:00–17:00, 16:30–17:30, 17:00–18:00.
    """
    span_start, span_end = span
    windows = []
    start = span_start
    while start + duration <= span_end:
        windows.append((start, start + duration))
        start += step
    return windows


def merge_intervals(spans: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Union overlapping or touching intervals."""
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged

