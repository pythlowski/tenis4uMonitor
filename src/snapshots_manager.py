import datetime
import json
import os
from pathlib import Path

from models.snapshot import Snapshot
from logger import Logger

class SnapshotManager:
    MAX_FILES = 10
    DIRECTORY_NAME = "snapshots"
    FILENAME_PATTERN = "snapshot_*.json"

    def __init__(self):
        self.logger = Logger("SNAPSHOTS")
    
    def save(self, snapshot: Snapshot) -> None:
        with open(f"{self.DIRECTORY_NAME}/{self._get_filename()}", "w") as f:
            json.dump(snapshot.__dict__, f, default=str)
        self._ensure_rolling()

    def get_latest(self) -> Snapshot:
        files = self._get_all(newest_first=True)

        if len(files) == 0:
            return Snapshot()

        return Snapshot.from_json(files[0])
    
    def _get_all(self, newest_first:bool = True) -> list[Path]:
        dir_path = Path(self.DIRECTORY_NAME)
        return sorted(dir_path.glob(self.FILENAME_PATTERN), key=os.path.getmtime, reverse=newest_first)
        
    def _ensure_rolling(self):
        files = self._get_all(newest_first=False)
        for old_file in files[self.MAX_FILES:]:
            try:
                old_file.unlink()
            except OSError as e:
                self.logger.error(f"Error deleting old file {old_file}.", e)

    def _get_filename(self) -> str:
        timestamp: str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.FILENAME_PATTERN.replace("*", timestamp)


if __name__ == "__main__":
    manager = SnapshotManager()

    # snapshot = Snapshot(weekdays=[], free_slots=[])
    # manager.save(snapshot=snapshot)

    latest = manager.get_latest()
    print(latest)