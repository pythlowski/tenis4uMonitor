from dataclasses import dataclass, field

from models.free_window import FreeWindow


@dataclass(frozen=True)
class SnapshotsDiff:
    changed: bool
    new_windows: list[FreeWindow] = field(default_factory=list)
    is_baseline: bool = False
