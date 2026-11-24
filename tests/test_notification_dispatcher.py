from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from models.facility_result import FacilityResult
from models.free_window import FreeWindow
from notifications.message_formatter import MessageFormatter
from notifications.notification_dispatcher import NotificationDispatcher
from settings import DiscordSettings

WINDOW = FreeWindow(datetime(2026, 11, 23, 17), datetime(2026, 11, 23, 19), "c1")


class FakeNotifier:
    def __init__(self):
        self.sent: list[tuple[str, dict]] = []

    def send(self, webhook_url, payload):
        self.sent.append((webhook_url, payload))
        return True


def result(key, changed):
    return FacilityResult(
        facility=SimpleNamespace(key=key, name=key.upper()),
        booking_url="https://book",
        windows=[WINDOW],
        changed=changed,
    )


def dispatcher(mode):
    discord = DiscordSettings(
        mode=mode,
        global_webhook_url=SecretStr("https://global"),
        facility={"a_webhook_url": SecretStr("https://a"), "b_webhook_url": SecretStr("https://b")},
    )
    notifier = FakeNotifier()
    return NotificationDispatcher(discord, notifier, MessageFormatter(["Monday"])), notifier


@pytest.mark.parametrize(
    "mode, expected",
    [
        ("global", ["https://global"]),
        ("per_facility", ["https://a"]),
        ("both", ["https://a", "https://global"]),
    ],
)
def test_routing_per_mode(mode, expected):
    d, notifier = dispatcher(mode)
    d.dispatch([result("a", changed=True), result("b", changed=False)])
    assert [url for url, _ in notifier.sent] == expected


@pytest.mark.parametrize("mode", ["global", "per_facility", "both"])
def test_nothing_sent_without_changes(mode):
    d, notifier = dispatcher(mode)
    d.dispatch([result("a", changed=False), result("b", changed=False)])
    assert notifier.sent == []


def test_global_includes_unchanged_facilities_when_one_changed():
    d, notifier = dispatcher("global")
    d.dispatch([result("a", changed=False), result("b", changed=True)])
    [(_, payload)] = notifier.sent
    assert [e["title"] for e in payload["embeds"]] == ["A", "B"]
