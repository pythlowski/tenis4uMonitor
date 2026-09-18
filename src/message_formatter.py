import datetime
from collections import defaultdict

from discord_notifier import DiscordNotifier
from models.free_slot import FreeSlot
from models.snapshot import Snapshot
from settings import Settings
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
                        "url": "https://discord.com",
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
            + "\n[Book at tenis4u!](https://app.tenis4u.pl/court/104)" if url else "",
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
                "name": f"{DatetimeUtils.get_weekday(date)} {date.strftime('%d.%m.%Y')}", 
                "value": "\n".join(f"- {item['time'].strftime('%H:%M')} - {item['name']}" for item in values), 
                "inline": False}
            for date, values in grouped.items()
        ]

    @staticmethod
    def _get_new_slots_description(new_slots: list[FreeSlot]) -> str:
        return "\n".join(f"- {DatetimeUtils.get_weekday(slot.date)} {slot.date.strftime('%d.%m.%Y %H:%M')} - {slot.courtName}" for slot in new_slots)

if __name__ == "__main__":
    settings = Settings()
    discord_notifier = DiscordNotifier(webhook_url=settings.api.discord_webhook_url)
    free_slots = [
        FreeSlot(courtName="badminton 1", date=datetime.datetime(2024, 6, 15, 17, 0)),
        FreeSlot(courtName="badminton 2", date=datetime.datetime(2024, 6, 15, 17, 30)),
        FreeSlot(courtName="badminton 3", date=datetime.datetime(2024, 6, 15, 19, 0)),
        FreeSlot(courtName="badminton 2", date=datetime.datetime(2024, 6, 16, 20, 0)),
        FreeSlot(courtName="badminton 1", date=datetime.datetime(2024, 6, 16, 21, 30)),
        FreeSlot(courtName="badminton 2", date=datetime.datetime(2024, 6, 17, 18, 0)),
        FreeSlot(courtName="badminton 3", date=datetime.datetime(2024, 6, 18, 19, 0)),
    ]
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"]
    snapshot = Snapshot(weekdays=weekdays, free_slots=free_slots)
    payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=free_slots, url="https://app.tenis4u.pl/court/104")
    print(payload)
    discord_notifier.send_alert(payload=payload)