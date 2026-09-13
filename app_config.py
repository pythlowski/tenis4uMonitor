import json
import datetime
from dataclasses import dataclass, field



@dataclass(frozen=True)
class AppConfig:

    facility_id: int
    court_type: str
    begin_time: datetime.time
    end_time: datetime.time

    fetch_interval_minutes: int
    api_url: str
    api_headers: dict

    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: str
    recipients: list[str]

    days_of_week: list[str] = field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])

    @classmethod
    def from_json(cls, filepath: str) -> "AppConfig":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            facility_id=int(data["settings"].get("facility_id", 104)),
            court_type=data["settings"].get("court_type", "badminton"),
            begin_time=datetime.time.fromisoformat(data["settings"].get("begin_time", "16:30")),
            end_time=datetime.time.fromisoformat(data["settings"].get("end_time", "22:30")),
            days_of_week=data["settings"].get("days_of_week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),

            fetch_interval_minutes=int(data["api_settings"].get("fetch_interval_minutes", 1)),
            api_url=data["api_settings"]["url"],
            api_headers=data["api_settings"]["headers"],

            smtp_server=data["smtp_settings"]["server"],
            smtp_port=int(data["smtp_settings"]["port"]),
            sender_email=data["smtp_settings"]["sender_email"],
            sender_password=data["smtp_settings"]["sender_password"],
            recipients=data["smtp_settings"]["recipients"]       
        )