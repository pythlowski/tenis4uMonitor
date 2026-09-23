import datetime
from unittest.mock import patch

import pytest

from monitor_service import MonitorService
from settings import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(interval_minutes: int = 20) -> MonitorService:
    """Return a MonitorService with a minimal faked Settings object."""
    settings = Settings()
    settings.api.fetch_interval_minutes = interval_minutes
    return MonitorService(settings)


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
# _seconds_until_next_slot
# ---------------------------------------------------------------------------

class TestSecondsUntilNextSlot:
    """Test MonitorService._seconds_until_next_slot with a 20-minute interval.

    Scheduled boundaries for a 20-min interval (1200 s) are:
        XX:00:00, XX:20:00, XX:40:00
    """

    def _seconds(self, minute, second=0, microsecond=0, interval=20):
        svc = _make_service(interval_minutes=interval)
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
