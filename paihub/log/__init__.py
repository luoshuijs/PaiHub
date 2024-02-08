from .logger import Logger

__all__ = ("logger", "Logger")


logger = Logger(name="PaiHub", filename="log.log", color_log=True)
