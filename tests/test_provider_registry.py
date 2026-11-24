import pytest

from providers import PROVIDERS, create_provider
from providers.tenis4u import Tenis4uProvider
from tests.fakes import FakeHttp


def test_known_provider_resolves():
    http = FakeHttp()
    provider = create_provider("tenis4u", http)
    assert isinstance(provider, Tenis4uProvider)
    assert provider.http is http


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider("nope", FakeHttp())


def test_registry_keys_match_provider_names():
    assert all(cls.name == name for name, cls in PROVIDERS.items())


def test_twojtenis_is_registered():
    from providers.twojtenis import TwojTenisProvider

    assert isinstance(create_provider("twojtenis", FakeHttp()), TwojTenisProvider)
