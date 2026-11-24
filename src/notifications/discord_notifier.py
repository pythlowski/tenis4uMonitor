import time
from typing import Callable

import requests

from logger import Logger


class DiscordNotifier:
    def __init__(
        self,
        timeout: float = 10,
        max_retries: int = 5,
        base_delay: float = 1.0,
        post: Callable[..., requests.Response] = requests.post,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.logger = Logger(name="DISCORD")
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._post = post
        self._sleep = sleep

    def send(self, webhook_url: str, payload: dict) -> bool:
        for attempt in range(self.max_retries):
            try:
                response = self._post(webhook_url, json=payload, timeout=self.timeout)

                if response.status_code in (200, 204):
                    self.logger.info("Message sent.")
                    return True

                if response.status_code == 429:
                    delay = self._retry_after(response, self.base_delay)
                    self.logger.warning(f"Rate limited, retrying in {delay:.2f}s.")
                    self._sleep(delay)
                    continue

                self.logger.error(f"HTTP {response.status_code}: {response.text}")
                return False

            except requests.exceptions.ConnectionError:
                self.logger.error(f"Connection failed (attempt {attempt + 1}/{self.max_retries}).")
            except requests.exceptions.Timeout:
                self.logger.error(f"Request timed out (attempt {attempt + 1}/{self.max_retries}).")

            # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            self._sleep(self.base_delay * (2 ** attempt))

        self.logger.error("All retry attempts exhausted.")
        return False

    @staticmethod
    def _retry_after(response: requests.Response, default: float) -> float:
        try:
            return float(response.json().get("retry_after", default))
        except (ValueError, AttributeError, TypeError):
            pass
        try:
            return float(response.headers.get("Retry-After", default))
        except (AttributeError, TypeError, ValueError):
            return default
