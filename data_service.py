from api_client import APIClient
from app_config import AppConfig
from data_parser import DataParser


class DataService:
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_parser = DataParser()
        self.api_client = APIClient(headers=self.config.api_headers)

    def get_free_slots(self, facility_id: int) -> str:
        raw_data = self.api_client.fetch_data(self.config.api_url + f"/occupancy/{facility_id}")
        free_slots = self.data_parser.parse_occupancy(raw_data, "badminton")
        return sorted(free_slots, key=lambda slot: (slot.date, slot.courtName))
