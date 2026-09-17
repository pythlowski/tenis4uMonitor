import logging
import time
import calendar
import datetime
from urllib.error import HTTPError, URLError

from discord_notifier import DiscordNotifier
from models.snapshot import Snapshot
from settings import Settings
from data_service import DataService
from snapshots_manager import SnapshotManager


class APIMonitorService:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.notifier = DiscordNotifier(self.settings.api.discord_webhook_url)
        self.data_service = DataService(self.settings)
        self.snapshots_manager = SnapshotManager()

    def run_once(self) -> None:
        free_slots = self.data_service.get_free_slots()

        snapshot = Snapshot(days_of_week=self.settings.days_of_week, free_slots=free_slots)
        self.snapshots_manager.save(snapshot)

        self.notifier.send_alert(
            message=f"Found {len(free_slots)} free slots\n\n" + "\n".join(
                f"- {slot.courtName} at {self.get_weekday(slot.date)} {slot.date.strftime('%Y-%m-%d %H:%M:%S')}"
                for slot in free_slots
            )
        )


            
    def get_weekday(self, date: datetime) -> str:
        return calendar.day_name[date.weekday()]
    
    def start(self) -> None:
        while True:
            try:
                print(f"Fetching data at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.run_once()
            except (URLError, HTTPError) as err:
                logging.error("Network or HTTP error occurred: %s", err)
            except Exception as err:
                logging.exception("Unexpected error during execution: %s", err)

            time.sleep(self.settings.api.fetch_interval_minutes * 60)
