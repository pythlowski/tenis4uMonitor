from api_monitor_service import APIMonitorService
from app_config import AppConfig


if __name__ == "__main__":
    config = AppConfig.from_json("config.json")
    app = APIMonitorService(config)
    app.start()
