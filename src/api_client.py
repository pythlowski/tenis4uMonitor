import requests

from proxy_background_service import ProxyBackgroundService
from settings import ApiSettings
from logger import Logger

class APIClient:

    def __init__(self, api_settings: ApiSettings, user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"):
        self.logger = Logger(name="API_CLIENT")
        self.proxy_service = ProxyBackgroundService(api_settings=api_settings)
        self.user_agent = user_agent
        self.headers = api_settings.headers or {}

    def fetch_data(self, url: str, timeout: int = 10, max_retries: int = 5) -> str:
        request_headers = {"User-Agent": self.user_agent}
        request_headers.update(self.headers)

        for attempt in range(max_retries):
            try:
                return self._fetch_with_proxy(url, request_headers, timeout)
            except requests.RequestException as e:
                self.logger.error(f"[Attempt {attempt + 1}/{max_retries}] Request failed: {e}")
                if attempt == max_retries - 1:
                    raise
                else:
                    self.logger.info("Retrying with a new proxy...")

    def _fetch_with_proxy(self, url: str, headers: dict, timeout: int) -> str:
        proxy = self.proxy_service.get_proxy()
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}

        response = requests.get(
            url, 
            headers=headers, 
            proxies=proxies, 
            timeout=timeout
        )

        return response.text