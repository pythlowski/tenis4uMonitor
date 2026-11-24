import json
from datetime import date, datetime, time
from types import SimpleNamespace

import pytest

from models.court_type import CourtType
from providers.twojtenis import (
    Booking,
    Location,
    TwojTenisProvider,
    compute_free,
    date_chunks,
    parse_bookings,
    parse_club,
    parse_open_hours,
    select_locations,
)
from tests.fakes import FakeHttp, fixture_text

CLUB_ID = "958662f0-0bd2-4fdc-8bef-bb2d69761adb"
CLUB_RAW = fixture_text("twojtenis_club.json")
BOOKINGS_RAW = fixture_text("twojtenis_bookings.json")
CLUB_URL = f"https://app-twojtenis-api-p-weu.azurewebsites.net/api/v1/Clubs/{CLUB_ID}"
BOOKINGS_URL = f"https://app-twojtenis-tech-krakow-api-p-weu.azurewebsites.net/api/v1/Clubs/{CLUB_ID}/bookings/public"

MONDAY = date(2026, 11, 23)
ALL_DAY = {k: (time(7), time(23)) for k in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")}


def dt(hour, minute=0, day=MONDAY):
    return datetime.combine(day, time(hour, minute))


def loc(id="L1", type=1, open_hours=None, enabled=True):
    return Location(id=id, name=f"Court {id}", type=type, open_hours=open_hours or {}, is_enabled=enabled)


def free(locations, bookings, club_hours=ALL_DAY, date_from=MONDAY, date_to=MONDAY):
    return [(c.court_id, c.start, c.end) for c in compute_free(locations, bookings, club_hours, date_from, date_to)]


def facility(court_type=CourtType.BADMINTON):
    return SimpleNamespace(facility_id=CLUB_ID, court_type=court_type)


class TestParsing:
    def test_parse_club_locations_and_hours(self):
        club = parse_club(CLUB_RAW)
        assert club.id == CLUB_ID
        assert club.open_hours["monday"] == (time(7), time(23))
        names = {l.name for l in club.locations}
        assert {"Badminton 1", "Tenis 1", "Padel 1", "Boisko 90m x 45m"} <= names
        pitch = next(l for l in club.locations if l.type == 5)
        assert pitch.open_hours["monday"] == (time(7), time(22))

    def test_parse_open_hours_skips_closed_days_and_handles_end_of_day(self):
        hours = parse_open_hours({
            "Monday": {"from": "08:00:00", "to": "24:00:00"},
            "tuesday": None,
            "wednesday": {"from": None, "to": None},
        })
        assert hours == {"monday": (time(8), None)}

    def test_parse_bookings(self):
        bookings = parse_bookings(BOOKINGS_RAW)
        assert len(bookings) == 20
        assert all(b.start.date() == MONDAY for b in bookings)

    def test_booking_ending_at_midnight(self):
        raw = json.dumps([{"date": "2026-11-23", "startTime": "22:00:00", "endTime": "00:00:00", "locationId": "L1"}])
        [booking] = parse_bookings(raw)
        assert booking.end == datetime(2026, 11, 24, 0, 0)


class TestSelectLocations:
    def test_maps_types(self):
        club = parse_club(CLUB_RAW)
        assert {l.name for l in select_locations(club, CourtType.BADMINTON)} == {f"Badminton {i}" for i in range(1, 5)}
        assert {l.name for l in select_locations(club, CourtType.TENNIS)} == {f"Tenis {i}" for i in range(1, 6)}
        assert {l.name for l in select_locations(club, CourtType.PADEL)} == {f"Padel {i}" for i in range(1, 5)}

    def test_unknown_type_and_disabled_are_ignored(self):
        club = SimpleNamespace(locations=[loc("a", type=5), loc("b", type=1, enabled=False), loc("c", type=1)])
        assert [l.id for l in select_locations(club, CourtType.BADMINTON)] == ["c"]


class TestComputeFree:
    def test_no_bookings_gives_full_opening_hours(self):
        assert free([loc()], []) == [("L1", dt(7), dt(23))]

    def test_booking_in_the_middle_splits_window(self):
        assert free([loc()], [Booking("L1", dt(17), dt(18))]) == [("L1", dt(7), dt(17)), ("L1", dt(18), dt(23))]

    def test_overlapping_and_touching_bookings(self):
        bookings = [Booking("L1", dt(17), dt(18, 30)), Booking("L1", dt(18), dt(19)), Booking("L1", dt(19), dt(20))]
        assert free([loc()], bookings) == [("L1", dt(7), dt(17)), ("L1", dt(20), dt(23))]

    def test_bookings_at_and_beyond_opening_edges_are_clipped(self):
        bookings = [Booking("L1", dt(6), dt(8)), Booking("L1", dt(22), datetime(2026, 11, 24, 0, 0))]
        assert free([loc()], bookings) == [("L1", dt(8), dt(22))]

    def test_bookings_of_other_locations_are_ignored(self):
        assert free([loc("L1")], [Booking("L2", dt(7), dt(23))]) == [("L1", dt(7), dt(23))]

    def test_location_hours_override_club_hours(self):
        location = loc(open_hours={"monday": (time(9), time(22))})
        assert free([location], []) == [("L1", dt(9), dt(22))]

    def test_falls_back_to_club_hours_per_weekday(self):
        location = loc(open_hours={"tuesday": (time(9), time(22))})
        assert free([location], []) == [("L1", dt(7), dt(23))]

    def test_weekday_without_hours_is_skipped(self):
        assert free([loc()], [], club_hours={"tuesday": (time(7), time(23))}) == []

    def test_end_of_day_closing(self):
        assert free([loc()], [], club_hours={"monday": (time(20), None)}) == [("L1", dt(20), datetime(2026, 11, 24))]
        assert free([loc()], [], club_hours={"monday": (time(20), time(0))}) == [("L1", dt(20), datetime(2026, 11, 24))]

    def test_multiple_days(self):
        tuesday = date(2026, 11, 24)
        result = free([loc()], [Booking("L1", dt(7, day=tuesday), dt(22, day=tuesday))], date_to=tuesday)
        assert result == [("L1", dt(7), dt(23)), ("L1", dt(22, day=tuesday), dt(23, day=tuesday))]

    def test_fixture_end_to_end(self):
        club = parse_club(CLUB_RAW)
        locations = select_locations(club, CourtType.BADMINTON)
        result = compute_free(locations, parse_bookings(BOOKINGS_RAW), club.open_hours, MONDAY, MONDAY)
        by_name = {}
        for c in result:
            by_name.setdefault(c.court_name, []).append((c.start.time(), c.end.time()))
        assert by_name["Badminton 1"] == [(time(7), time(15)), (time(17), time(18))]
        assert by_name["Badminton 4"] == [(time(8), time(13, 30)), (time(15, 30), time(18))]


class TestDateChunks:
    def test_seven_days_is_one_chunk(self):
        assert date_chunks(date(2026, 11, 24), date(2026, 11, 30)) == [(date(2026, 11, 24), date(2026, 11, 30))]

    def test_ten_days_is_two_chunks_of_at_most_seven(self):
        chunks = date_chunks(date(2026, 11, 24), date(2026, 12, 3))
        assert chunks == [(date(2026, 11, 24), date(2026, 11, 30)), (date(2026, 12, 1), date(2026, 12, 3))]
        assert all((end - start).days + 1 <= 7 for start, end in chunks)

    def test_single_day(self):
        assert date_chunks(MONDAY, MONDAY) == [(MONDAY, MONDAY)]


class TestProvider:
    def _provider(self, clock=None):
        http = FakeHttp({CLUB_URL: CLUB_RAW, BOOKINGS_URL: BOOKINGS_RAW})
        provider = TwojTenisProvider(http, clock=clock or (lambda: 0.0))
        return provider, http

    def test_requests_go_to_their_hosts_with_chunked_ranges(self):
        provider, http = self._provider()
        provider.fetch_availability(facility(), date(2026, 11, 23), date(2026, 12, 2))

        urls = [c["url"] for c in http.calls]
        assert urls == [CLUB_URL, BOOKINGS_URL, BOOKINGS_URL]
        assert [c["params"] for c in http.calls[1:]] == [
            {"from": "2026-11-23", "to": "2026-11-29"},
            {"from": "2026-11-30", "to": "2026-12-02"},
        ]

    def test_returns_free_intervals_for_requested_type(self):
        provider, _ = self._provider()
        courts = provider.fetch_availability(facility(), MONDAY, MONDAY)
        assert {c.court_name for c in courts} == {f"Badminton {i}" for i in range(1, 5)}

    def test_club_is_cached_between_runs(self):
        provider, http = self._provider()
        provider.fetch_availability(facility(), MONDAY, MONDAY)
        provider.fetch_availability(facility(), MONDAY, MONDAY)
        assert [c["url"] for c in http.calls].count(CLUB_URL) == 1

    def test_club_is_refetched_after_ttl(self):
        now = [0.0]
        provider, http = self._provider(clock=lambda: now[0])
        provider.fetch_availability(facility(), MONDAY, MONDAY)
        now[0] = 24 * 60 * 60 + 1
        provider.fetch_availability(facility(), MONDAY, MONDAY)
        assert [c["url"] for c in http.calls].count(CLUB_URL) == 2

    def test_stale_club_is_used_when_refresh_fails(self):
        now = [0.0]
        provider, http = self._provider(clock=lambda: now[0])
        provider.fetch_availability(facility(), MONDAY, MONDAY)
        now[0] = 24 * 60 * 60 + 1
        http.routes[CLUB_URL] = RuntimeError("down")
        assert provider.fetch_availability(facility(), MONDAY, MONDAY)

    def test_club_error_without_cache_raises(self):
        http = FakeHttp({CLUB_URL: RuntimeError("down")})
        with pytest.raises(RuntimeError):
            TwojTenisProvider(http).fetch_availability(facility(), MONDAY, MONDAY)

    def test_booking_url(self):
        provider, _ = self._provider()
        assert provider.booking_url(facility()) == f"https://app.twojtenis.pl/#/clubs/{CLUB_ID}?tab=bookings"
