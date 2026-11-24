from typing import Protocol

from logger import Logger
from models.facility_result import FacilityResult
from notifications.message_formatter import REPORT_COLORS, MessageFormatter
from settings import DiscordSettings


class Notifier(Protocol):
    def send(self, webhook_url: str, payload: dict) -> bool: ...


class NotificationDispatcher:
    def __init__(self, discord: DiscordSettings, notifier: Notifier, formatter: MessageFormatter):
        self.logger = Logger(name="DISPATCHER")
        self.discord = discord
        self.notifier = notifier
        self.formatter = formatter
        self._reports_sent: dict[str, int] = {}  # per channel, to alternate the report colour

    def _next_color(self, channel: str) -> int:
        """Light and dark blue in turn, per channel, so consecutive reports are easy to tell apart."""
        count = self._reports_sent.get(channel, 0)
        self._reports_sent[channel] = count + 1
        return REPORT_COLORS[count % len(REPORT_COLORS)]

    def dispatch(self, results: list[FacilityResult]) -> None:
        changed = [result.facility.key for result in results if result.changed]
        if not changed:
            self.logger.info("No changes in any facility, nothing to send.")
            return
        self.logger.info(f"Changes in: {', '.join(changed)} (mode={self.discord.mode}).")

        if self.discord.sends_per_facility:
            for result in results:
                if not result.changed:
                    continue
                webhook = self.discord.facility_webhook(result.facility.key)
                if webhook is None:
                    self.logger.error(f"No webhook configured for facility {result.facility.key!r}.")
                    continue
                self.logger.info(f"Sending {result.facility.key!r} report to its facility webhook.")
                self.notifier.send(webhook.get_secret_value(), self.formatter.facility_payload(result, self._next_color(result.facility.key)))

        if self.discord.sends_global:
            webhook = self.discord.global_webhook_url
            if webhook is None:
                self.logger.error("No global webhook configured.")
                return
            payloads = self.formatter.global_payloads(results, self._next_color("global"))
            self.logger.info(f"Sending global report ({len(payloads)} message(s)) to the global webhook.")
            for payload in payloads:
                self.notifier.send(webhook.get_secret_value(), payload)
