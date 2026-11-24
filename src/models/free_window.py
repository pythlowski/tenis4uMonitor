from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, order=True)
class FreeWindow:
    """A merged free time window on a single court."""

    start: datetime
    end: datetime
    court_id: str  # identity/diffing only, never displayed

    def covers(self, other: "FreeWindow") -> bool:
        return self.court_id == other.court_id and self.start <= other.start and other.end <= self.end
