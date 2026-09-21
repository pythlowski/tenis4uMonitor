import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class Logger:
    LOGS_DIRECTORY = "logs"
    ALL_LOGS_FILENAME = "app.log"
    ERROR_LOGS_FILENAME = "error.log"  

    def __init__(
        self,
        name: str = "APP",
        level: int = logging.INFO,
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Prevent duplicate handlers if Logger is instantiated multiple times
        if self.logger.handlers:
            return

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        Path(self.LOGS_DIRECTORY).mkdir(parents=True, exist_ok=True)

        all_logs_handler = self._create_handler(self.ALL_LOGS_FILENAME, formatter, logging.INFO)
        error_logs_handler = self._create_handler(self.ERROR_LOGS_FILENAME, formatter, logging.ERROR)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        self.logger.addHandler(all_logs_handler)
        self.logger.addHandler(error_logs_handler)
        self.logger.addHandler(console_handler)

    def _create_handler(self, file_name: str, formatter: logging.Formatter, logLevel):
        handler = RotatingFileHandler(
            f"{self.LOGS_DIRECTORY}/{file_name}",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setLevel(logLevel)
        handler.setFormatter(formatter)

        return handler

    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        self.logger.exception(message, *args, **kwargs)