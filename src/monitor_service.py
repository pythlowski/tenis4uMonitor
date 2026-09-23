import time
import datetime
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

    def _seconds_until_next_slot(self) -> float:
        """Return the number of seconds to sleep until the next even interval boundary.

        For example, with fetch_interval_minutes=20 the scheduled times are
        XX:00, XX:20 and XX:40 (relative to the top of each hour).
        """
        interval = self.settings.api.fetch_interval_minutes * 60  # seconds
        now = datetime.datetime.now()
        elapsed_in_hour = now.minute * 60 + now.second + now.microsecond / 1_000_000
        remainder = elapsed_in_hour % interval
        return interval - remainder if remainder != 0 else interval

    def start(self) -> None:
        interval_minutes = self.settings.api.fetch_interval_minutes
        sleep_for = self._seconds_until_next_slot()
        self.logger.info(
            f"Waiting {sleep_for:.1f}s until next scheduled slot "
            f"(interval: every {interval_minutes} minutes on even boundaries)."
        )
        time.sleep(sleep_for)

        while True:
            started = time.monotonic()
            try:
                self.logger.info("Monitor run started...")
                self.run_once()
            except (URLError, HTTPError) as err:
                self.logger.error("Network or HTTP error occurred: %s", err)
            except Exception as err:
                self.logger.exception("Unexpected error during execution: %s", err)

            elapsed = time.monotonic() - started

            sleep_for = max(0, interval_minutes * 60 - elapsed)
            self.logger.info(f"Elapsed time: {elapsed:.2f}s. Sleeping for {sleep_for:.2f}s.")
            time.sleep(sleep_for)

