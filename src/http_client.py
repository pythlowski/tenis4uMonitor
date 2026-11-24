from typing import Callable, Protocol

import requests

from logger import Logger


class ProxyProvider(Protocol):
    def get_proxy(self, timeout: float = 30) -> str: ...


class HttpClient:
    """HTTP GET with retries; through a fresh proxy per attempt when a proxy service is given."""

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        proxy_service: ProxyProvider | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 10,
        max_retries: int = 5,
        request_get: Callable[..., requests.Response] = requests.get,
    ):
        self.logger = Logger(name="HTTP_CLIENT")
        self.proxy_service = proxy_service
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self._get = request_get

    def get(self, url: str, headers: dict[str, str] | None = None, params: dict | None = None) -> str:
        request_headers = {"User-Agent": self.user_agent, **(headers or {})}

        for attempt in range(1, self.max_retries + 1):
            try:
                return self._get_once(url, request_headers, params)
            except requests.RequestException as e:
                self.logger.error(f"[Attempt {attempt}/{self.max_retries}] GET {url} failed: {e}")
                if attempt == self.max_retries:
                    raise
                self.logger.info("Retrying with a new proxy..." if self.proxy_service else "Retrying...")

        raise AssertionError("unreachable")

    def _get_once(self, url: str, headers: dict[str, str], params: dict | None) -> str:
        proxies = None
        if self.proxy_service is not None:
            proxy = self.proxy_service.get_proxy()
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}

        response = self._get(url, headers=headers, params=params, proxies=proxies, timeout=self.timeout)
        response.raise_for_status()
        return response.text
