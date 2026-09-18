from time import time

from api_client import APIClient
from datetime_utils import DatetimeUtils
from src.models.free_slot import FreeSlot
from settings import Settings
from slots_computer import SlotsComputer


class DataService:
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.slots_computer = SlotsComputer(self.settings.court_type, self.settings.begin_time, self.settings.end_time, self.settings.weekdays)
        self.api_client = APIClient(api_settings=self.settings.api)

    def get_free_slots(self) -> list[FreeSlot]:
        raw_data = self.api_client.fetch_data(self.settings.api.url + f"/occupancy/{self.settings.facility_id}")
        free_slots = self.slots_computer.compute(raw_data)
        filtered_slots = self._filter_slots_by_weekday(free_slots)
        return sorted(filtered_slots, key=lambda slot: (slot.date, slot.courtName))

    def _filter_slots_by_weekday(self, free_slots: list[FreeSlot]) -> list[FreeSlot]:
        return [slot for slot in free_slots if DatetimeUtils.get_weekday(slot.date) in self.settings.weekdays]