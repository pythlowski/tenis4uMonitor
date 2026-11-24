"""Test doubles shared across test modules."""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeHttp:
    """Records GET calls and answers from a list of responders.

    `routes` maps a URL prefix to either a string body or a callable(url, params) -> str.
    """

    def __init__(self, routes: dict | None = None):
        self.routes = routes or {}
        self.calls: list[dict] = []

    def get(self, url, headers=None, params=None):
        self.calls.append({"url": url, "headers": headers, "params": params})
        for prefix, responder in self.routes.items():
            if url.startswith(prefix):
                if isinstance(responder, Exception):
                    raise responder
                return responder(url, params) if callable(responder) else responder
        raise AssertionError(f"Unexpected GET {url}")
