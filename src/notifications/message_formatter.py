import calendar
import re
from datetime import date, datetime
from typing import Callable, Sequence

from availability import ALL_WEEKDAYS
from models.facility_result import FacilityResult
from models.free_window import FreeWindow

# Discord limits
MAX_EMBEDS_PER_MESSAGE = 10
MAX_EMBED_CHARS_PER_MESSAGE = 6000
MAX_DESCRIPTION = 4096
MAX_TITLE = 256
MAX_BUTTON_LABEL = 80
BUTTONS_PER_ROW = 5
MAX_BUTTON_ROWS = 5

REPORT_COLOR = 5793266
NEW_WINDOWS_COLOR = 15906135
FOOTER = "Monitor"
GLOBAL_TITLE = "Free courts"
NEW_WINDOWS_TITLE = "New free windows!"


def format_range(start: datetime, end: datetime) -> str:
    return f"{start:%H:%M}–{end:%H:%M}"


def day_label(day: date) -> str:
    return f"{calendar.day_name[day.weekday()]} {day:%d.%m}"


def weekdays_label(weekdays: Sequence[str]) -> str:
    if set(weekdays) >= set(ALL_WEEKDAYS):
        return "every day"
    ordered = [day for day in ALL_WEEKDAYS if day in weekdays]
    return ", ".join(day[:3] for day in ordered)


def natural_key(text: str) -> list:
    """Sort 'Court 2' before 'Court 10'."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


# (window, facility label shown after the hours or "" to omit it, facility position for sorting)
Entry = tuple[FreeWindow, str, int]


def facility_label(result: FacilityResult) -> str:
    """Facility name, as a markdown link to its booking page when there is one."""
    name = result.facility.name
    return f"[{name}]({result.booking_url})" if result.booking_url else name


def entries(windows: list[FreeWindow], facility: str = "", order: int = 0) -> list[Entry]:
    return [(window, facility, order) for window in windows]


def day_lines(items: list[Entry]) -> list[str]:
    """
    **Monday 23.11**
    - 16:30–19:00 · [Facility](url) · court 1

    Days in date order; within a day by time, then facility, then court.
    """
    ordered = sorted(
        items, key=lambda e: (e[0].start, e[0].end, e[2], natural_key(e[0].court_label))
    )
    lines: list[str] = []
    current_day: date | None = None
    for window, facility, _ in ordered:
        day = window.start.date()
        if day != current_day:
            lines.append(f"**{day_label(day)}**")
            current_day = day
        parts = [format_range(window.start, window.end), facility, window.court_label.lower()]
        lines.append("- " + " · ".join(part for part in parts if part))
    return lines


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


def split_lines(lines: list[str], limit: int) -> list[str]:
    """Pack lines into as few texts of at most `limit` chars as possible, never splitting a line."""
    texts: list[str] = []
    current: list[str] = []
    for line in lines:
        line = line[:limit]
        if current and len("\n".join([*current, line])) > limit:
            texts.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        texts.append("\n".join(current))
    return texts


def embed_size(embed: dict) -> int:
    """Characters that count towards Discord's 6000 per-message limit."""
    size = len(embed.get("title", "")) + len(embed.get("description", ""))
    size += len(embed.get("footer", {}).get("text", ""))
    size += sum(len(f["name"]) + len(f["value"]) for f in embed.get("fields", []))
    return size


def link_button(label: str, url: str) -> dict:
    return {"type": 2, "style": 5, "label": label[:MAX_BUTTON_LABEL], "url": url, "emoji": {"name": "🎾"}}


def button_rows(buttons: list[dict]) -> list[dict]:
    buttons = buttons[: BUTTONS_PER_ROW * MAX_BUTTON_ROWS]
    return [
        {"type": 1, "components": buttons[i : i + BUTTONS_PER_ROW]}
        for i in range(0, len(buttons), BUTTONS_PER_ROW)
    ]


