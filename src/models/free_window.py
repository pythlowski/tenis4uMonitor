from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, order=True)
class FreeWindow:
    """A merged free time window on a single court."""

    start: datetime
    end: datetime
    court_id: str  # stable identity, used for diffing
    court_name: str = field(default="", compare=False)  # display only; empty in older snapshots

    @property
    def court_label(self) -> str:
        return self.court_name or self.court_id

    def covers(self, other: "FreeWindow") -> bool:
        return self.court_id == other.court_id and self.start <= other.start and other.end <= self.end
