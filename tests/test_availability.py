from datetime import datetime, time

import pytest

from availability import AvailabilityComputer, AvailabilityFilters, merge_intervals
from models.court_availability import CourtAvailability
from models.free_window import FreeWindow

MONDAY = (2026, 11, 23)
TUESDAY = (2026, 11, 24)


def dt(day, hour, minute=0):
    return datetime(*day, hour, minute)


def court(court_id, start, end):
    return CourtAvailability(court_id=court_id, court_name=f"Court {court_id}", start=start, end=end)


def compute(courts, **filters):
    defaults = dict(begin_time=time(16, 30), end_time=time(22, 30), min_duration_minutes=60)
    return AvailabilityComputer(AvailabilityFilters(**{**defaults, **filters})).compute(courts)


class TestClipping:
    def test_clips_to_begin_and_end_time(self):
        windows = compute([court("1", dt(MONDAY, 10), dt(MONDAY, 23, 30))])
        assert windows == [FreeWindow(dt(MONDAY, 16, 30), dt(MONDAY, 22, 30), "1")]

    def test_drops_interval_outside_hours(self):
        assert compute([court("1", dt(MONDAY, 10), dt(MONDAY, 16, 30))]) == []

    def test_midnight_end_is_clipped_to_end_time(self):
        windows = compute([court("1", dt(MONDAY, 21), dt(TUESDAY, 0))], min_duration_minutes=30)
        assert windows == [FreeWindow(dt(MONDAY, 21), dt(MONDAY, 22, 30), "1")]


class TestWeekdays:
    def test_filters_out_days_not_selected(self):
        courts = [court("1", dt(MONDAY, 17), dt(MONDAY, 19)), court("1", dt(TUESDAY, 17), dt(TUESDAY, 19))]
        windows = compute(courts, weekdays=("Tuesday",))
        assert [w.start for w in windows] == [dt(TUESDAY, 17)]

    def test_default_weekdays_include_saturday_and_sunday(self):
        assert {"Saturday", "Sunday"} <= set(AvailabilityFilters().weekdays)


class TestMerging:
    def test_merges_touching_and_overlapping_intervals_on_one_court(self):
        courts = [
            court("1", dt(MONDAY, 16, 30), dt(MONDAY, 17)),
            court("1", dt(MONDAY, 17), dt(MONDAY, 18)),
            court("1", dt(MONDAY, 17, 30), dt(MONDAY, 19)),
        ]
        assert compute(courts) == [FreeWindow(dt(MONDAY, 16, 30), dt(MONDAY, 19), "1")]

    def test_different_courts_are_not_merged(self):
        courts = [court("1", dt(MONDAY, 17), dt(MONDAY, 18)), court("2", dt(MONDAY, 18), dt(MONDAY, 19))]
        assert compute(courts) == [
            FreeWindow(dt(MONDAY, 17), dt(MONDAY, 18), "1"),
            FreeWindow(dt(MONDAY, 18), dt(MONDAY, 19), "2"),
        ]

    def test_gap_keeps_windows_separate(self):
        courts = [court("1", dt(MONDAY, 17), dt(MONDAY, 18)), court("1", dt(MONDAY, 19), dt(MONDAY, 20))]
        assert len(compute(courts)) == 2

    def test_merge_intervals_unsorted_input(self):
        spans = [(dt(MONDAY, 19), dt(MONDAY, 20)), (dt(MONDAY, 17), dt(MONDAY, 19, 30))]
        assert merge_intervals(spans) == [(dt(MONDAY, 17), dt(MONDAY, 20))]


class TestMinDuration:
    @pytest.mark.parametrize("minutes, kept", [(60, True), (59, False)])
    def test_boundary(self, minutes, kept):
        start = dt(MONDAY, 17)
        end = datetime(*MONDAY, 17 + minutes // 60, minutes % 60)
        assert bool(compute([court("1", start, end)])) is kept

    def test_applied_after_merging(self):
        courts = [court("1", dt(MONDAY, 17), dt(MONDAY, 17, 30)), court("1", dt(MONDAY, 17, 30), dt(MONDAY, 18))]
        assert compute(courts) == [FreeWindow(dt(MONDAY, 17), dt(MONDAY, 18), "1")]


def test_result_is_sorted_by_start_end_court():
    courts = [
        court("b", dt(TUESDAY, 17), dt(TUESDAY, 18)),
        court("b", dt(MONDAY, 17), dt(MONDAY, 18)),
        court("a", dt(MONDAY, 17), dt(MONDAY, 18)),
    ]
    assert [(w.start.day, w.court_id) for w in compute(courts)] == [(23, "a"), (23, "b"), (24, "b")]


def test_windows_carry_the_court_name():
    [window] = compute([court("1", dt(MONDAY, 17), dt(MONDAY, 18))])
    assert window.court_name == "Court 1"
    assert window.court_label == "Court 1"


def test_court_name_is_display_only():
    named = FreeWindow(dt(MONDAY, 17), dt(MONDAY, 18), "1", "Court 1")
    unnamed = FreeWindow(dt(MONDAY, 17), dt(MONDAY, 18), "1")
    assert named == unnamed and hash(named) == hash(unnamed)
    assert unnamed.court_label == "1"
