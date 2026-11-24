from logger import Logger
from models.facility_snapshot import FacilitySnapshot
from models.snapshots_diff import SnapshotsDiff


class SnapshotsComparator:
    def __init__(self):
        self.logger = Logger(name="SNAP_COMPARE")

    def get_diff(self, old: FacilitySnapshot | None, new: FacilitySnapshot) -> SnapshotsDiff:
        if old is None:
            self.logger.info(f"[{new.facility_key}] No previous snapshot, taking a baseline.")
            return SnapshotsDiff(changed=True, new_windows=[], is_baseline=True)

        changed = set(old.windows) != set(new.windows)
        # A window is new unless an old window on the same court fully covers it:
        # shrinking is silent; growing, a new window or another court freeing up is new.
        new_windows = [
            window for window in new.windows if not any(previous.covers(window) for previous in old.windows)
        ]

        if new_windows:
            self.logger.info(f"[{new.facility_key}] Found {len(new_windows)} new windows.")

        return SnapshotsDiff(changed=changed, new_windows=new_windows)
