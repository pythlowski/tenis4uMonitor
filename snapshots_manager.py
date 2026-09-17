import datetime
import json

from models.snapshot import Snapshot


class SnapshotManager:
    def __init__(self):
        pass

    def save(self, snapshot: Snapshot) -> None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshots/snapshot_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(snapshot.__dict__, f, default=str)