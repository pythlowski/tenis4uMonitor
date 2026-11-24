from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING, ClassVar, Protocol

from models.court_availability import CourtAvailability
from models.court_type import CourtType

if TYPE_CHECKING:
    from http_client import HttpClient

__all__ = ["CourtAvailability", "CourtType", "FacilityRef", "SlotProvider"]


class FacilityRef(Protocol):
    """The part of a facility config a provider needs."""

    facility_id: str
    court_type: CourtType


class SlotProvider(ABC):
    name: ClassVar[str]
    API_BASE_URL: ClassVar[str]
    WEB_BASE_URL: ClassVar[str]
    HEADERS: ClassVar[dict[str, str]] = {}

    def __init__(self, http: HttpClient):
        self.http = http

    @abstractmethod
    def fetch_availability(self, facility: FacilityRef, date_from: date, date_to: date) -> list[CourtAvailability]:
        """Return free intervals for the facility's court type within [date_from, date_to]."""

    @abstractmethod
    def booking_url(self, facility: FacilityRef) -> str:
        """Return the URL a person can open in the browser to book manually."""
