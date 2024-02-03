import logging
from logging.handlers import RotatingFileHandler
import colorlog
import os


class Logger:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        if self.__initialized:
            return
        self.__initialized = True

        log_path = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(log_path):
            os.mkdir(log_path)

        self.log_file_name = os.path.join(log_path, "log.log")
        self.logger = logging.getLogger("PaiHub")
        self.logger.setLevel(logging.INFO)  # Set the base level to DEBUG

        log_colors_config = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red",
        }

        formatter = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] [%(levelname)s] - %(message)s",
            log_colors=log_colors_config,
        )
        formatter_plain = logging.Formatter("[%(asctime)s] [%(levelname)s] - %(message)s")

        # Console Handler
        ch = colorlog.StreamHandler()
        # ch.setLevel(logging.INFO)  # Set to INFO or any other level
        ch.setFormatter(formatter)

        # File Handler
        fh = RotatingFileHandler(
            filename=self.log_file_name,
            maxBytes=1024 * 1024 * 5,
            backupCount=5,
            encoding="utf-8",
        )
        # fh.setLevel(logging.INFO)  # Set to INFO or any other level
        fh.setFormatter(formatter_plain)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def debug(self, message, *args, exc_info: any = None, **kwargs):
        self.logger.debug(message, *args, exc_info=exc_info, extra=kwargs)

    def info(self, message, *args, exc_info: any = None, **kwargs):
        self.logger.info(message, *args, exc_info=exc_info, extra=kwargs)

    def warning(self, message, *args, exc_info: any = None, **kwargs):
        self.logger.warning(message, *args, exc_info=exc_info, extra=kwargs)

    def error(self, message, *args, exc_info: any = None, **kwargs):
        self.logger.error(message, *args, exc_info=exc_info, extra=kwargs)

    def critical(self, message, *args, exc_info: any = None, **kwargs):
        self.logger.critical(message, *args, exc_info=exc_info, extra=kwargs)
