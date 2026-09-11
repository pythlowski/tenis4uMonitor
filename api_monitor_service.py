import logging
import time
from urllib.error import HTTPError, URLError

from app_config import AppConfig
from data_service import DataService
from email_notifier import EmailNotifier


class APIMonitorService:

    def __init__(self, config_path: str = "config.json"):
        self.config = AppConfig.from_json(config_path)
        self.notifier = EmailNotifier(self.config)
        self.data_service = DataService(self.config)

    def run_once(self) -> None:
        free_slots = self.data_service.get_free_slots(facility_id=104)

        print(f"Found {len(free_slots)} free slots:")
        for slot in free_slots:
            print(f"- {slot.courtName} at {slot.date.strftime('%Y-%m-%d %H:%M:%S')}")

        if False:
            self.notifier.send_alert(
                subject="[Alert] API Update Notification",
                body=f"Automated System Report:\n\n{summary}",
            )

    def start(self) -> None:
        while True:
            try:
                self.run_once()
            except (URLError, HTTPError) as err:
                logging.error("Network or HTTP error occurred: %s", err)
            except Exception as err:
                logging.exception("Unexpected error during execution: %s", err)

            time.sleep(self.config.fetch_interval_seconds)
