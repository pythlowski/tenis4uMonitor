import datetime
from unittest.mock import patch

import pytest

from models.court_availability import CourtAvailability
from monitor_service import MonitorService
from snapshots_repository import SnapshotRepository

TWO_FACILITIES = """
days_ahead = 3

[discord]
mode = "global"

[[facilities]]
key = "good"
name = "Good"
provider = "tenis4u"
facility_id = "1"
court_type = "badminton"

[[facilities]]
key = "broken"
name = "Broken"
provider = "tenis4u"
facility_id = "2"
court_type = "badminton"
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeProvider:
    def __init__(self, courts=None, error=None, booking="https://book"):
        self.courts = courts or []
        self.error = error
        self.booking = booking
        self.calls = []

    def fetch_availability(self, facility, date_from, date_to):
        self.calls.append((facility.key, date_from, date_to))
        if self.error:
            raise self.error
        return self.courts

    def booking_url(self, facility):
        return self.booking


class FakeDispatcher:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, results):
        self.dispatched.append(results)


@pytest.fixture
def make_service(make_settings):
    def factory(interval_minutes: int = 20) -> MonitorService:
        """Return a MonitorService with an isolated Settings object and no network."""
        settings = make_settings(fetch_interval_minutes=interval_minutes)
        return MonitorService(settings, providers={}, dispatcher=FakeDispatcher())

    return factory


def _frozen_datetime(minute: int, second: int = 0, microsecond: int = 0):
    """Return a context manager that freezes datetime.datetime.now() to the
    given time while keeping all other datetime functionality intact."""
    fixed = datetime.datetime(2026, 9, 23, 10, minute, second, microsecond)

    class _FakeDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    return patch("monitor_service.datetime.datetime", _FakeDatetime)


# ---------------------------------------------------------------------------
# run_once
# ---------------------------------------------------------------------------

COURT = CourtAvailability("c1", "Badminton 1", datetime.datetime(2026, 11, 23, 17), datetime.datetime(2026, 11, 23, 19))
TODAY = datetime.date(2026, 11, 23)


@pytest.fixture
def run_once_service(make_settings, tmp_path):
    def factory(good=None, broken=None):
        settings = make_settings(TWO_FACILITIES)
        # route the second facility to its own fake provider instance
        settings.facilities[1].provider = "fake_broken"
        good = good or FakeProvider([COURT])
        broken = broken or FakeProvider(error=RuntimeError("API down"))
        dispatcher = FakeDispatcher()
        service = MonitorService(
            settings,
            providers={"tenis4u": good, "fake_broken": broken},
            repository=SnapshotRepository(tmp_path),
            dispatcher=dispatcher,
            today=lambda: TODAY,
        )
        return service, dispatcher, good, broken

    return factory


class TestRunOnce:
    def test_failing_facility_does_not_stop_others_and_keeps_its_snapshot(self, run_once_service, tmp_path):
        service, dispatcher, _, _ = run_once_service()
        (tmp_path / "broken.json").write_text("previous", encoding="utf-8")

        results = service.run_once()

        assert [r.facility.key for r in results] == ["good"]
        assert dispatcher.dispatched == [results]
        assert (tmp_path / "broken.json").read_text(encoding="utf-8") == "previous"
        assert (tmp_path / "good.json").exists()

    def test_date_range_follows_days_ahead(self, run_once_service):
        service, _, good, _ = run_once_service()
        service.run_once()
        assert good.calls == [("good", TODAY, datetime.date(2026, 11, 25))]

    def test_first_run_is_baseline_then_unchanged(self, run_once_service):
        service, dispatcher, _, _ = run_once_service()

        [first] = service.run_once()
        [second] = service.run_once()

        assert first.is_baseline and first.changed and first.new_windows == []
        assert not second.is_baseline and not second.changed

    def test_new_window_after_baseline(self, run_once_service):
        good = FakeProvider([COURT])
        service, _, _, _ = run_once_service(good=good)
        service.run_once()

        extra = CourtAvailability("c2", "Badminton 2", COURT.start, COURT.end)
        good.courts = [COURT, extra]
        [result] = service.run_once()

        assert [w.court_id for w in result.new_windows] == ["c2"]
        assert result.changed

    def test_booking_url_from_provider_or_override(self, run_once_service):
        service, _, _, _ = run_once_service()
        [result] = service.run_once()
        assert result.booking_url == "https://book"

        service.settings.facilities[0].booking_url = "https://override"
        [result] = service.run_once()
        assert result.booking_url == "https://override"

    def test_nothing_dispatched_when_every_facility_fails(self, run_once_service):
        service, dispatcher, _, _ = run_once_service(good=FakeProvider(error=RuntimeError("x")))
        assert service.run_once() == []
        assert dispatcher.dispatched == []


# ---------------------------------------------------------------------------
# _seconds_until_next_slot
# ---------------------------------------------------------------------------

class TestSecondsUntilNextSlot:
    """Test MonitorService._seconds_until_next_slot with a 20-minute interval.

    Scheduled boundaries for a 20-min interval (1200 s) are:
        XX:00:00, XX:20:00, XX:40:00
    """

    @pytest.fixture(autouse=True)
    def _factory(self, make_service):
        self.make_service = make_service

    def _seconds(self, minute, second=0, microsecond=0, interval=20):
        svc = self.make_service(interval_minutes=interval)
        with _frozen_datetime(minute, second, microsecond):
            return svc._seconds_until_next_slot()

    # --- exactly on a boundary ---

    def test_returns_full_interval_when_exactly_on_boundary(self):
        # 10:00:00 — elapsed_in_hour == 0 → remainder == 0 → returns full interval
        result = self._seconds(minute=0, second=0)
        assert result == 20 * 60

    def test_returns_full_interval_when_on_second_boundary(self):
        # 10:20:00 — elapsed_in_hour == 1200 → remainder == 0
        result = self._seconds(minute=20, second=0)
        assert result == 20 * 60

    # --- one second past a boundary ---

    def test_returns_interval_minus_one_second_after_boundary(self):
        # 10:00:01 → elapsed = 1 → remainder = 1 → wait = 1199 s
        result = self._seconds(minute=0, second=1)
        assert result == pytest.approx(20 * 60 - 1, abs=1e-3)

    # --- halfway through an interval ---

    def test_returns_half_interval_at_midpoint(self):
        # 10:10:00 → elapsed = 600 → remainder = 600 → wait = 600 s
        result = self._seconds(minute=10, second=0)
        assert result == pytest.approx(600, abs=1e-3)

    # --- one second before the next boundary ---

    def test_returns_one_second_just_before_boundary(self):
        # 10:19:59 → elapsed = 1199 → remainder = 1199 → wait = 1 s
        result = self._seconds(minute=19, second=59)
        assert result == pytest.approx(1, abs=1e-3)

    # --- sub-second precision ---

    def test_fractional_seconds_accounted_for(self):
        # 10:00:00.500000 → elapsed = 0.5 → remainder = 0.5 → wait = 1199.5 s
        result = self._seconds(minute=0, second=0, microsecond=500_000)
        assert result == pytest.approx(20 * 60 - 0.5, abs=1e-3)

    # --- different interval ---

    def test_respects_30_minute_interval(self):
        # Interval = 30 min (1800 s). At 10:15:00 → elapsed = 900 → remainder = 900 → wait = 900 s
        result = self._seconds(minute=15, second=0, interval=30)
        assert result == pytest.approx(900, abs=1e-3)

    def test_respects_60_minute_interval(self):
        # Interval = 60 min (3600 s). At 10:45:00 → elapsed = 2700 → remainder = 2700 → wait = 900 s
        result = self._seconds(minute=45, second=0, interval=60)
        assert result == pytest.approx(900, abs=1e-3)


class TestProxyRouting:
    def test_only_tenis4u_goes_through_the_proxy_pool(self, make_settings):
        with patch("monitor_service.ProxyBackgroundService") as proxy_service:
            service = MonitorService(make_settings(TWO_FACILITIES))
            twojtenis = service._provider("twojtenis")
            assert twojtenis.http.proxy_service is None
            proxy_service.assert_not_called()  # the pool is not even started without a proxied provider

            tenis4u = service._provider("tenis4u")
            assert tenis4u.http.proxy_service is proxy_service.return_value
            proxy_service.assert_called_once()
