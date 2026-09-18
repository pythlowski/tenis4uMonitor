from datetime import datetime, time

from slots_computer import SlotsComputer

computer = SlotsComputer("badminton", time(17, 0), time(22, 30), ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"])
YEAR = 2026
MONTH = 9
DAY = 10

def test_returns_empty_when_interval_is_outside_allowed_window():
    slots = computer._get_acceptable_slots(datetime(YEAR, MONTH, DAY, 14, 0), datetime(YEAR, MONTH, DAY, 16, 30))
    assert slots == []

def test_clips_start_and_end_to_working_day_bounds():
    slots = computer._get_acceptable_slots(datetime(YEAR, MONTH, DAY, 16, 30), datetime(YEAR, MONTH, DAY, 23, 0))
    assert slots == [
        datetime(YEAR, MONTH, DAY, 17, 0), 
        datetime(YEAR, MONTH, DAY, 17, 30), 
        datetime(YEAR, MONTH, DAY, 18, 0), 
        datetime(YEAR, MONTH, DAY, 18, 30),
        datetime(YEAR, MONTH, DAY, 19, 0), 
        datetime(YEAR, MONTH, DAY, 19, 30), 
        datetime(YEAR, MONTH, DAY, 20, 0), 
        datetime(YEAR, MONTH, DAY, 20, 30),
        datetime(YEAR, MONTH, DAY, 21, 0), 
        datetime(YEAR, MONTH, DAY, 21, 30),
    ]

def test_returns_empty_when_requested_duration_is_longer_than_interval():
    slots = computer._get_acceptable_slots(datetime(YEAR, MONTH, DAY, 17, 0), datetime(YEAR, MONTH, DAY, 17, 30), duration_hours=1)
    assert slots == []

def test_returns_empty_when_only_acceptable_slots_are_too_short():
    slots = computer._get_acceptable_slots(datetime(YEAR, MONTH, DAY, 15, 0), datetime(YEAR, MONTH, DAY, 17, 30), duration_hours=1)
    assert slots == []

def test_honors_custom_duration_hours_when_fit_is_possible():
    slots = computer._get_acceptable_slots(datetime(YEAR, MONTH, DAY, 17, 0), datetime(YEAR, MONTH, DAY, 20, 0), duration_hours=2)
    assert slots == [
        datetime(YEAR, MONTH, DAY, 17, 0), 
        datetime(YEAR, MONTH, DAY, 17, 30), 
        datetime(YEAR, MONTH, DAY, 18, 0)
    ]

def test_returns_empty_when_begin_is_after_end():
    slots = computer._get_acceptable_slots(datetime(YEAR, MONTH, DAY, 21, 0), datetime(YEAR, MONTH, DAY, 20, 0))
    assert slots == []
