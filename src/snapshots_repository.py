from pathlib import Path

from pydantic import ValidationError

from logger import Logger
from models.facility_snapshot import FacilitySnapshot


class SnapshotRepository:
    """Stores the latest snapshot of each facility in `{directory}/{facility_key}.json`."""

    def __init__(self, directory: str | Path = "snapshots"):
        self.logger = Logger("SNAPSHOTS")
        self.directory = Path(directory)

    def get(self, facility_key: str) -> FacilitySnapshot | None:
        path = self._path(facility_key)
        if not path.exists():
            return None
        try:
            return FacilitySnapshot.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValidationError, ValueError) as e:
            self.logger.warning(f"Ignoring unreadable snapshot {path}: {e}")
            return None

    def save(self, snapshot: FacilitySnapshot) -> None:
        path = self._path(snapshot.facility_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

    def _path(self, facility_key: str) -> Path:
        return self.directory / f"{facility_key}.json"
