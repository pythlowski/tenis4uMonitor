from http_client import HttpClient
from providers.base import SlotProvider
from providers.tenis4u import Tenis4uProvider
from providers.twojtenis import TwojTenisProvider

PROVIDERS: dict[str, type[SlotProvider]] = {
    Tenis4uProvider.name: Tenis4uProvider,
    TwojTenisProvider.name: TwojTenisProvider,
}


def provider_class(name: str) -> type[SlotProvider]:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown provider {name!r}. Known providers: {', '.join(sorted(PROVIDERS))}") from None


def create_provider(name: str, http: HttpClient) -> SlotProvider:
    return provider_class(name)(http)
