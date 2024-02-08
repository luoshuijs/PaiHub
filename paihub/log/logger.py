from typing import Optional
import logging
import os
from logging.handlers import RotatingFileHandler

import colorlog


class Logger:
    def __init__(
        self,
        name: Optional[str] = None,
        level: int = logging.INFO,
        filename: Optional[str] = None,
        color_log: Optional[bool] = None,
    ):
        log_path = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(log_path):
            os.mkdir(log_path)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level=level)

        if color_log:
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
            # Console Handler
            ch = colorlog.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        if filename is not None:
            # File Handler
            log_file_name = os.path.join(log_path, filename)
            fh = RotatingFileHandler(
                filename=log_file_name,
                maxBytes=1024 * 1024 * 5,
                backupCount=5,
                encoding="utf-8",
            )
            formatter_plain = logging.Formatter("[%(asctime)s] [%(levelname)s] - %(message)s")
            fh.setFormatter(formatter_plain)
            self.logger.addHandler(fh)

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
