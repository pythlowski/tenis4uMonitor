import datetime

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource, EnvSettingsSource, DotEnvSettingsSource


class ApiSettings(BaseModel):
    url: str = "https://api.tenis4u.pl"
    headers: dict[str, str] = {"x-tenis-user-agent": "tenis4u-web-frontoffice/3.6.0"}
    discord_webhook_url: str = ""
    fetch_interval_minutes: int = 1
    max_proxies_ready: int = 5


class Settings(BaseSettings):
    facility_id: int = 104
    court_type: str = "badminton"
    begin_time: datetime.time = datetime.time(16, 30)
    end_time: datetime.time = datetime.time(22, 30)
    days_of_week: list[str] = Field(
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MYAPP_",
        env_nested_delimiter="__",
        toml_file="config.toml",
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