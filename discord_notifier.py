from datetime import time

import requests

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, message: str, max_retries=5, base_delay=1.0):
        payload = {
            "content": message
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(self.webhook_url, json=payload)

                if response.status_code == 204:
                    return True

                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", base_delay)
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 400:
                    print(f"HTTP {response.status_code}: {response.text}")
                    return False

            except requests.exceptions.ConnectionError:
                print(f"Connection failed (attempt {attempt + 1}/{max_retries})")
            except requests.exceptions.Timeout:
                print(f"Request timed out (attempt {attempt + 1}/{max_retries})")
            except requests.exceptions.HTTPError as e:
                print(f"HTTP error: {e}")
                return False

            # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)

        print("All retry attempts exhausted.")
        return False
