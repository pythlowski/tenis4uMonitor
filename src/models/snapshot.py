from dataclasses import dataclass
import json

from models.free_slot import FreeSlot

@dataclass
class Snapshot:
    weekdays: list[str]
    free_slots: list[FreeSlot]

    @classmethod
    def from_json(cls, filepath):
        """Reads a JSON file and instantiates the class."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls(**data)
