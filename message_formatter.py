import datetime
from collections import defaultdict

from discord_notifier import DiscordNotifier
from models.free_slot import FreeSlot
from settings import Settings
from datetime_utils import DatetimeUtils

class MessageFormatter:
    @staticmethod
    def format_payload(free_slots: list[FreeSlot]) -> str:
        if not free_slots:
            return "No free slots found."

        message = f"Found {len(free_slots)} free slots\n\n" + "\n".join(
                f"- {slot.courtName} at {DatetimeUtils.get_weekday(slot.date)} {slot.date.strftime('%d-%m-%Y %H:%M')}"
                for slot in free_slots
        )

        return {"content": message}
    
    @staticmethod
    def discord_rich_format_payload(free_slots: list[FreeSlot], weekdays: list[str], url: str = None) -> dict:
        embeds = [
            {
                "title": "tenis4u Monitor Report",
                "description": f"Found {len(free_slots)} free slots for: {', '.join(weekdays)}!" 
                + "\n[Book at tenis4u!](https://app.tenis4u.pl/court/104)" if url else "",
                "color": 5793266,
                "footer": {
                    "text": "tenis4u Monitor"
                },
                "timestamp": DatetimeUtils.get_current_datetime(),
                "fields": MessageFormatter._get_fields(free_slots),
            }
        ]

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
        
        return {"embeds": embeds, "components": components}

    @staticmethod
    def _get_fields(free_slots: list[FreeSlot]) -> list[dict]:
        grouped = defaultdict(list)

        for slot in sorted(free_slots, key=lambda slot: (slot.date, slot.courtName)):
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
    payload = MessageFormatter.discord_rich_format_payload(free_slots, weekdays, "https://app.tenis4u.pl/court/104")
    print(payload)
    discord_notifier.send_alert(payload=payload)