from datetime import datetime

import pytest

from models.facility_snapshot import FacilitySnapshot
from models.free_window import FreeWindow
from snapshots_comparator import SnapshotsComparator


def w(start, end, court="1"):
    return FreeWindow(datetime(2026, 11, 23, *start), datetime(2026, 11, 23, *end), court)


def snap(*windows):
    return FacilitySnapshot(facility_key="f", taken_at=datetime(2026, 11, 23, 12), windows=list(windows))


@pytest.fixture
def comparator():
    return SnapshotsComparator()


def test_no_change(comparator):
    diff = comparator.get_diff(snap(w((17,), (19,))), snap(w((17,), (19,))))
    assert not diff.changed and diff.new_windows == [] and not diff.is_baseline


def test_new_window(comparator):
    new = w((20,), (21,))
    diff = comparator.get_diff(snap(w((17,), (19,))), snap(w((17,), (19,)), new))
    assert diff.changed and diff.new_windows == [new]


def test_grown_window_is_new(comparator):
    grown = w((17,), (20,))
    diff = comparator.get_diff(snap(w((17,), (19,))), snap(grown))
    assert diff.new_windows == [grown]


def test_shrunk_window_is_changed_but_not_new(comparator):
    diff = comparator.get_diff(snap(w((17,), (20,))), snap(w((17, 30), (19,))))
    assert diff.changed and diff.new_windows == []


def test_another_court_for_same_range_is_new(comparator):
    other = w((17,), (19,), court="2")
    diff = comparator.get_diff(snap(w((17,), (19,))), snap(w((17,), (19,)), other))
    assert diff.new_windows == [other]


def test_court_a_does_not_cover_court_b(comparator):
    b = w((17, 30), (18, 30), court="B")
    diff = comparator.get_diff(snap(w((16,), (22,), court="A")), snap(b))
    assert diff.new_windows == [b]


def test_removed_window(comparator):
    diff = comparator.get_diff(snap(w((17,), (19,)), w((20,), (21,))), snap(w((17,), (19,))))
    assert diff.changed and diff.new_windows == []


def test_taken_at_is_ignored(comparator):
    old = snap(w((17,), (19,)))
    new = old.model_copy(update={"taken_at": datetime(2026, 11, 24)})
    assert not comparator.get_diff(old, new).changed


def test_missing_old_snapshot_is_a_silent_baseline(comparator):
    diff = comparator.get_diff(None, snap(w((17,), (19,))))
    assert diff.is_baseline and diff.changed and diff.new_windows == []
