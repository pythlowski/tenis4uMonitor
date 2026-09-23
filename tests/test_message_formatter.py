import datetime

import pytest

from models.free_slot import FreeSlot
from models.snapshot import Snapshot
from message_formatter import MessageFormatter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

URL = "https://app.tenis4u.pl/court/104"

MONDAY_SLOT    = FreeSlot(courtName="Court A", date=datetime.datetime(2026, 9, 21, 17,  0))  # Monday
MONDAY_SLOT_2  = FreeSlot(courtName="Court B", date=datetime.datetime(2026, 9, 21, 17, 30))  # Monday
TUESDAY_SLOT   = FreeSlot(courtName="Court A", date=datetime.datetime(2026, 9, 22, 18,  0))  # Tuesday


def _snapshot(*slots: FreeSlot) -> Snapshot:
    return Snapshot(weekdays=["Monday", "Tuesday"], free_slots=list(slots))


# ===========================================================================
# _get_new_slots_description
# ===========================================================================

class TestGetNewSlotsDescription:
    def test_single_slot_format(self):
        desc = MessageFormatter._get_new_slots_description([MONDAY_SLOT])
        assert "- Monday 21.09 17:00 - Court A" in desc

    def test_multiple_slots_are_separated_by_newlines(self):
        desc = MessageFormatter._get_new_slots_description([MONDAY_SLOT, TUESDAY_SLOT])
        lines = desc.splitlines()
        assert len(lines) == 2

    def test_empty_list_returns_empty_string(self):
        assert MessageFormatter._get_new_slots_description([]) == ""


# ===========================================================================
# _get_fields
# ===========================================================================

class TestGetFields:
    def test_single_slot_produces_one_field(self):
        fields = MessageFormatter._get_fields([MONDAY_SLOT])
        assert len(fields) == 1

    def test_slots_on_same_day_are_grouped_into_one_field(self):
        fields = MessageFormatter._get_fields([MONDAY_SLOT, MONDAY_SLOT_2])
        assert len(fields) == 1
        value = fields[0]["value"]
        assert "17:00" in value
        assert "17:30" in value

    def test_slots_on_different_days_produce_separate_fields(self):
        fields = MessageFormatter._get_fields([MONDAY_SLOT, TUESDAY_SLOT])
        assert len(fields) == 2

    def test_field_name_contains_weekday_and_date(self):
        fields = MessageFormatter._get_fields([MONDAY_SLOT])
        assert "Monday" in fields[0]["name"]
        assert "21.09" in fields[0]["name"]

    def test_fields_are_not_inline(self):
        fields = MessageFormatter._get_fields([MONDAY_SLOT])
        assert fields[0]["inline"] is False

    def test_slots_sorted_by_date_then_court_name(self):
        # TUESDAY_SLOT comes after MONDAY_SLOT even though it's passed second
        fields = MessageFormatter._get_fields([TUESDAY_SLOT, MONDAY_SLOT])
        assert "Monday" in fields[0]["name"]
        assert "Tuesday" in fields[1]["name"]

    def test_empty_list_returns_empty_fields(self):
        assert MessageFormatter._get_fields([]) == []


# ===========================================================================
# get_payload
# ===========================================================================

class TestGetPayload:
    def test_everyone_mention_present_when_new_slots_exist(self):
        snapshot = _snapshot(MONDAY_SLOT)
        payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=[MONDAY_SLOT], url=URL)
        assert payload["content"] == "@everyone"

    def test_everyone_mention_absent_when_no_new_slots(self):
        snapshot = _snapshot(MONDAY_SLOT)
        payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=[], url=URL)
        assert payload["content"] == ""

    def test_two_embeds_when_new_slots_present(self):
        snapshot = _snapshot(MONDAY_SLOT)
        payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=[MONDAY_SLOT], url=URL)
        assert len(payload["embeds"]) == 2

    def test_one_embed_when_no_new_slots(self):
        snapshot = _snapshot(MONDAY_SLOT)
        payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=[], url=URL)
        assert len(payload["embeds"]) == 1

    def test_components_present_when_url_provided(self):
        snapshot = _snapshot(MONDAY_SLOT)
        payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=[], url=URL)
        assert len(payload["components"]) == 1

    def test_components_empty_when_no_url(self):
        snapshot = _snapshot(MONDAY_SLOT)
        payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=[], url=None)
        assert payload["components"] == []

    def test_allowed_mentions_always_present(self):
        snapshot = _snapshot(MONDAY_SLOT)
        payload = MessageFormatter.get_payload(snapshot=snapshot, new_slots=[], url=URL)
        assert payload["allowed_mentions"] == {"parse": ["everyone"]}

