from dataclasses import dataclass
from datetime import datetime


@dataclass
class FreeSlot:
    courtName: str
    date: datetime
    durationHours: int = 1

    def __eq__(self, other):
        return self.date == other.date and self.courtName == other.courtName

    def __lt__(self, other):
        return self.date < other.date or self.courtName < other.courtName
