from datetime import datetime
from types import SimpleNamespace

import pytest

from models.facility_result import FacilityResult
from models.free_window import FreeWindow
from notifications.message_formatter import (
    FOOTER,
    GLOBAL_TITLE,
    MAX_DESCRIPTION,
    MAX_EMBED_CHARS_PER_MESSAGE,
    NEW_WINDOWS_TITLE,
    MessageFormatter,
    day_lines,
    entries,
    embed_size,
    join_limited,
    split_lines,
    weekdays_label,
)

URL = "https://app.tenis4u.pl/court/104"
URL_B = "https://app.twojtenis.pl/x"
NOW = "2026-11-23T12:00:00+01:00"
ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def w(day, start, end, court, name=None):
    sh, sm = start
    eh, em = end
    return FreeWindow(datetime(2026, 11, day, sh, sm), datetime(2026, 11, day, eh, em), court, name or court)


MON_1 = w(23, (16, 30), (19, 0), "c1", "Court 1")
MON_1_LATE = w(23, (20, 0), (22, 30), "c1", "Court 1")
MON_2 = w(23, (17, 30), (19, 0), "c2", "Court 2")
MON_10 = w(23, (18, 0), (19, 0), "c10", "Court 10")
TUE_1 = w(24, (18, 0), (20, 0), "c1", "Court 1")


def result(windows=(), new=(), changed=True, baseline=False, name="Hala XYZ", key="hala", url=URL):
    return FacilityResult(
        facility=SimpleNamespace(key=key, name=name),
        booking_url=url,
        windows=list(windows),
        new_windows=list(new),
        changed=changed,
        is_baseline=baseline,
    )


@pytest.fixture
def formatter():
    return MessageFormatter(weekdays=ALL_DAYS, now=lambda: NOW)


class TestDayLines:
    def test_groups_by_date_then_sorts_by_time_and_court(self):
        assert day_lines(entries([TUE_1, MON_1_LATE, MON_2, MON_1])) == [
            "**Monday 23.11**",
            "- 16:30–19:00 · court 1",
            "- 17:30–19:00 · court 2",
            "- 20:00–22:30 · court 1",
            "**Tuesday 24.11**",
            "- 18:00–20:00 · court 1",
        ]

    def test_same_time_courts_in_natural_order(self):
        same = [w(23, (18, 0), (19, 0), f"c{n}", f"Court {n}") for n in (10, 2, 1)]
        assert day_lines(entries(same))[1:] == ["- 18:00–19:00 · court 1", "- 18:00–19:00 · court 2", "- 18:00–19:00 · court 10"]

    def test_facility_between_hours_and_court(self):
        assert day_lines(entries([MON_1], "Hala"))[1] == "- 16:30–19:00 · Hala · court 1"

    def test_same_time_sorted_by_facility_order(self):
        items = entries([MON_10], "B", order=1) + entries([MON_10], "A", order=0)
        assert day_lines(items)[1:] == ["- 18:00–19:00 · A · court 10", "- 18:00–19:00 · B · court 10"]

    def test_falls_back_to_court_id_without_name(self):
        unnamed = FreeWindow(datetime(2026, 11, 23, 17), datetime(2026, 11, 23, 18), "Badminton 3")
        assert day_lines(entries([unnamed]))[1] == "- 17:00–18:00 · badminton 3"


class TestFacilityEmbed:
    def test_lists_courts_then_booking_link(self, formatter):
        embed = formatter.facility_embed(result([MON_1, MON_2]))
        lines = embed["description"].split("\n")
        assert lines[0] == "Found 2 free windows for: every day"
        assert lines[2:5] == ["**Monday 23.11**", "- 16:30–19:00 · court 1", "- 17:30–19:00 · court 2"]
        assert lines[-1].startswith("[Book") and lines[-1].endswith(f"]({URL})")

    def test_title_url_and_footer(self, formatter):
        embed = formatter.facility_embed(result([MON_1]))
        assert embed["title"] == "Hala XYZ"
        assert embed["url"] == URL
        assert embed["footer"] == {"text": FOOTER}

    def test_without_url(self, formatter):
        embed = formatter.facility_embed(result([MON_1], url=""))
        assert "Book" not in embed["description"]
        assert "url" not in embed

    def test_empty_state(self, formatter):
        embed = formatter.facility_embed(result([]))
        assert embed["description"].startswith("No free windows")
        assert "**" not in embed["description"]

    def test_long_list_is_truncated_but_keeps_booking_link(self, formatter):
        many = [w(d, (16, m), (22, 0), f"c{c}", f"Court {c}") for d in range(23, 30) for c in range(40) for m in (0,)]
        embed = formatter.facility_embed(result(many))
        assert len(embed["description"]) <= MAX_DESCRIPTION
        assert "more" in embed["description"]
        assert embed["description"].endswith(f"]({URL})")

    def test_weekday_label(self):
        assert weekdays_label(["Tuesday", "Monday"]) == "Mon, Tue"
        assert weekdays_label(ALL_DAYS) == "every day"


