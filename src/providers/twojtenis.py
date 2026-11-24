import json
import time as time_module
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable

from logger import Logger
from providers.base import CourtAvailability, CourtType, FacilityRef, SlotProvider

TYPE_MAP: dict[int, CourtType] = {
    0: CourtType.TENNIS,
    1: CourtType.BADMINTON,
    8: CourtType.PADEL,
}

WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MAX_BOOKINGS_RANGE_DAYS = 7  # API: CannotSearchForBookingsInMoreThan7Days (inclusive range)
CLUB_CACHE_TTL_SECONDS = 24 * 60 * 60

# weekday key -> (from, to); `to` may be None, meaning end of day
OpenHours = dict[str, tuple[time, time | None]]


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    type: int
    open_hours: OpenHours
    is_enabled: bool = True


@dataclass(frozen=True)
class Club:
    id: str
    open_hours: OpenHours
    locations: list[Location]


@dataclass(frozen=True)
class Booking:
    location_id: str
    start: datetime
    end: datetime


def _parse_time(value: str) -> time | None:
    """'HH:MM[:SS]' -> time. '24:00' returns None (end of day)."""
    if value.startswith("24:"):
        return None
    return time.fromisoformat(value)


def _end_datetime(day: date, start: datetime, value: time | None) -> datetime:
    """Build an end datetime; '00:00'/'24:00' or an end before the start means midnight of the next day."""
    end = datetime.combine(day, value) if value is not None else datetime.combine(day + timedelta(days=1), time())
    return end if end > start else datetime.combine(day + timedelta(days=1), time())


def parse_open_hours(raw: dict | None) -> OpenHours:
    hours: OpenHours = {}
    for key, entry in (raw or {}).items():
        if not entry or not entry.get("from") or not entry.get("to"):
            continue
        start = _parse_time(entry["from"])
        if start is None:
            continue
        hours[key.lower()] = (start, _parse_time(entry["to"]))
    return hours


def parse_club(raw: str) -> Club:
    data = json.loads(raw)
    locations = [
        Location(
            id=location["id"],
            name=location.get("name") or location.get("shortName") or location["id"],
            type=location.get("type"),
            open_hours=parse_open_hours(location.get("openHours")),
            is_enabled=location.get("isEnabled", True),
        )
        for location in data.get("locations") or []
    ]
    return Club(id=data["id"], open_hours=parse_open_hours(data.get("openHours")), locations=locations)


def parse_bookings(raw: str) -> list[Booking]:
    bookings = []
    for item in json.loads(raw):
        day = date.fromisoformat(item["date"])
        start_time = _parse_time(item["startTime"])
        start = datetime.combine(day, start_time or time())
        bookings.append(Booking(item["locationId"], start, _end_datetime(day, start, _parse_time(item["endTime"]))))
    return bookings


def select_locations(club: Club, court_type: CourtType) -> list[Location]:
    return [loc for loc in club.locations if loc.is_enabled and TYPE_MAP.get(loc.type) == court_type]


def date_chunks(date_from: date, date_to: date, max_days: int = MAX_BOOKINGS_RANGE_DAYS) -> list[tuple[date, date]]:
    """Split an inclusive date range into inclusive chunks of at most `max_days` days."""
    chunks = []
    start = date_from
    while start <= date_to:
        end = min(start + timedelta(days=max_days - 1), date_to)
        chunks.append((start, end))
        start = end + timedelta(days=1)
    return chunks


def subtract_intervals(
    span: tuple[datetime, datetime], busy: list[tuple[datetime, datetime]]
) -> list[tuple[datetime, datetime]]:
    """Return the parts of `span` not covered by any `busy` interval (which are clipped to the span)."""
    span_start, span_end = span
    free = []
    cursor = span_start
    for busy_start, busy_end in sorted(busy):
        busy_start, busy_end = max(busy_start, span_start), min(busy_end, span_end)
        if busy_end <= busy_start:
            continue
        if busy_start > cursor:
            free.append((cursor, busy_start))
        cursor = max(cursor, busy_end)
    if cursor < span_end:
        free.append((cursor, span_end))
    return free


def compute_free(
    locations: list[Location],
    bookings: list[Booking],
    club_open_hours: OpenHours,
    date_from: date,
    date_to: date,
) -> list[CourtAvailability]:
    """Free time = opening hours minus bookings, per location and date."""
    busy_by_location: dict[str, list[tuple[datetime, datetime]]] = {}
    for booking in bookings:
        busy_by_location.setdefault(booking.location_id, []).append((booking.start, booking.end))

    results = []
    for location in locations:
        busy = busy_by_location.get(location.id, [])
        day = date_from
        while day <= date_to:
            key = WEEKDAY_KEYS[day.weekday()]
            hours = location.open_hours.get(key) or club_open_hours.get(key)
            if hours:
                open_start = datetime.combine(day, hours[0])
                open_end = _end_datetime(day, open_start, hours[1])
                for start, end in subtract_intervals((open_start, open_end), busy):
                    results.append(CourtAvailability(court_id=location.id, court_name=location.name, start=start, end=end))
            day += timedelta(days=1)
    return results


class TwojTenisProvider(SlotProvider):
    name = "twojtenis"
    API_BASE_URL = "https://app-twojtenis-api-p-weu.azurewebsites.net"  # club metadata
    BOOKINGS_BASE_URL = "https://app-twojtenis-tech-krakow-api-p-weu.azurewebsites.net"  # bookings, all clubs
    WEB_BASE_URL = "https://app.twojtenis.pl"

    def __init__(self, http, clock: Callable[[], float] = time_module.monotonic):
        super().__init__(http)
        self.logger = Logger(name="TWOJTENIS")
        self._clock = clock
        self._clubs: dict[str, tuple[float, Club]] = {}

    def fetch_availability(self, facility: FacilityRef, date_from: date, date_to: date) -> list[CourtAvailability]:
        club = self._get_club(facility.facility_id)
        locations = select_locations(club, facility.court_type)
        if not locations:
            self.logger.warning(f"Club {facility.facility_id} has no enabled {facility.court_type} courts.")
            return []

        bookings: list[Booking] = []
        for chunk_from, chunk_to in date_chunks(date_from, date_to):
            raw = self.http.get(
                f"{self.BOOKINGS_BASE_URL}/api/v1/Clubs/{facility.facility_id}/bookings/public",
                headers=self.HEADERS,
                params={"from": chunk_from.isoformat(), "to": chunk_to.isoformat()},
            )
            bookings.extend(parse_bookings(raw))

        return compute_free(locations, bookings, club.open_hours, date_from, date_to)

    def booking_url(self, facility: FacilityRef) -> str:
        return f"{self.WEB_BASE_URL}/#/clubs/{facility.facility_id}?tab=bookings"

    def _get_club(self, club_id: str) -> Club:
        cached = self._clubs.get(club_id)
        now = self._clock()
        if cached and now - cached[0] < CLUB_CACHE_TTL_SECONDS:
            return cached[1]

        try:
            club = parse_club(self.http.get(f"{self.API_BASE_URL}/api/v1/Clubs/{club_id}", headers=self.HEADERS))
        except Exception as err:
            if cached:
                self.logger.warning(f"Refreshing club {club_id} failed ({err}); using cached data.")
                return cached[1]
            raise

        self._clubs[club_id] = (now, club)
        return club
