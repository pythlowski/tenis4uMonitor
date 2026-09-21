import datetime
import json
import os
from pathlib import Path

from models.free_slot import FreeSlot
from models.snapshot import Snapshot
from logger import Logger

class SnapshotRepository:
    MAX_FILES = 10
    DIRECTORY_NAME = "snapshots"
    FILENAME_PATTERN = "snapshot_*.json"

    def __init__(self):
        self.logger = Logger("SNAPSHOTS")
    
    def save(self, snapshot: Snapshot) -> None:
        path = Path(f"{self.DIRECTORY_NAME}/{self._get_filename()}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        self._ensure_rolling()

    def get_latest(self) -> Snapshot:
        file_paths: list[Path] = self._get_all(newest_first=True)

        if not file_paths:
            return Snapshot(weekdays=[], free_slots=[])

        return Snapshot.model_validate_json(file_paths[0].read_text(encoding="utf-8"))
    
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
    repository = SnapshotRepository()

    snapshot = Snapshot(weekdays=["Monday", "Tuesday"], free_slots=[
        FreeSlot(courtName="badminton 1", date=datetime.datetime(2026, 6, 19, 17, 0)),
        FreeSlot(courtName="badminton 2", date=datetime.datetime(2026, 6, 19, 17, 30)),
    ])
    repository.save(snapshot=snapshot)

    latest = repository.get_latest()
    print(latest)