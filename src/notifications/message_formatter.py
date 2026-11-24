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
NO_WINDOWS = "No free windows."


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


def short_court_name(name: str) -> str:
    """Initials of the words plus the number in the name: 'Badminton 1' -> 'B1', 'Padel Hala 1' -> 'PH1'.

    Names without a number are kept as they are.
    """
    number = re.search(r"\d+", name)
    if not number:
        return name
    initials = "".join(word[0].upper() for word in name.split() if not word[0].isdigit())
    return f"{initials}{number.group()}"


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
    - 16:00–17:00 · [Błonia Sport](url) (b1, b2), [Fame Sport Club](url) (b4)    with facilities (global channel)
    - 16:00–17:00 · badminton 1, badminton 2                                     without them

    Court names are abbreviated only next to a facility, to keep the merged list short.

    One line per distinct time range; days in date order, ranges by time, then facilities, then courts.
    """
    ranges: dict[tuple[datetime, datetime], dict[tuple[int, str], list[str]]] = {}
    for window, facility, order in items:
        courts = ranges.setdefault((window.start, window.end), {}).setdefault((order, facility), [])
        courts.append((short_court_name(window.court_name) if facility else window.court_name).lower())

    lines: list[str] = []
    current_day: date | None = None
    for (start, end), facilities in sorted(ranges.items()):
        if start.date() != current_day:
            current_day = start.date()
            lines.append(f"**{day_label(current_day)}**")
        places = []
        for (_, facility), courts in sorted(facilities.items(), key=lambda item: item[0][0]):
            names = ", ".join(sorted(dict.fromkeys(courts), key=natural_key))
            places.append(f"{facility} ({names})" if facility else names)
        lines.append(f"- {format_range(start, end)} · {', '.join(places)}")
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

    def facility_embed(self, result: FacilityResult) -> dict:
        book = [f"[Book here!]({result.booking_url})"] if result.booking_url else []
        body_limit = MAX_DESCRIPTION - len("\n".join(book)) - 2
        body = join_limited(day_lines(entries(result.windows)), body_limit) or NO_WINDOWS

        embed = {
            "title": result.facility.name[:MAX_TITLE],
            "description": "\n".join([body, *([""] + book if book else [])]),
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
        merged = [
            entry
            for order, result in enumerate(results)
            for entry in entries(result.windows, facility_label(result), order)
        ]
        lines = day_lines(merged) or [NO_WINDOWS]

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
