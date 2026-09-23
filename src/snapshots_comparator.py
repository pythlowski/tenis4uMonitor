from datetime import datetime

from logger import Logger
from models.free_slot import FreeSlot
from models.snapshot import Snapshot


class SnapshotsComparator:
    def __init__(self):
        self.logger = Logger(name="SNAP_COMPARE")

    def get_new_slots(self, new: Snapshot, old: Snapshot) -> list[FreeSlot]:
        new_slots = [slot for slot in new.free_slots if slot not in old.free_slots]

        if new_slots:
            self.logger.info(f"Found {len(new_slots)} new slots.")

        return new_slots


if __name__ == "__main__":
    new_slots = [
        FreeSlot(courtName="badminton 1", date=datetime(2024, 6, 19, 17, 0)),
        FreeSlot(courtName="badminton 2", date=datetime(2024, 6, 19, 17, 30)),
        FreeSlot(courtName="badminton 3", date=datetime(2024, 6, 19, 18, 00)),
    ]

    old_slots = [
        FreeSlot(courtName="badminton 2", date=datetime(2024, 6, 19, 17, 30)),
    ]
    
    new = Snapshot(weekdays=[], free_slots=new_slots)
    old = Snapshot(weekdays=[], free_slots=old_slots)

    comparator = SnapshotsComparator()
    print(comparator.get_new_slots(new, old))