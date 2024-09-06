from typing import Optional
import logging
import os
from logging.handlers import RotatingFileHandler


from rich.console import Console
from rich.logging import RichHandler
from rich.style import Style
from rich.theme import Theme


SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


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
            console = self._get_rich_console()
            rich_handler = RichHandler(
                console=console, show_time=True, show_level=True, show_path=False, rich_tracebacks=True, markup=True
            )
            self.logger.addHandler(rich_handler)

        if filename is not None:
            # File Handler
            log_file_name = os.path.join(log_path, filename)
            rotating_file_handler = RotatingFileHandler(
                filename=log_file_name,
                maxBytes=1024 * 1024 * 5,
                backupCount=5,
                encoding="utf-8",
            )
            formatter_plain = logging.Formatter("[%(asctime)s] [%(levelname)s] - %(message)s")
            rotating_file_handler.setFormatter(formatter_plain)
            self.logger.addHandler(rotating_file_handler)

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

    def success(self, message, *args, exc_info: any = None, **kwargs):
        self.logger.log(SUCCESS_LEVEL_NUM, message, *args, exc_info=exc_info, extra=kwargs)

    @staticmethod
    def _get_rich_console(stderr: bool = False) -> Console:
        return Console(
            theme=Theme({"logging.level.success": Style(color="green")}),
            color_system="auto",
            force_terminal=None,
            width=None,
            stderr=stderr,
        )
