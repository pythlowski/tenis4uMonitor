import unittest
from datetime import datetime, time

from slots_computer import SlotsComputer


class TestSlotsComputer(unittest.TestCase):
    def setUp(self):
        self.computer = SlotsComputer("badminton", time(17, 0), time(22, 30), ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"])
        self.YEAR = 2026
        self.MONTH = 9
        self.DAY = 10

    def test_returns_empty_when_interval_is_outside_allowed_window(self):
        slots = self.computer._get_acceptable_slots(datetime(self.YEAR, self.MONTH, self.DAY, 14, 0), datetime(self.YEAR, self.MONTH, self.DAY, 16, 30))
        self.assertEqual(slots, [])

    def test_clips_start_and_end_to_working_day_bounds(self):
        slots = self.computer._get_acceptable_slots(datetime(self.YEAR, self.MONTH, self.DAY, 16, 30), datetime(self.YEAR, self.MONTH, self.DAY, 23, 0))
        self.assertEqual(slots, [
            datetime(self.YEAR, self.MONTH, self.DAY, 17, 0), 
            datetime(self.YEAR, self.MONTH, self.DAY, 17, 30), 
            datetime(self.YEAR, self.MONTH, self.DAY, 18, 0), 
            datetime(self.YEAR, self.MONTH, self.DAY, 18, 30),
            datetime(self.YEAR, self.MONTH, self.DAY, 19, 0), 
            datetime(self.YEAR, self.MONTH, self.DAY, 19, 30), 
            datetime(self.YEAR, self.MONTH, self.DAY, 20, 0), 
            datetime(self.YEAR, self.MONTH, self.DAY, 20, 30),
            datetime(self.YEAR, self.MONTH, self.DAY, 21, 0), 
            datetime(self.YEAR, self.MONTH, self.DAY, 21, 30),
        ])

    def test_returns_empty_when_requested_duration_is_longer_than_interval(self):
        slots = self.computer._get_acceptable_slots(datetime(self.YEAR, self.MONTH, self.DAY, 17, 0), datetime(self.YEAR, self.MONTH, self.DAY, 17, 30), duration_hours=1)
        self.assertEqual(slots, [])
    
    def test_returns_empty_when_only_acceptable_slots_are_too_short(self):
        slots = self.computer._get_acceptable_slots(datetime(self.YEAR, self.MONTH, self.DAY, 15, 0), datetime(self.YEAR, self.MONTH, self.DAY, 17, 30), duration_hours=1)
        self.assertEqual(slots, [])

    def test_honors_custom_duration_hours_when_fit_is_possible(self):
        slots = self.computer._get_acceptable_slots(datetime(self.YEAR, self.MONTH, self.DAY, 17, 0), datetime(self.YEAR, self.MONTH, self.DAY, 20, 0), duration_hours=2)
        self.assertEqual(slots, [
            datetime(self.YEAR, self.MONTH, self.DAY, 17, 0), 
            datetime(self.YEAR, self.MONTH, self.DAY, 17, 30), 
            datetime(self.YEAR, self.MONTH, self.DAY, 18, 0)
        ])

    def test_returns_empty_when_begin_is_after_end(self):
        slots = self.computer._get_acceptable_slots(datetime(self.YEAR, self.MONTH, self.DAY, 21, 0), datetime(self.YEAR, self.MONTH, self.DAY, 20, 0))
        self.assertEqual(slots, [])
