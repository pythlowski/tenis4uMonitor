import calendar
from collections import defaultdict
from datetime import date, datetime
from typing import Callable, Sequence

from availability import ALL_WEEKDAYS, group_windows
from models.facility_result import FacilityResult
from models.free_window import FreeWindow

# Discord limits
MAX_EMBEDS_PER_MESSAGE = 10
MAX_EMBED_CHARS_PER_MESSAGE = 6000
MAX_FIELDS_PER_EMBED = 25
MAX_FIELD_VALUE = 1024
MAX_DESCRIPTION = 4096
MAX_TITLE = 256
MAX_BUTTON_LABEL = 80
BUTTONS_PER_ROW = 5

REPORT_COLOR = 5793266
NEW_WINDOWS_COLOR = 15906135
FOOTER = "Court Monitor"


def format_range(start: datetime, end: datetime) -> str:
    return f"{start:%H:%M}–{end:%H:%M}"


def courts_label(count: int) -> str:
    return "1 court" if count == 1 else f"{count} courts"


def day_label(day: date) -> str:
    return f"{calendar.day_name[day.weekday()]} {day:%d.%m}"


def weekdays_label(weekdays: Sequence[str]) -> str:
    if set(weekdays) >= set(ALL_WEEKDAYS):
        return "every day"
    ordered = [day for day in ALL_WEEKDAYS if day in weekdays]
    return ", ".join(day[:3] for day in ordered)


def window_lines(windows: list[FreeWindow], prefix: str = "", with_day: bool = True) -> list[str]:
    """`- {prefix}Monday 23.11 16:30–19:00 · 3 courts`, grouped per identical range."""
    return [
        f"- {prefix}{day_label(group.start.date()) + ' ' if with_day else ''}"
        f"{format_range(group.start, group.end)} · {courts_label(group.count)}"
        for group in group_windows(windows)
    ]


def join_limited(lines: list[str], limit: int) -> str:
    """Join lines, replacing the tail with '…and N more' if it would exceed `limit` chars."""
    text = "\n".join(lines)
    if len(text) <= limit:
        return text
    kept: list[str] = []
    for index, line in enumerate(lines):
        suffix = f"\n…and {len(lines) - index} more"
        if len("\n".join([*kept, line])) + len(suffix) > limit:
            return "\n".join(kept) + suffix
        kept.append(line)
    return "\n".join(kept)


def embed_size(embed: dict) -> int:
    """Characters that count towards Discord's 6000 per-message limit."""
    size = len(embed.get("title", "")) + len(embed.get("description", ""))
    size += len(embed.get("footer", {}).get("text", ""))
    size += sum(len(f["name"]) + len(f["value"]) for f in embed.get("fields", []))
    return size


def link_button(label: str, url: str) -> dict:
    return {"type": 2, "style": 5, "label": label[:MAX_BUTTON_LABEL], "url": url, "emoji": {"name": "🎾"}}


def button_rows(buttons: list[dict]) -> list[dict]:
    return [
        {"type": 1, "components": buttons[i : i + BUTTONS_PER_ROW]}
        for i in range(0, len(buttons), BUTTONS_PER_ROW)
    ]


class MessageFormatter:
    def __init__(self, weekdays: Sequence[str], now: Callable[[], str] | None = None):
        self.weekdays = list(weekdays)
        self._now = now or (lambda: datetime.now().astimezone().isoformat())

    # ---- embeds -----------------------------------------------------------

    def facility_embed(self, result: FacilityResult) -> dict:
        count = len(result.windows)
        if count:
            summary = f"Found {count} free window{'s' if count != 1 else ''} for: {weekdays_label(self.weekdays)}"
        else:
            summary = f"No free windows for: {weekdays_label(self.weekdays)}"
        description = summary + (f"\n[Book here]({result.booking_url})" if result.booking_url else "")

        embed = {
            "title": result.facility.name[:MAX_TITLE],
            "description": description,
            "color": REPORT_COLOR,
            "footer": {"text": FOOTER},
            "timestamp": self._now(),
            "fields": [],
        }
        if result.booking_url:
            embed["url"] = result.booking_url

        by_day: dict[date, list[FreeWindow]] = defaultdict(list)
        for window in result.windows:
            by_day[window.start.date()].append(window)

        days = sorted(by_day)
        budget = MAX_EMBED_CHARS_PER_MESSAGE - embed_size(embed) - 100  # leave room for an overflow note
        for index, day in enumerate(days):
            field = {
                "name": day_label(day),
                "value": join_limited(window_lines(by_day[day], with_day=False), MAX_FIELD_VALUE),
                "inline": False,
            }
            field_size = len(field["name"]) + len(field["value"])
            if index >= MAX_FIELDS_PER_EMBED or field_size > budget:
                embed["description"] += f"\n…{len(days) - index} more day(s) not shown"
                break
            embed["fields"].append(field)
            budget -= field_size

        return embed

    def new_windows_embed(self, lines: list[str]) -> dict:
        return {
            "title": "New free windows!",
            "description": join_limited(lines, MAX_DESCRIPTION),
            "color": NEW_WINDOWS_COLOR,
            "footer": {"text": FOOTER},
            "timestamp": self._now(),
        }

    # ---- payloads ---------------------------------------------------------

    def facility_payload(self, result: FacilityResult) -> dict:
        embeds = [self.facility_embed(result)]
        if result.should_ping:
            embeds.append(self.new_windows_embed(window_lines(result.new_windows)))

        buttons = [link_button("Book here!", result.booking_url)] if result.booking_url else []
        return self._payload(embeds, buttons, ping=result.should_ping)

    def global_payloads(self, results: list[FacilityResult]) -> list[dict]:
        new_lines = [
            line
            for result in results
            if result.should_ping
            for line in window_lines(result.new_windows, prefix=f"**{result.facility.name}** · ")
        ]
        ping = bool(new_lines)

        # (embed, button or None); the new-windows embed goes first so the ping shows it.
        items: list[tuple[dict, dict | None]] = []
        if new_lines:
            items.append((self.new_windows_embed(new_lines), None))
        for result in results:
            button = link_button(result.facility.name, result.booking_url) if result.booking_url else None
            items.append((self.facility_embed(result), button))

        chunks: list[list[tuple[dict, dict | None]]] = [[]]
        size = 0
        for embed, button in items:
            current = chunks[-1]
            if current and (len(current) >= MAX_EMBEDS_PER_MESSAGE or size + embed_size(embed) > MAX_EMBED_CHARS_PER_MESSAGE):
                chunks.append([])
                size = 0
            chunks[-1].append((embed, button))
            size += embed_size(embed)

        return [
            self._payload(
                [embed for embed, _ in chunk],
                [button for _, button in chunk if button],
                ping=ping and index == 0,
            )
            for index, chunk in enumerate(chunks)
            if chunk
        ]

    @staticmethod
    def _payload(embeds: list[dict], buttons: list[dict], ping: bool) -> dict:
        return {
            "content": "@everyone" if ping else "",
            "embeds": embeds,
            "components": button_rows(buttons),
            "allowed_mentions": {"parse": ["everyone"]},
        }
