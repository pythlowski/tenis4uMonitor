from dataclasses import dataclass

from models.free_slot import FreeSlot


@dataclass
class SnapshotsDiff:
    are_equal: bool
    new_slots: list[FreeSlot]