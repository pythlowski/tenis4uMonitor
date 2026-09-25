import datetime
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource
from logger import Logger

ALLOWED_ENVS = {"dev", "prod"}

load_dotenv(".env", override=True)
CURRENT_ENV = os.getenv("APP_ENV", "dev").lower()

if CURRENT_ENV not in ALLOWED_ENVS:
    raise ValueError(
        f"Invalid APP_ENV='{CURRENT_ENV}'. Allowed values are: {', '.join(sorted(ALLOWED_ENVS))}"
    )

class ApiSettings(BaseModel):
    url: str = "https://api.tenis4u.pl"
    headers: dict[str, str] = {"x-tenis-user-agent": "tenis4u-web-frontoffice/3.6.0"}
    discord_webhook_url: str = ""
    fetch_interval_minutes: int = 1
    max_proxies_ready: int = 5


class Settings(BaseSettings):
    _logger: Logger = PrivateAttr()
    
    facility_id: int = 104
    court_type: str = "badminton"
    begin_time: datetime.time = datetime.time(16, 30)
    end_time: datetime.time = datetime.time(22, 30)
    weekdays: list[str] = Field(
        default_factory=lambda: [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
    )
    api: ApiSettings = Field(default_factory=ApiSettings)

    def __init__(self, **data):
        super().__init__(**data)
        self._logger = Logger("SETTINGS")
        self._logger.info(f"Running settings for {CURRENT_ENV} environment.")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=f"{CURRENT_ENV.upper()}_",
        env_nested_delimiter="__",
        toml_file=("config.toml", f"config.{CURRENT_ENV}.toml"),
        extra="ignore",
    )

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


if __name__ == "__main__":
    settings = Settings()
    print(settings.api.fetch_interval_minutes)
    print(settings.api.headers)
