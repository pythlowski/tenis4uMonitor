import json
from datetime import date, datetime, timedelta
from typing import Callable

from logger import Logger
from providers.base import CourtAvailability, CourtType, FacilityRef, SlotProvider

TYPE_MAP: dict[str, CourtType] = {
    "badminton": CourtType.BADMINTON,
    "padel": CourtType.PADEL,
    "padel hala": CourtType.PADEL,
    "tenis hala: szt. mączka": CourtType.TENNIS,  # raw value has a trailing space
}

DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"


def map_station_type(raw_type: str | None) -> CourtType | None:
    return TYPE_MAP.get((raw_type or "").strip().lower())


def _parse_datetime(day: str, time_str: str) -> datetime:
    return datetime.strptime(f"{day} {time_str}", DATETIME_FORMAT)


def parse_occupancy(
    raw: str,
    court_type: CourtType,
    on_unknown_type: Callable[[str], None] | None = None,
) -> list[CourtAvailability]:
    """Turn a tenis4u /occupancy response into free intervals for one court type."""
    data = json.loads(raw)
    results: list[CourtAvailability] = []

    for station in data.get("stations") or []:
        raw_type = station.get("type")
        mapped = map_station_type(raw_type)
        if mapped is None:
            if on_unknown_type:
                on_unknown_type(str(raw_type))
            continue
        if mapped != court_type:
            continue

        name = station["name"]
        for day in station.get("days") or []:
            for free in day.get("free_hours") or []:
                start = _parse_datetime(day["date"], free["begin_time"])
                end = _parse_datetime(day["date"], free["end_time"])
                if end <= start:  # "00:00:00" end means midnight of the next day
                    end += timedelta(days=1)
                results.append(CourtAvailability(court_id=name, court_name=name, start=start, end=end))

    return results


class Tenis4uProvider(SlotProvider):
    name = "tenis4u"
    USES_PROXY = True  # the tenis4u API blocks repeated requests from one IP
    API_BASE_URL = "https://api.tenis4u.pl"
    WEB_BASE_URL = "https://app.tenis4u.pl"
    HEADERS = {"x-tenis-user-agent": "tenis4u-web-frontoffice/3.6.0"}

    def __init__(self, http):
        super().__init__(http)
        self.logger = Logger(name="TENIS4U")
        self._warned_types: set[str] = set()

    def fetch_availability(self, facility: FacilityRef, date_from: date, date_to: date) -> list[CourtAvailability]:
        raw = self.http.get(f"{self.API_BASE_URL}/occupancy/{facility.facility_id}", headers=self.HEADERS)
        courts = parse_occupancy(raw, facility.court_type, on_unknown_type=self._warn_unknown_type)
        return [c for c in courts if date_from <= c.start.date() <= date_to]

    def booking_url(self, facility: FacilityRef) -> str:
        return f"{self.WEB_BASE_URL}/court/{facility.facility_id}"

    def _warn_unknown_type(self, raw_type: str) -> None:
        if raw_type not in self._warned_types:
            self._warned_types.add(raw_type)
            self.logger.warning(f"Unknown tenis4u station type {raw_type!r} - skipped.")
