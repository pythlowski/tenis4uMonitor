import datetime
import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource

from availability import ALL_WEEKDAYS, AvailabilityFilters
from logger import Logger
from models.court_type import CourtType
from providers import PROVIDERS

ALLOWED_ENVS = {"dev", "prod"}

load_dotenv(".env", override=True)
CURRENT_ENV = os.getenv("APP_ENV", "dev").lower()

if CURRENT_ENV not in ALLOWED_ENVS:
    raise ValueError(
        f"Invalid APP_ENV='{CURRENT_ENV}'. Allowed values are: {', '.join(sorted(ALLOWED_ENVS))}"
    )

ENV_PREFIX = f"{CURRENT_ENV.upper()}_"

Weekday = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DiscordMode = Literal["global", "per_facility", "both"]

# Lowercase, digits, single underscores: the key becomes part of an env var name,
# so no hyphens (shells reject them) and no "__" (the nesting delimiter).
FACILITY_KEY_PATTERN = r"^[a-z0-9]+(_[a-z0-9]+)*$"
FACILITY_WEBHOOK_SUFFIX = "_webhook_url"


class FacilityConfig(BaseModel):
    key: str = Field(pattern=FACILITY_KEY_PATTERN)
    name: str
    provider: str
    facility_id: str
    court_type: CourtType
    booking_url: str | None = None  # overrides the provider's booking url

    @field_validator("facility_id", mode="before")
    @classmethod
    def _coerce_facility_id(cls, value):
        return str(value) if isinstance(value, int) else value

    @field_validator("provider")
    @classmethod
    def _known_provider(cls, value: str) -> str:
        if value not in PROVIDERS:
            raise ValueError(f"unknown provider {value!r}, expected one of: {', '.join(sorted(PROVIDERS))}")
        return value


class DiscordSettings(BaseModel):
    mode: DiscordMode = "global"
    global_webhook_url: SecretStr | None = None
    # Raw env entries: {ENV}_DISCORD__FACILITY__{KEY}_WEBHOOK_URL -> facility["{key}_webhook_url"]
    facility: dict[str, SecretStr] = Field(default_factory=dict)

    @field_validator("global_webhook_url", mode="before")
    @classmethod
    def _empty_as_none(cls, value):
        return None if value == "" else value

    def facility_webhook(self, key: str) -> SecretStr | None:
        webhook = self.facility.get(f"{key}{FACILITY_WEBHOOK_SUFFIX}")
        return webhook if webhook and webhook.get_secret_value() else None

    @property
    def sends_global(self) -> bool:
        return self.mode in ("global", "both")

    @property
    def sends_per_facility(self) -> bool:
        return self.mode in ("per_facility", "both")


class Settings(BaseSettings):
    _logger: Logger = PrivateAttr()

    fetch_interval_minutes: int = Field(20, ge=1)
    max_proxies_ready: int = Field(5, ge=1)
    days_ahead: int = Field(7, ge=1, le=14)

    # Global filters, applied to every facility
    begin_time: datetime.time = datetime.time(16, 30)
    end_time: datetime.time = datetime.time(22, 30)
    duration_minutes: int = Field(60, ge=1)  # length of every reported window
    weekdays: list[Weekday] = Field(default_factory=lambda: list(ALL_WEEKDAYS))

    facilities: list[FacilityConfig] = Field(min_length=1)
    discord: DiscordSettings = Field(default_factory=DiscordSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        toml_file=("config.toml", f"config.{CURRENT_ENV}.toml"),
        extra="ignore",
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._logger = Logger("SETTINGS")
        self._logger.info(f"Running settings for {CURRENT_ENV} environment.")

    @property
    def filters(self) -> AvailabilityFilters:
        return AvailabilityFilters(
            begin_time=self.begin_time,
            end_time=self.end_time,
            duration_minutes=self.duration_minutes,
            weekdays=tuple(self.weekdays),
        )

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if self.begin_time >= self.end_time:
            raise ValueError("begin_time must be earlier than end_time")

        keys = [facility.key for facility in self.facilities]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"duplicate facility keys: {', '.join(duplicates)}")

        if self.discord.sends_global and self.discord.global_webhook_url is None:
            raise ValueError(
                f"discord.mode={self.discord.mode!r} requires {ENV_PREFIX}DISCORD__GLOBAL_WEBHOOK_URL"
            )

        if self.discord.sends_per_facility:
            missing = [key for key in keys if self.discord.facility_webhook(key) is None]
            if missing:
                names = ", ".join(f"{ENV_PREFIX}DISCORD__FACILITY__{key.upper()}_WEBHOOK_URL" for key in missing)
                raise ValueError(f"discord.mode={self.discord.mode!r} requires {names}")

        expected = {f"{key}{FACILITY_WEBHOOK_SUFFIX}" for key in keys}
        unknown = sorted(set(self.discord.facility) - expected)
        if unknown:
            Logger("SETTINGS").warning(
                f"Ignoring facility webhooks that match no configured facility: {', '.join(unknown)}"
            )

        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
