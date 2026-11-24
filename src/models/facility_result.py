from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.free_window import FreeWindow

if TYPE_CHECKING:
    from settings import FacilityConfig


@dataclass(frozen=True)
class FacilityResult:
    """Outcome of one monitor run for one facility, ready to be notified."""

    facility: FacilityConfig
    booking_url: str
    windows: list[FreeWindow]
    new_windows: list[FreeWindow] = field(default_factory=list)
    changed: bool = False
    is_baseline: bool = False

    @property
    def should_ping(self) -> bool:
        return bool(self.new_windows) and not self.is_baseline
