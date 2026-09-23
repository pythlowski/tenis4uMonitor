import time
from urllib.error import HTTPError, URLError

from discord_notifier import DiscordNotifier
from message_formatter import MessageFormatter
from settings import Settings
from data_service import DataService
from snapshots_comparator import SnapshotsComparator
from snapshots_repository import SnapshotRepository
from logger import Logger
from models.snapshot import Snapshot

class MonitorService:

    def __init__(self, settings: Settings):
        self.logger = Logger(name="MONITOR")
        self.settings = settings
        self.notifier = DiscordNotifier(self.settings.api.discord_webhook_url)
        self.data_service = DataService(self.settings)
        self.snapshots_repository = SnapshotRepository()
        self.snapshots_comparator = SnapshotsComparator()

    def run_once(self) -> None:
        free_slots = self.data_service.get_free_slots()

        self.logger.info(f"Found {len(free_slots)} free slots.")

        old_snapshot = self.snapshots_repository.get_latest()
        new_snapshot = Snapshot(weekdays=self.settings.weekdays, free_slots=free_slots)
        self.snapshots_repository.save(snapshot=new_snapshot)

        snapshots_diff = self.snapshots_comparator.get_diff(old=old_snapshot, new=new_snapshot)

        if not snapshots_diff.are_equal:
            self.notifier.send_alert(
                payload=MessageFormatter.get_payload(
                    snapshot=new_snapshot,
                    new_slots=snapshots_diff.new_slots, 
                    url=self.settings.api.url + f"/court/{self.settings.facility_id}"
                )
            )
    
    def start(self) -> None:
        while True:
            started = time.monotonic()
            try:
                self.logger.info(f"Monitor run started...")
                self.run_once()
            except (URLError, HTTPError) as err:
                self.logger.error("Network or HTTP error occurred: %s", err)
            except Exception as err:
                self.logger.exception("Unexpected error during execution: %s", err)

            elapsed = time.monotonic() - started
            sleep_for = max(0, self.settings.api.fetch_interval_minutes * 60 - elapsed)

            self.logger.info(f"Elapsed time: {elapsed:.2f} seconds. Sleeping for {sleep_for:.2f} seconds.")
            
            time.sleep(sleep_for)
