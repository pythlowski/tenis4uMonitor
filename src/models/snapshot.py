from pydantic import BaseModel

from models.free_slot import FreeSlot

class Snapshot(BaseModel):
    weekdays: list[str]
    free_slots: list[FreeSlot]

