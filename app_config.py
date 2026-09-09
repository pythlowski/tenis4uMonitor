import json
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:

    api_url: str
    api_headers: dict
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: str
    recipients: list[str]
    fetch_interval_seconds: int = 300

    @classmethod
    def from_json(cls, filepath: str) -> "AppConfig":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            api_url=data["api_settings"]["url"],
            api_headers=data["api_settings"]["headers"],
            smtp_server=data["smtp_settings"]["server"],
            smtp_port=int(data["smtp_settings"]["port"]),
            sender_email=data["smtp_settings"]["sender_email"],
            sender_password=data["smtp_settings"]["sender_password"],
            recipients=data["smtp_settings"]["recipients"],
            fetch_interval_seconds=int(data["settings"].get("fetch_interval_seconds", 300)),
        )