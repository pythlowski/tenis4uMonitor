from http_client import HttpClient
from proxy_background_service import ProxyBackgroundService
from providers.tenis4u import Tenis4uProvider
from datetime_utils import DatetimeUtils
from models.free_slot import FreeSlot
from settings import Settings
from slots_computer import SlotsComputer


class DataService:
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.facility = settings.facilities[0]
        self.slots_computer = SlotsComputer(self.facility.court_type, self.settings.begin_time, self.settings.end_time, self.settings.weekdays)
        self.http = HttpClient(ProxyBackgroundService(max_proxies_ready=self.settings.max_proxies_ready))

    def get_free_slots(self) -> list[FreeSlot]:
        raw_data = self.http.get(Tenis4uProvider.API_BASE_URL + f"/occupancy/{self.facility.facility_id}", headers=Tenis4uProvider.HEADERS)
        free_slots = self.slots_computer.compute(raw_data)
        filtered_slots = self._filter_slots_by_weekday(free_slots)
        return sorted(filtered_slots, key=lambda slot: (slot.date, slot.courtName))

    def _filter_slots_by_weekday(self, free_slots: list[FreeSlot]) -> list[FreeSlot]:
        return [slot for slot in free_slots if DatetimeUtils.get_weekday(slot.date) in self.settings.weekdays]