from monitor_service import MonitorService
from settings import Settings


if __name__ == "__main__":
    settings = Settings()
    app = MonitorService(settings)
    app.start()
