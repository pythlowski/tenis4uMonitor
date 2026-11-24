from datetime import datetime, timezone

from models.facility_snapshot import FacilitySnapshot
from models.free_window import FreeWindow
from snapshots_repository import SnapshotRepository

WINDOW = FreeWindow(datetime(2026, 11, 23, 17), datetime(2026, 11, 23, 19), "Badminton 1")


def snap(key, windows=(WINDOW,)):
    return FacilitySnapshot(facility_key=key, taken_at=datetime(2026, 11, 23, 12, tzinfo=timezone.utc), windows=list(windows))


def test_round_trip(tmp_path):
    repo = SnapshotRepository(tmp_path)
    repo.save(snap("tenis4u_104"))

    loaded = repo.get("tenis4u_104")
    assert loaded == snap("tenis4u_104")
    assert isinstance(loaded.windows[0], FreeWindow)
    assert (tmp_path / "tenis4u_104.json").exists()


def test_missing_returns_none(tmp_path):
    assert SnapshotRepository(tmp_path).get("nope") is None


def test_facilities_are_kept_separate(tmp_path):
    repo = SnapshotRepository(tmp_path)
    repo.save(snap("a"))
    repo.save(snap("b", windows=()))
    assert repo.get("a").windows == [WINDOW]
    assert repo.get("b").windows == []


def test_unreadable_file_is_treated_as_missing(tmp_path):
    (tmp_path / "a.json").write_text("{not json", encoding="utf-8")
    assert SnapshotRepository(tmp_path).get("a") is None
