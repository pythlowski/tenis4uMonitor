from time import time

from api_client import APIClient
from models.free_slot import FreeSlot
from settings import Settings
from slots_computer import SlotsComputer


class DataService:
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.slots_computer = SlotsComputer(self.settings.court_type, self.settings.begin_time, self.settings.end_time, self.settings.days_of_week)
        self.api_client = APIClient(api_settings=self.settings.api)

    def get_free_slots(self) -> list[FreeSlot]:
        raw_data = self.api_client.fetch_data(self.settings.api.url + f"/occupancy/{self.settings.facility_id}")
        free_slots = self.slots_computer.compute(raw_data)
        return sorted(free_slots, key=lambda slot: (slot.date, slot.courtName))
