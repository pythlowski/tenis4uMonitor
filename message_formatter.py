import datetime
from collections import defaultdict

from discord_notifier import DiscordNotifier
from models.free_slot import FreeSlot
from settings import Settings
from datetime_utils import DatetimeUtils

class MessageFormatter:
    @staticmethod
    def format(free_slots: list[FreeSlot]) -> str:
        if not free_slots:
            return "No free slots found."

        return f"Found {len(free_slots)} free slots\n\n" + "\n".join(
                f"- {slot.courtName} at {DatetimeUtils.get_weekday(slot.date)} {slot.date.strftime('%d-%m-%Y %H:%M')}"
                for slot in free_slots
        )
    
    @staticmethod
    def discord_rich_format(free_slots: list[FreeSlot], weekdays: list[str], url: str = None) -> dict:
        embed = {
            "title": "tenis4u Monitor Report",
            "description": f"Found {len(free_slots)} free slots for: {', '.join(weekdays)}!" + (f"\n[Book on tenis4u!]({url})" if url else ""),
            "color": 5793266,
            "footer": {
                "text": "Monitoring Bot"
            },
            "timestamp": DatetimeUtils.get_current_datetime(),
            "fields": MessageFormatter._get_fields(free_slots),
        }

        return embed

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
    embed = MessageFormatter.discord_rich_format(free_slots, weekdays, "https://app.tenis4u.pl/court/104")
    discord_notifier.send_alert(embed=embed)