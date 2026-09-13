import random
import requests
from proxies import get_working_proxies

class APIClient:

    def __init__(self, user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36", headers: dict | None = None):
        self.user_agent = user_agent
        self.headers = headers or {}

    def fetch_data(self, url: str, timeout: int = 10) -> str:
        request_headers = {"User-Agent": self.user_agent}
        request_headers.update(self.headers)

        proxies = self.get_proxies()

        response = requests.get(
            url, 
            headers=request_headers, 
            proxies=proxies, 
            timeout=timeout
        )

        return response.text

    def get_proxies(self) -> list[dict[str, str]]:
        working_proxies = get_working_proxies(max_working=3)
        random_proxies_idx = random.randint(0, len(working_proxies) - 1)
        return working_proxies[random_proxies_idx]