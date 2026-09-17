import threading
import queue
import time
import requests

from settings import ApiSettings

class ProxyBackgroundService:
    def __init__(self, api_settings: ApiSettings):
        self.ready_proxies: queue.Queue[str] = queue.Queue(maxsize=api_settings.max_proxies_ready)
        self.untested_proxies: queue.Queue[str] = queue.Queue()
        
        self.is_running = True
        
        self.worker_thread = threading.Thread(target=self._test_proxies_loop, daemon=True)
        self.worker_thread.start()

    def get_proxy(self, timeout=30) -> dict[str, str]:
        return self.ready_proxies.get(block=True, timeout=timeout)

    def stop(self):
        self.is_running = False

    def _test_proxies_loop(self):
        while self.is_running:
            if self.ready_proxies.full():
                time.sleep(1)
                continue

            if self.untested_proxies.empty():
                print("[Background] Fetching new batch of untested proxies...")
                raw_proxies = self._fetch_raw_proxies()
                for proxy in raw_proxies:
                    self.untested_proxies.put(proxy) # Add them to the queue
                
                if self.untested_proxies.empty():
                    time.sleep(5)
                    continue

            try:
                untested_proxy = self.untested_proxies.get(block=False)
            except queue.Empty:
                continue

            if self._is_proxy_working(untested_proxy):
                self.ready_proxies.put(untested_proxy)
                print(f"[Background] Added proxy! Ready to use: {self.ready_proxies.qsize()}/{self.ready_proxies.maxsize}")

    def _fetch_raw_proxies(self):
        try:
            url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000"
            response = requests.get(url, timeout=10)
            return response.text.strip().split('\r\n')
        except:
            return []

    def _is_proxy_working(self, proxy_ip: str) -> bool:
        """Test if the proxy actually works."""
        proxy_dict = {"http": f"http://{proxy_ip}", "https": f"http://{proxy_ip}"}
        try:
            # Short timeout is critical for testing
            requests.get("https://httpbin.org/ip", proxies=proxy_dict, timeout=3)
            return True
        except requests.RequestException:
            return False


if __name__ == "__main__":
    proxyService = ProxyBackgroundService()
    proxy = proxyService.get_proxy()
    print(f"Using proxy: {proxy}")