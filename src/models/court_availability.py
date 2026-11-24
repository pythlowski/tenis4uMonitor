from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CourtAvailability:
    """Provider-neutral free interval on a single court."""

    court_id: str  # stable identity (station name / location GUID)
    court_name: str
    start: datetime
    end: datetime
