from time import time

from api_client import APIClient
from settings import Settings
from data_parser import DataParser


class DataService:
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_parser = DataParser(self.settings.court_type, self.settings.begin_time, self.settings.end_time, self.settings.days_of_week)
        self.api_client = APIClient(headers=self.settings.api.headers)

    def get_free_slots(self) -> str:
        raw_data = self.api_client.fetch_data(self.settings.api.url + f"/occupancy/{self.settings.facility_id}")
        free_slots = self.data_parser.parse_occupancy(raw_data)
        return sorted(free_slots, key=lambda slot: (slot.date, slot.courtName))
