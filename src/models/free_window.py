from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, order=True)
class FreeWindow:
    """A free window of the configured duration on a single court."""

    start: datetime
    end: datetime
    court_id: str  # stable identity, used for diffing
    court_name: str = field(compare=False)  # display only

    def covers(self, other: "FreeWindow") -> bool:
        return self.court_id == other.court_id and self.start <= other.start and other.end <= self.end
