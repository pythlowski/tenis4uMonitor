from typing import Protocol

from logger import Logger
from models.facility_result import FacilityResult
from notifications.message_formatter import MessageFormatter
from settings import DiscordSettings


class Notifier(Protocol):
    def send(self, webhook_url: str, payload: dict) -> bool: ...


class NotificationDispatcher:
    def __init__(self, discord: DiscordSettings, notifier: Notifier, formatter: MessageFormatter):
        self.logger = Logger(name="DISPATCHER")
        self.discord = discord
        self.notifier = notifier
        self.formatter = formatter

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
                self.notifier.send(webhook.get_secret_value(), self.formatter.facility_payload(result))

        if self.discord.sends_global:
            webhook = self.discord.global_webhook_url
            if webhook is None:
                self.logger.error("No global webhook configured.")
                return
            payloads = self.formatter.global_payloads(results)
            self.logger.info(f"Sending global report ({len(payloads)} message(s)) to the global webhook.")
            for payload in payloads:
                self.notifier.send(webhook.get_secret_value(), payload)