class MessageFormatter:
    def __init__(self, weekdays: Sequence[str], now: Callable[[], str] | None = None):
        self.weekdays = list(weekdays)
        self._now = now or (lambda: datetime.now().astimezone().isoformat())

    # ---- embeds -----------------------------------------------------------

    def summary(self, count: int) -> str:
        if count:
            return f"Found {count} free window{'s' if count != 1 else ''} for: {weekdays_label(self.weekdays)}"
        return f"No free windows for: {weekdays_label(self.weekdays)}"

    def facility_embed(self, result: FacilityResult) -> dict:
        book = [f"[Book here!]({result.booking_url})"] if result.booking_url else []
        head = [self.summary(len(result.windows)), ""]
        body_limit = MAX_DESCRIPTION - len("\n".join([*head, *book])) - 2
        body = join_limited(day_lines(entries(result.windows)), body_limit)

        embed = {
            "title": result.facility.name[:MAX_TITLE],
            "description": "\n".join([*head, *([body, ""] if body else []), *book]).strip(),
            "color": REPORT_COLOR,
            "footer": {"text": FOOTER},
            "timestamp": self._now(),
        }
        if result.booking_url:
            embed["url"] = result.booking_url
        return embed

    def new_windows_embed(self, lines: list[str]) -> dict:
        return {
            "title": NEW_WINDOWS_TITLE,
            "description": join_limited(lines, MAX_DESCRIPTION),
            "color": NEW_WINDOWS_COLOR,
            "footer": {"text": FOOTER},
            "timestamp": self._now(),
        }

    def global_embeds(self, results: list[FacilityResult]) -> list[dict]:
        """All facilities merged into one list, then the booking links; split only to fit Discord limits."""
        total = sum(len(result.windows) for result in results)
        lines = [self.summary(total)]
        merged = [
            entry
            for order, result in enumerate(results)
            for entry in entries(result.windows, facility_label(result), order)
        ]
        if merged:
            lines += ["", *day_lines(merged)]

        links = [f"- [{result.facility.name}]({result.booking_url})" for result in results if result.booking_url]
        if links:
            lines += ["", "**Book:**", *links]

        embeds = [
            {"description": text, "color": REPORT_COLOR} for text in split_lines(lines, MAX_DESCRIPTION)
        ]
        embeds[0]["title"] = GLOBAL_TITLE
        embeds[-1]["footer"] = {"text": FOOTER}
        embeds[-1]["timestamp"] = self._now()
        return embeds

    # ---- payloads ---------------------------------------------------------

    def facility_payload(self, result: FacilityResult) -> dict:
        embeds = [self.facility_embed(result)]
        if result.should_ping:
            embeds.append(self.new_windows_embed(day_lines(entries(result.new_windows))))

        buttons = [link_button("Book here!", result.booking_url)] if result.booking_url else []
        return self._payload(embeds, buttons, ping=result.should_ping)

    def global_payloads(self, results: list[FacilityResult]) -> list[dict]:
        new_lines = day_lines([
            entry
            for order, result in enumerate(results)
            if result.should_ping
            for entry in entries(result.new_windows, facility_label(result), order)
        ])
        ping = bool(new_lines)

        # The new-windows embed goes first so the ping shows it.
        embeds = ([self.new_windows_embed(new_lines)] if new_lines else []) + self.global_embeds(results)

        chunks: list[list[dict]] = [[]]
        size = 0
        for embed in embeds:
            if chunks[-1] and (
                len(chunks[-1]) >= MAX_EMBEDS_PER_MESSAGE or size + embed_size(embed) > MAX_EMBED_CHARS_PER_MESSAGE
            ):
                chunks.append([])
                size = 0
            chunks[-1].append(embed)
            size += embed_size(embed)

        # Booking buttons sit under the last message, below the list.
        buttons = [link_button(r.facility.name, r.booking_url) for r in results if r.booking_url]
        return [
            self._payload(chunk, buttons if index == len(chunks) - 1 else [], ping=ping and index == 0)
            for index, chunk in enumerate(chunks)
        ]

    @staticmethod
    def _payload(embeds: list[dict], buttons: list[dict], ping: bool) -> dict:
        return {
            "content": "@everyone" if ping else "",
            "embeds": embeds,
            "components": button_rows(buttons),
            "allowed_mentions": {"parse": ["everyone"]},
        }
