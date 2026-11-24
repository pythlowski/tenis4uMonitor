from datetime import datetime
from types import SimpleNamespace

import pytest

from models.facility_result import FacilityResult
from models.free_window import FreeWindow
from notifications.message_formatter import (
    MAX_EMBED_CHARS_PER_MESSAGE,
    MessageFormatter,
    embed_size,
    join_limited,
    weekdays_label,
)

URL = "https://app.tenis4u.pl/court/104"
NOW = "2026-11-23T12:00:00+01:00"
ALL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def w(day, start, end, court):
    sh, sm = start
    eh, em = end
    return FreeWindow(datetime(2026, 11, day, sh, sm), datetime(2026, 11, day, eh, em), court)


MON_A = w(23, (16, 30), (19, 0), "Badminton 1")
MON_B = w(23, (16, 30), (19, 0), "Badminton 2")
MON_C = w(23, (16, 30), (19, 0), "Badminton 3")
MON_D = w(23, (17, 30), (19, 0), "Badminton 4")
TUE_A = w(24, (18, 0), (20, 0), "Badminton 1")


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


class TestFacilityEmbed:
    def test_time_ranges_with_court_counts(self, formatter):
        embed = formatter.facility_embed(result([MON_A, MON_B, MON_C, MON_D]))
        assert embed["fields"] == [
            {"name": "Monday 23.11", "value": "- 16:30–19:00 · 3 courts\n- 17:30–19:00 · 1 court", "inline": False}
        ]

    def test_no_court_names_anywhere(self, formatter):
        payload = formatter.facility_payload(result([MON_A, TUE_A], new=[TUE_A]))
        assert "Badminton 1" not in str(payload)

    def test_groups_fields_by_day_in_order(self, formatter):
        embed = formatter.facility_embed(result([TUE_A, MON_A]))
        assert [f["name"] for f in embed["fields"]] == ["Monday 23.11", "Tuesday 24.11"]

    def test_title_link_and_description_use_booking_url(self, formatter):
        embed = formatter.facility_embed(result([MON_A]))
        assert embed["title"] == "Hala XYZ"
        assert embed["url"] == URL
        assert embed["description"] == f"Found 1 free window for: every day\n[Book here]({URL})"
        assert embed["footer"] == {"text": "Court Monitor"}

    def test_description_without_url(self, formatter):
        embed = formatter.facility_embed(result([MON_A, MON_B], url=""))
        assert embed["description"] == "Found 2 free windows for: every day"
        assert "url" not in embed

    def test_empty_state(self, formatter):
        embed = formatter.facility_embed(result([]))
        assert embed["description"].startswith("No free windows")
        assert embed["fields"] == []

    def test_weekday_label(self):
        assert weekdays_label(["Tuesday", "Monday"]) == "Mon, Tue"
        assert weekdays_label(ALL_DAYS) == "every day"


class TestFacilityPayload:
    def test_ping_and_new_windows_embed(self, formatter):
        payload = formatter.facility_payload(result([MON_A, MON_B], new=[MON_B]))
        assert payload["content"] == "@everyone"
        assert len(payload["embeds"]) == 2
        assert payload["embeds"][1]["description"] == "- Monday 23.11 16:30–19:00 · 1 court"
        assert payload["allowed_mentions"] == {"parse": ["everyone"]}

    def test_no_ping_without_new_windows(self, formatter):
        payload = formatter.facility_payload(result([MON_A]))
        assert payload["content"] == ""
        assert len(payload["embeds"]) == 1

    def test_baseline_never_pings(self, formatter):
        payload = formatter.facility_payload(result([MON_A], new=[MON_A], baseline=True))
        assert payload["content"] == ""
        assert len(payload["embeds"]) == 1

    def test_button_uses_booking_url(self, formatter):
        payload = formatter.facility_payload(result([MON_A]))
        button = payload["components"][0]["components"][0]
        assert button["url"] == URL and button["style"] == 5

    def test_no_button_without_url(self, formatter):
        assert formatter.facility_payload(result([MON_A], url=""))["components"] == []


class TestGlobalPayloads:
    def test_one_embed_per_facility_and_ping_with_facility_name(self, formatter):
        results = [
            result([MON_A], new=[MON_A], name="Hala XYZ", key="a"),
            result([TUE_A], changed=False, name="Blonia", key="b", url="https://app.twojtenis.pl/x"),
        ]
        [payload] = formatter.global_payloads(results)
        assert payload["content"] == "@everyone"
        titles = [e["title"] for e in payload["embeds"]]
        assert titles == ["New free windows!", "Hala XYZ", "Blonia"]
        assert payload["embeds"][0]["description"] == "- **Hala XYZ** · Monday 23.11 16:30–19:00 · 1 court"
        labels = [b["label"] for row in payload["components"] for b in row["components"]]
        assert labels == ["Hala XYZ", "Blonia"]

    def test_no_ping_when_only_baselines(self, formatter):
        [payload] = formatter.global_payloads([result([MON_A], new=[MON_A], baseline=True)])
        assert payload["content"] == ""
        assert [e["title"] for e in payload["embeds"]] == ["Hala XYZ"]

    def test_splits_above_ten_embeds(self, formatter):
        results = [result([MON_A], name=f"F{i}", key=f"f{i}") for i in range(12)]
        payloads = formatter.global_payloads(results)
        assert [len(p["embeds"]) for p in payloads] == [10, 2]
        for p in payloads:
            buttons = [b for row in p["components"] for b in row["components"]]
            assert len(buttons) == len(p["embeds"])
            assert all(len(row["components"]) <= 5 for row in p["components"])

    def test_ping_only_on_first_payload(self, formatter):
        results = [result([MON_A], new=[MON_A], name=f"F{i}", key=f"f{i}") for i in range(12)]
        payloads = formatter.global_payloads(results)
        assert [p["content"] for p in payloads] == ["@everyone", ""]

    def test_splits_at_6000_characters(self, formatter):
        # distinct start minutes per court -> nothing groups, so every field hits its 1024-char cap
        many = [w(d, (h, c), (h + 1, 0), f"c{c}") for d in range(23, 30) for h in range(16, 22) for c in range(20)]
        results = [result(many, name=f"Facility {i}", key=f"f{i}") for i in range(3)]
        payloads = formatter.global_payloads(results)
        assert len(payloads) == 3
        for p in payloads:
            assert sum(embed_size(e) for e in p["embeds"]) <= MAX_EMBED_CHARS_PER_MESSAGE
            assert "more day(s) not shown" in p["embeds"][0]["description"]


def test_join_limited_truncates_with_count():
    lines = [f"line {i}" for i in range(100)]
    text = join_limited(lines, 50)
    assert len(text) <= 50
    assert text.endswith("more")
