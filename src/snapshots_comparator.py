from datetime import datetime

from models.free_slot import FreeSlot
from models.snapshot import Snapshot


class SnapshotsComparator:
    def get_new_slots(self, new: Snapshot, old: Snapshot):
        return [slot for slot in new.free_slots if slot not in old.free_slots]


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