from time import time

from api_client import APIClient
from app_config import AppConfig
from data_parser import DataParser


class DataService:
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_parser = DataParser(self.config.court_type, self.config.begin_time, self.config.end_time, self.config.days_of_week)
        self.api_client = APIClient(headers=self.config.api_headers)

    def get_free_slots(self) -> str:
        raw_data = self.api_client.fetch_data(self.config.api_url + f"/occupancy/{self.config.facility_id}")
        free_slots = self.data_parser.parse_occupancy(raw_data)
        return sorted(free_slots, key=lambda slot: (slot.date, slot.courtName))
