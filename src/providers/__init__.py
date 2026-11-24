from http_client import HttpClient
from providers.base import SlotProvider
from providers.tenis4u import Tenis4uProvider

PROVIDERS: dict[str, type[SlotProvider]] = {
    Tenis4uProvider.name: Tenis4uProvider,
}


def create_provider(name: str, http: HttpClient) -> SlotProvider:
    try:
        provider_cls = PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown provider {name!r}. Known providers: {', '.join(sorted(PROVIDERS))}") from None
    return provider_cls(http)
