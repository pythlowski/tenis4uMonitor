from datetime import datetime

from pydantic import BaseModel

from models.free_window import FreeWindow


class FacilitySnapshot(BaseModel):
    facility_key: str
    taken_at: datetime
    windows: list[FreeWindow]
