import json
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from models.court_type import CourtType
from providers.tenis4u import Tenis4uProvider, map_station_type, parse_occupancy
from tests.fakes import FakeHttp, fixture_text

RAW = fixture_text("tenis4u_occupancy.json")


def _facility(court_type=CourtType.BADMINTON, facility_id="104"):
    return SimpleNamespace(facility_id=facility_id, court_type=court_type)


class TestTypeMapping:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("badminton", CourtType.BADMINTON),
            ("padel", CourtType.PADEL),
            ("padel hala", CourtType.PADEL),
            ("Padel Hala", CourtType.PADEL),
            ("tenis hala: szt. mączka ", CourtType.TENNIS),
            ("tenis hala: szt. mączka", CourtType.TENNIS),
            ("squash", None),
            (None, None),
        ],
    )
    def test_map_station_type(self, raw, expected):
        assert map_station_type(raw) == expected


class TestParseOccupancy:
    def test_filters_by_court_type_and_parses_datetimes(self):
        courts = parse_occupancy(RAW, CourtType.BADMINTON)
        assert {c.court_name for c in courts} == {"Badminton 1", "Badminton 2"}
        first = courts[0]
        assert first.court_id == "Badminton 1"
        assert first.start == datetime(2026, 11, 23, 16, 0)
        assert first.end == datetime(2026, 11, 23, 19, 0)

    def test_multiple_days_and_stations(self):
        courts = parse_occupancy(RAW, CourtType.BADMINTON)
        assert len(courts) == 4
        assert {c.start.date() for c in courts} == {date(2026, 11, 23), date(2026, 11, 24)}

    def test_midnight_end_means_end_of_day(self):
        courts = parse_occupancy(RAW, CourtType.BADMINTON)
        late = [c for c in courts if c.start.hour == 21][0]
        assert late.end == datetime(2026, 11, 24, 0, 0)

    def test_both_padel_types_map_to_padel(self):
        courts = parse_occupancy(RAW, CourtType.PADEL)
        assert {c.court_name for c in courts} == {"Padel 1", "Padel Hala 1"}

    def test_tennis_type_with_trailing_space(self):
        courts = parse_occupancy(RAW, CourtType.TENNIS)
        assert [c.court_name for c in courts] == ["Kort 1"]

    def test_unknown_type_is_skipped_and_reported(self):
        unknown = []
        parse_occupancy(RAW, CourtType.BADMINTON, on_unknown_type=unknown.append)
        assert unknown == ["squash"]

    def test_empty_stations(self):
        assert parse_occupancy(json.dumps({"stations": []}), CourtType.BADMINTON) == []
        assert parse_occupancy(json.dumps({}), CourtType.BADMINTON) == []

    def test_bad_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_occupancy("<html>oops</html>", CourtType.BADMINTON)


class TestTenis4uProvider:
    def test_fetch_calls_occupancy_url_with_provider_headers(self):
        http = FakeHttp({"https://api.tenis4u.pl/occupancy/104": RAW})
        provider = Tenis4uProvider(http)

        provider.fetch_availability(_facility(), date(2026, 11, 23), date(2026, 11, 30))

        assert http.calls[0]["url"] == "https://api.tenis4u.pl/occupancy/104"
        assert http.calls[0]["headers"] == {"x-tenis-user-agent": "tenis4u-web-frontoffice/3.6.0"}

    def test_fetch_trims_to_date_range(self):
        http = FakeHttp({"https://api.tenis4u.pl": RAW})
        courts = Tenis4uProvider(http).fetch_availability(_facility(), date(2026, 11, 24), date(2026, 11, 24))
        assert [c.start for c in courts] == [datetime(2026, 11, 24, 17, 30)]

    def test_booking_url_uses_web_app_host(self):
        url = Tenis4uProvider(FakeHttp()).booking_url(_facility())
        assert url == "https://app.tenis4u.pl/court/104"
        assert "api." not in url
