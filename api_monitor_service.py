import json
import logging
import time
import calendar
import datetime
from urllib.error import HTTPError, URLError

from app_config import AppConfig
from data_service import DataService
from email_notifier import EmailNotifier


class APIMonitorService:

    def __init__(self, config: AppConfig):
        self.config = config
        self.notifier = EmailNotifier(self.config)
        self.data_service = DataService(self.config)

    def run_once(self) -> None:
        free_slots = self.data_service.get_free_slots()

        print(f"Found {len(free_slots)} free slots:")
        self.save_snapshot(free_slots)
        for slot in free_slots:
            print(f"- {slot.courtName} at {self.get_weekday(slot.date)} {slot.date.strftime('%Y-%m-%d %H:%M:%S')}")

        if False:
            self.notifier.send_alert(
                subject="[Alert] API Update Notification",
                body=f"Automated System Report:\n\n{summary}",
            )

    def save_snapshot(self, free_slots: list) -> None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshots/snapshot_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump([slot.__dict__ for slot in free_slots], f, default=str)
            
    def get_weekday(self, date: datetime) -> str:
        return calendar.day_name[date.weekday()]
    
    def start(self) -> None:
        while True:
            try:
                self.run_once()
            except (URLError, HTTPError) as err:
                logging.error("Network or HTTP error occurred: %s", err)
            except Exception as err:
                logging.exception("Unexpected error during execution: %s", err)

            time.sleep(self.config.fetch_interval_minutes * 60)
