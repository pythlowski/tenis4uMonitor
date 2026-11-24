import pytest
import requests

from http_client import HttpClient


class FakeProxies:
    def __init__(self):
        self.counter = 0

    def get_proxy(self, timeout=30):
        self.counter += 1
        return f"10.0.0.{self.counter}:8080"


class FakeResponse:
    def __init__(self, status=200, text="ok"):
        self.status_code = status
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


class RecordingGet:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _client(responses, max_retries=3):
    getter = RecordingGet(responses)
    return HttpClient(FakeProxies(), user_agent="UA", max_retries=max_retries, request_get=getter), getter


def test_merges_user_agent_with_provider_headers_and_passes_params():
    client, getter = _client([FakeResponse(text="body")])

    assert client.get("https://x", headers={"x-custom": "1"}, params={"a": "b"}) == "body"
    assert getter.calls[0]["headers"] == {"User-Agent": "UA", "x-custom": "1"}
    assert getter.calls[0]["params"] == {"a": "b"}


def test_non_2xx_raises_after_all_retries():
    client, getter = _client([FakeResponse(500)] * 3)

    with pytest.raises(requests.HTTPError):
        client.get("https://x")
    assert len(getter.calls) == 3


def test_uses_new_proxy_on_each_retry():
    client, getter = _client([requests.ConnectionError("boom"), FakeResponse(500), FakeResponse(text="ok")])

    assert client.get("https://x") == "ok"
    proxies = [call["proxies"]["https"] for call in getter.calls]
    assert proxies == ["http://10.0.0.1:8080", "http://10.0.0.2:8080", "http://10.0.0.3:8080"]
