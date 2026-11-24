from collections import defaultdict

from models.free_slot import FreeSlot
from models.snapshot import Snapshot
from datetime_utils import DatetimeUtils

class MessageFormatter:

    @staticmethod
    def get_payload(snapshot: Snapshot, new_slots: list[FreeSlot], url: str = None) -> dict:
        embeds = []
        embeds.append(MessageFormatter.snapshot_embed(snapshot=snapshot, url=url))

        if new_slots:
            embeds.append(MessageFormatter.new_slots_embed(new_slots=new_slots))

        components = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Book here!",
                        "url": url,
                        "emoji": {
                            "name": "🎾"
                        }
                    }
                ]
            }
        ] if url else []
        
        return {
            "content": "@everyone" if new_slots else "", 
            "embeds": embeds, 
            "components": components, 
            "allowed_mentions": {"parse": ["everyone"]}}
    
    @staticmethod
    def snapshot_embed(snapshot: Snapshot, url: str = None) -> dict:
        return {
            "title": "tenis4u Monitor Report",
            "description": f"Found {len(snapshot.free_slots)} free slots for: {', '.join(snapshot.weekdays)}!"
            + (f"\n[Book at tenis4u!]({url})" if url else ""),
            "color": 5793266,
            "footer": {
                "text": "tenis4u Monitor"
            },
            "timestamp": DatetimeUtils.get_current_datetime(),
            "fields": MessageFormatter._get_fields(snapshot.free_slots),
        }

    @staticmethod
    def new_slots_embed(new_slots: list[FreeSlot]) -> dict:
         return {
            "title": "New free slots!",
            "description": MessageFormatter._get_new_slots_description(new_slots),
            "color": 15906135,
            "footer": {
                "text": "tenis4u Monitor"
            },
            "timestamp": DatetimeUtils.get_current_datetime(),
        }

    @staticmethod
    def _get_fields(slots: list[FreeSlot]) -> list[dict]:
        grouped = defaultdict(list)

        for slot in sorted(slots, key=lambda slot: (slot.date, slot.courtName)):
            grouped[slot.date.date()].append({
                "name": slot.courtName,
                "time": slot.date.time()
            })

        return [
            {
                "name": f"{DatetimeUtils.get_weekday(date)} {date.strftime('%d.%m')}", 
                "value": "\n".join(f"- {item['time'].strftime('%H:%M')} - {item['name']}" for item in values), 
                "inline": False}
            for date, values in grouped.items()
        ]

    @staticmethod
    def _get_new_slots_description(new_slots: list[FreeSlot]) -> str:
        return "\n".join(f"- {DatetimeUtils.get_weekday(slot.date)} {slot.date.strftime('%d.%m %H:%M')} - {slot.courtName}" for slot in new_slots)
