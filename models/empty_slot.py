from dataclasses import dataclass
from datetime import time


@dataclass
class EmptySlot:
    courtName: str
    date: time
    durationHours: int = 1
