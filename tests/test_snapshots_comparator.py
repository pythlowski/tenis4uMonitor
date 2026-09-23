from datetime import datetime
from dataclasses import replace

from models.free_slot import FreeSlot
from models.snapshot import Snapshot
from snapshots_comparator import SnapshotsComparator

snapshots_comparator = SnapshotsComparator()

free_slots = [
    FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 23, 19, 00)),
    FreeSlot(courtName="badminton 2", date=datetime(2026, 9, 23, 19, 30))
]

def test_get_diff_returns_not_equal_and_identifies_new_slots_when_snapshot_grows():
    snapshot1 = Snapshot(free_slots=free_slots)
    snapshot2 = Snapshot(free_slots=[*free_slots, FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 23, 20, 00))])

    snapshots_diff = snapshots_comparator.get_diff(snapshot1, snapshot2)

    assert snapshots_diff.are_equal == False
    assert len(snapshots_diff.new_slots) == 1

def test_get_diff_returns_equal_and_identifies_no_new_slots_when_snapshots_have_the_same_slots():
    snapshot1 = Snapshot(free_slots=free_slots)
    snapshot2 = Snapshot(free_slots=free_slots)

    snapshots_diff = snapshots_comparator.get_diff(snapshot1, snapshot2)

    assert snapshots_diff.are_equal == True
    assert len(snapshots_diff.new_slots) == 0

def test_get_diff_returns_not_equal_and_identifies_no_new_slots_when_snapshot_shrinks():
    snapshot1 = Snapshot(free_slots=[*free_slots, FreeSlot(courtName="badminton 1", date=datetime(2026, 9, 23, 20, 00))])
    snapshot2 = Snapshot(free_slots=free_slots)

    snapshots_diff = snapshots_comparator.get_diff(snapshot1, snapshot2)

    assert snapshots_diff.are_equal == False
    assert len(snapshots_diff.new_slots) == 0

def test_get_diff_returns_not_equal_and_identifies_new_slots_when_snapshot_slots_have_same_dates_but_different_court_names():
    snapshot1 = Snapshot(free_slots=free_slots)
    snapshot2 = Snapshot(free_slots=[replace(slot, courtName="badminton2") for slot in free_slots])

    snapshots_diff = snapshots_comparator.get_diff(snapshot1, snapshot2)

    assert snapshots_diff.are_equal == False
    assert len(snapshots_diff.new_slots) == 2

def test_get_diff_returns_not_equal_and_identifies_new_slots_when_snapshot_slots_have_same_court_names_but_different_dates():
    snapshot1 = Snapshot(free_slots=free_slots)
    snapshot2 = Snapshot(free_slots=[replace(slot, date=datetime(2026, 9, 23, 20, 00)) for slot in free_slots])

    snapshots_diff = snapshots_comparator.get_diff(snapshot1, snapshot2)

    assert snapshots_diff.are_equal == False
    assert len(snapshots_diff.new_slots) == 2