class TestFacilityPayload:
    def test_new_windows_show_court_and_full_range(self, formatter):
        payload = formatter.facility_payload(result([MON_1, MON_2], new=[MON_2]))
        assert payload["content"] == "@everyone"
        assert payload["embeds"][1]["title"] == NEW_WINDOWS_TITLE
        assert payload["embeds"][1]["description"] == "**Monday 23.11**\n- 17:30–19:00 · court 2"
        assert payload["allowed_mentions"] == {"parse": ["everyone"]}

    def test_no_ping_without_new_windows(self, formatter):
        payload = formatter.facility_payload(result([MON_1]))
        assert payload["content"] == ""
        assert len(payload["embeds"]) == 1

    def test_baseline_never_pings(self, formatter):
        payload = formatter.facility_payload(result([MON_1], new=[MON_1], baseline=True))
        assert payload["content"] == ""
        assert len(payload["embeds"]) == 1

    def test_button_uses_booking_url(self, formatter):
        payload = formatter.facility_payload(result([MON_1]))
        button = payload["components"][0]["components"][0]
        assert button["url"] == URL and button["style"] == 5

    def test_no_button_without_url(self, formatter):
        assert formatter.facility_payload(result([MON_1], url=""))["components"] == []


class TestGlobalPayloads:
    def test_merges_all_facilities_into_one_embed_with_links_below(self, formatter):
        results = [
            result([MON_1], name="Hala XYZ", key="a"),
            result([TUE_1], changed=False, name="Blonia", key="b", url=URL_B),
        ]
        [payload] = formatter.global_payloads(results)
        [embed] = payload["embeds"]
        assert embed["title"] == GLOBAL_TITLE
        assert embed["description"].split("\n") == [
            "Found 2 free windows for: every day",
            "",
            "**Monday 23.11**",
            f"- 16:30–19:00 · [Hala XYZ]({URL}) · court 1",
            "**Tuesday 24.11**",
            f"- 18:00–20:00 · [Blonia]({URL_B}) · court 1",
            "",
            "**Book:**",
            f"- [Hala XYZ]({URL})",
            f"- [Blonia]({URL_B})",
        ]
        labels = [b["label"] for row in payload["components"] for b in row["components"]]
        assert labels == ["Hala XYZ", "Blonia"]

    def test_facility_name_is_plain_without_url(self, formatter):
        [payload] = formatter.global_payloads([result([MON_1], name="Hala", url="")])
        assert "- 16:30–19:00 · Hala · court 1" in payload["embeds"][0]["description"]

    def test_new_windows_show_facility_court_and_range(self, formatter):
        results = [
            result([MON_1], new=[MON_1], name="Hala XYZ", key="a"),
            result([TUE_1], new=[TUE_1], name="Blonia", key="b", url=URL_B),
        ]
        [payload] = formatter.global_payloads(results)
        assert payload["content"] == "@everyone"
        assert [e.get("title") for e in payload["embeds"]] == [NEW_WINDOWS_TITLE, GLOBAL_TITLE]
        assert payload["embeds"][0]["description"].split("\n") == [
            "**Monday 23.11**",
            f"- 16:30–19:00 · [Hala XYZ]({URL}) · court 1",
            "**Tuesday 24.11**",
            f"- 18:00–20:00 · [Blonia]({URL_B}) · court 1",
        ]

    def test_no_ping_when_only_baselines(self, formatter):
        [payload] = formatter.global_payloads([result([MON_1], new=[MON_1], baseline=True)])
        assert payload["content"] == ""
        assert [e["title"] for e in payload["embeds"]] == [GLOBAL_TITLE]

    def test_splits_long_lists_within_discord_limits(self, formatter):
        many = [w(d, (h, 0), (h + 1, 0), f"c{c}", f"Court {c}") for d in range(23, 30) for h in (16, 18, 20) for c in range(12)]
        results = [result(many, new=many, name=f"Facility {i}", key=f"f{i}") for i in range(4)]
        payloads = formatter.global_payloads(results)
        assert len(payloads) > 1
        assert [p["content"] for p in payloads] == ["@everyone"] + [""] * (len(payloads) - 1)
        for p in payloads:
            assert len(p["embeds"]) <= 10
            assert sum(embed_size(e) for e in p["embeds"]) <= MAX_EMBED_CHARS_PER_MESSAGE
            assert all(len(e["description"]) <= MAX_DESCRIPTION for e in p["embeds"])
        # buttons and booking links come last, after every slot
        assert all(p["components"] == [] for p in payloads[:-1])
        assert payloads[-1]["components"]
        assert payloads[-1]["embeds"][-1]["description"].endswith(f"- [Facility 3]({URL})")
        # nothing from the merged list is lost when splitting
        text = "\n".join(e["description"] for p in payloads for e in p["embeds"] if e.get("title") != NEW_WINDOWS_TITLE)
        assert text.count("](https://") - 4 == len(many) * 4  # every slot line + 4 booking links

    def test_at_most_25_buttons(self, formatter):
        results = [result([], name=f"F{i}", key=f"f{i}") for i in range(30)]
        payloads = formatter.global_payloads(results)
        rows = payloads[-1]["components"]
        assert len(rows) == 5 and all(len(row["components"]) == 5 for row in rows)


def test_split_lines_never_exceeds_limit():
    lines = [f"line {i}" for i in range(100)]
    texts = split_lines(lines, 50)
    assert all(len(t) <= 50 for t in texts)
    assert "\n".join(texts).split("\n") == lines


def test_join_limited_truncates_with_count():
    lines = [f"line {i}" for i in range(100)]
    text = join_limited(lines, 50)
    assert len(text) <= 50
    assert text.endswith("more")
