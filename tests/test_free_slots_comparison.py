from datetime import datetime

from models.free_slot import FreeSlot

def test_free_slot_equal_returns_true_when_court_name_and_dates_are_equal():
    slot1 = FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 19, 19, 30))
    slot2 = FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 19, 19, 30))

    assert slot1 == slot2

def test_free_slot_equal_returns_false_when_dates_are_equal_and_court_names_are_not_equal():
    slot1 = FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 19, 19, 30))
    slot2 = FreeSlot(courtName="badminton 2", date=datetime(2026, 9, 19, 19, 30))

    assert slot1 != slot2

def test_free_slot_equal_returns_false_when_both_dates_and_court_names_are_not_equal():
    slot1 = FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 19, 19, 00))
    slot2 = FreeSlot(courtName="badminton 2", date=datetime(2026, 9, 19, 19, 30))

    assert slot1 != slot2

def test_free_slot_less_than_prioritizes_earlier_date_over_court_name():
    slot1 = FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 23, 19, 00))
    slot2 = FreeSlot(courtName="badminton 2", date=datetime(2026, 9, 23, 19, 00))

    assert slot1 < slot2

def test_free_slot_less_than_prioritizes_earlier_date_over_court_name():
    slot1 = FreeSlot(courtName="badminton 2", date=datetime(2026, 9, 23, 19, 00))
    slot2 = FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 23, 20, 00))

    assert slot1 < slot2

