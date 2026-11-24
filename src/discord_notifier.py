import time

import requests

from logger import Logger


class DiscordNotifier:
    def __init__(self, webhook_url: str, timeout: float = 10):
        self.logger = Logger(name="DISCORD")
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send_alert(self, payload: dict | None = None, max_retries=5, base_delay=1.0):
        payload = payload or {}

        for attempt in range(max_retries):
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=self.timeout)

                if response.status_code in (200, 204):
                    self.logger.info("Message sent.")
                    return True

                if response.status_code == 429:
                    time.sleep(self._retry_after(response, base_delay))
                    continue

                if response.status_code >= 400:
                    self.logger.error(f"HTTP {response.status_code}: {response.text}")
                    return False

            except requests.exceptions.ConnectionError:
                self.logger.error(f"Connection failed (attempt {attempt + 1}/{max_retries}).")
            except requests.exceptions.Timeout:
                self.logger.error(f"Request timed out (attempt {attempt + 1}/{max_retries}).")

            # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            time.sleep(base_delay * (2 ** attempt))

        self.logger.error("All retry attempts exhausted.")
        return False

    @staticmethod
    def _retry_after(response: requests.Response, default: float) -> float:
        try:
            return float(response.json().get("retry_after", default))
        except (ValueError, AttributeError):
            pass
        try:
            return float(response.headers.get("Retry-After", default))
        except (TypeError, ValueError):
            return default
