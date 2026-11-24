from logger import Logger
from models.snapshot import Snapshot
from models.snapshots_diff import SnapshotsDiff


class SnapshotsComparator:
    def __init__(self):
        self.logger = Logger(name="SNAP_COMPARE")

    def get_diff(self, old: Snapshot, new: Snapshot) -> SnapshotsDiff:
        are_equal = old == new
        new_slots = [slot for slot in new.free_slots if slot not in old.free_slots]

        if new_slots:
            self.logger.info(f"Found {len(new_slots)} new slots.")

        return SnapshotsDiff(are_equal=are_equal, new_slots=new_slots)
