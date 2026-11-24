import requests

from notifications.discord_notifier import DiscordNotifier


class FakeResponse:
    def __init__(self, status, body=None, headers=None):
        self.status_code = status
        self._body = body
        self.headers = headers or {}
        self.text = str(body)

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakePost:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def notifier(responses, max_retries=3):
    post, sleeps = FakePost(responses), []
    return DiscordNotifier(max_retries=max_retries, post=post, sleep=sleeps.append), post, sleeps


def test_204_is_success_and_sends_payload_with_timeout():
    n, post, sleeps = notifier([FakeResponse(204)])
    assert n.send("https://hook", {"content": "hi"}) is True
    assert post.calls[0]["json"] == {"content": "hi"}
    assert post.calls[0]["timeout"] == 10
    assert sleeps == []


def test_429_honours_retry_after_body():
    n, post, sleeps = notifier([FakeResponse(429, {"retry_after": 1.5}), FakeResponse(204)])
    assert n.send("https://hook", {}) is True
    assert sleeps == [1.5]


def test_429_falls_back_to_retry_after_header():
    n, _, sleeps = notifier([FakeResponse(429, headers={"Retry-After": "2"}), FakeResponse(204)])
    assert n.send("https://hook", {}) is True
    assert sleeps == [2.0]


def test_4xx_does_not_retry():
    n, post, sleeps = notifier([FakeResponse(400, {"message": "bad"})])
    assert n.send("https://hook", {}) is False
    assert len(post.calls) == 1
    assert sleeps == []


def test_connection_errors_back_off_then_give_up():
    n, post, sleeps = notifier([requests.ConnectionError()] * 3)
    assert n.send("https://hook", {}) is False
    assert len(post.calls) == 3
    assert sleeps == [1.0, 2.0, 4.0]
