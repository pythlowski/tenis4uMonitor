from dataclasses import dataclass

from src.models.free_slot import FreeSlot

@dataclass
class Snapshot:
    days_of_week: list[str]
    free_slots: list[FreeSlot]
