import datetime
import time
from typing import Callable

from availability import AvailabilityComputer
from http_client import HttpClient
from logger import Logger
from models.facility_result import FacilityResult
from models.facility_snapshot import FacilitySnapshot
from notifications.discord_notifier import DiscordNotifier
from notifications.message_formatter import MessageFormatter
from notifications.notification_dispatcher import NotificationDispatcher
from providers import create_provider, provider_class
from providers.base import SlotProvider
from proxy_background_service import ProxyBackgroundService
from settings import FacilityConfig, Settings
from snapshots_comparator import SnapshotsComparator
from snapshots_repository import SnapshotRepository


class MonitorService:

    def __init__(
        self,
        settings: Settings,
        http: HttpClient | None = None,
        providers: dict[str, SlotProvider] | None = None,
        repository: SnapshotRepository | None = None,
        comparator: SnapshotsComparator | None = None,
        dispatcher: NotificationDispatcher | None = None,
        today: Callable[[], datetime.date] = datetime.date.today,
    ):
        self.logger = Logger(name="MONITOR")
        self.settings = settings
        self._http = http  # when given, used for every provider (tests)
        self._proxied_http: HttpClient | None = None
        self._direct_http: HttpClient | None = None
        self.providers: dict[str, SlotProvider] = dict(providers or {})
        self.repository = repository or SnapshotRepository()
        self.comparator = comparator or SnapshotsComparator()
        self.computer = AvailabilityComputer(settings.filters)
        self.dispatcher = dispatcher or NotificationDispatcher(
            settings.discord, DiscordNotifier(), MessageFormatter(settings.weekdays)
        )
        self._today = today

    def run_once(self) -> list[FacilityResult]:
        date_from = self._today()
        date_to = date_from + datetime.timedelta(days=self.settings.days_ahead - 1)

        results: list[FacilityResult] = []
        for facility in self.settings.facilities:
            try:
                results.append(self._process(facility, date_from, date_to))
            except Exception as err:
                # Skip this facility; its previous snapshot stays untouched.
                self.logger.exception(f"[{facility.key}] Failed to process facility: {err}")

        if results:
            self.dispatcher.dispatch(results)
        return results

    def _process(self, facility: FacilityConfig, date_from: datetime.date, date_to: datetime.date) -> FacilityResult:
        provider = self._provider(facility.provider)
        courts = provider.fetch_availability(facility, date_from, date_to)
        windows = self.computer.compute(courts)
        self.logger.info(f"[{facility.key}] Found {len(windows)} free windows.")

        new_snapshot = FacilitySnapshot(
            facility_key=facility.key,
            taken_at=datetime.datetime.now().astimezone(),
            windows=windows,
        )
        old_snapshot = self.repository.get(facility.key)
        diff = self.comparator.get_diff(old=old_snapshot, new=new_snapshot)
        self.repository.save(new_snapshot)

        return FacilityResult(
            facility=facility,
            booking_url=facility.booking_url or provider.booking_url(facility),
            windows=windows,
            new_windows=diff.new_windows,
            changed=diff.changed,
            is_baseline=diff.is_baseline,
        )

    def _provider(self, name: str) -> SlotProvider:
        if name not in self.providers:
            self.providers[name] = create_provider(name, self._http_for(provider_class(name).USES_PROXY))
        return self.providers[name]

    def prepare_providers(self) -> None:
        """Create the configured providers up front, so the proxy pool starts collecting at app start."""
        for name in dict.fromkeys(facility.provider for facility in self.settings.facilities):
            self._provider(name)

    def _http_for(self, uses_proxy: bool) -> HttpClient:
        """Proxy pool only for providers that need it; created together with the first such provider."""
        if self._http is not None:
            return self._http
        if not uses_proxy:
            self._direct_http = self._direct_http or HttpClient()
            return self._direct_http
        if self._proxied_http is None:
            self._proxied_http = HttpClient(ProxyBackgroundService(max_proxies_ready=self.settings.max_proxies_ready))
        return self._proxied_http

    def _seconds_until_next_slot(self) -> float:
        """Return the number of seconds to sleep until the next even interval boundary.

        For example, with fetch_interval_minutes=20 the scheduled times are
        XX:00, XX:20 and XX:40 (relative to the top of each hour).
        """
        interval = self.settings.fetch_interval_minutes * 60  # seconds
        now = datetime.datetime.now()
        elapsed_in_hour = now.minute * 60 + now.second + now.microsecond / 1_000_000
        remainder = elapsed_in_hour % interval
        return interval - remainder if remainder != 0 else interval

    def start(self) -> None:
        self.prepare_providers()
        interval_minutes = self.settings.fetch_interval_minutes
        sleep_for = self._seconds_until_next_slot()
        self.logger.info(
            f"Waiting {sleep_for:.1f}s until next scheduled slot "
            f"(interval: every {interval_minutes} minutes on even boundaries)."
        )
        time.sleep(sleep_for)

        while True:
            started = time.monotonic()
            try:
                self.logger.info("Monitor run started...")
                self.run_once()
            except Exception as err:
                self.logger.exception("Unexpected error during execution: %s", err)

            elapsed = time.monotonic() - started

            sleep_for = max(0, interval_minutes * 60 - elapsed)
            self.logger.info(f"Elapsed time: {elapsed:.2f}s. Sleeping for {sleep_for:.2f}s.")
            time.sleep(sleep_for)
