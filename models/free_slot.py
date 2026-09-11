from dataclasses import dataclass
from datetime import datetime


@dataclass
class FreeSlot:
    courtName: str
    date: datetime
    durationHours: int = 1
