import logging
import time
import calendar
import datetime
from urllib.error import HTTPError, URLError

from models.snapshot import Snapshot
from settings import Settings
from data_service import DataService
from email_notifier import EmailNotifier
from snapshots_manager import SnapshotManager


class APIMonitorService:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.notifier = EmailNotifier(self.settings.smtp)
        self.data_service = DataService(self.settings)
        self.snapshots_manager = SnapshotManager()

    def run_once(self) -> None:
        free_slots = self.data_service.get_free_slots()

        print(f"Found {len(free_slots)} free slots:")
        snapshot = Snapshot(days_of_week=self.settings.days_of_week, free_slots=free_slots)
        self.snapshots_manager.save(snapshot)
        for slot in free_slots:
            print(f"- {slot.courtName} at {self.get_weekday(slot.date)} {slot.date.strftime('%Y-%m-%d %H:%M:%S')}")

        if False:
            self.notifier.send_alert(
                subject="[Alert] API Update Notification",
                body=f"Automated System Report:\n\n{summary}",
            )


            
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

            time.sleep(self.settings.api.fetch_interval_minutes * 60)
