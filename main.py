from api_monitor_service import APIMonitorService


if __name__ == "__main__":
    app = APIMonitorService(config_path="config.json")
    app.start()
