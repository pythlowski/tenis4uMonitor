from dataclasses import dataclass
from datetime import datetime


@dataclass
class EmptySlot:
    courtName: str
    date: datetime
    durationHours: int = 1
