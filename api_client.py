from urllib.request import Request, urlopen


class APIClient:

    def __init__(self, user_agent: str = "Python-APIMonitor/2.0", headers: dict | None = None):
        self.user_agent = user_agent
        self.headers = headers or {}

    def fetch_data(self, url: str, timeout: int = 10) -> str:
        request_headers = {"User-Agent": self.user_agent}
        request_headers.update(self.headers)

        req = Request(url, headers=request_headers)
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
