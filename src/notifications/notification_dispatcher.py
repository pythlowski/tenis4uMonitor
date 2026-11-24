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
        if self.discord.sends_per_facility:
            for result in results:
                if not result.changed:
                    continue
                webhook = self.discord.facility_webhook(result.facility.key)
                if webhook is None:
                    self.logger.error(f"No webhook configured for facility {result.facility.key!r}.")
                    continue
                self.notifier.send(webhook.get_secret_value(), self.formatter.facility_payload(result))

        if self.discord.sends_global and any(result.changed for result in results):
            webhook = self.discord.global_webhook_url
            if webhook is None:
                self.logger.error("No global webhook configured.")
                return
            for payload in self.formatter.global_payloads(results):
                self.notifier.send(webhook.get_secret_value(), payload)
