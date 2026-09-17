import logging
import time
import datetime
from urllib.error import HTTPError, URLError

from discord_notifier import DiscordNotifier
from message_formatter import MessageFormatter
from settings import Settings
from data_service import DataService
from snapshots_manager import SnapshotManager


class MonitorService:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.notifier = DiscordNotifier(self.settings.api.discord_webhook_url)
        self.data_service = DataService(self.settings)
        self.snapshots_manager = SnapshotManager()

    def run_once(self) -> None:
        free_slots = self.data_service.get_free_slots()

        print(f"Found {len(free_slots)} free slots.")
        self.notifier.send_alert(embed=MessageFormatter.discord_rich_format(free_slots))
    
    def start(self) -> None:
        started = time.monotonic()

        while True:
            
            try:
                print(f"Fetching data at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.run_once()
            except (URLError, HTTPError) as err:
                logging.error("Network or HTTP error occurred: %s", err)
            except Exception as err:
                logging.exception("Unexpected error during execution: %s", err)

            elapsed = time.monotonic() - started
            sleep_for = max(0, self.settings.api.fetch_interval_minutes * 60 - elapsed)

            print(f"Elapsed time: {elapsed:.2f} seconds. Sleeping for {sleep_for:.2f} seconds.")
            
            time.sleep(sleep_for)
