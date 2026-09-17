from api_monitor_service import APIMonitorService
from settings import Settings


if __name__ == "__main__":
    settings = Settings()
    app = APIMonitorService(settings)
    app.start()
