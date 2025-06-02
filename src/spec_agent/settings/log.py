# src/core/config/logger.py

import logging
import sys

# ANSI escape codes for colors
RESET = "\x1b[0m"
COLOR_INFO = "\x1b[32m"  # Green
COLOR_WARNING = "\x1b[33m"  # Yellow
COLOR_ERROR = "\x1b[31m"  # Red
COLOR_NOTI = "\x1b[35m"  # Magenta


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter to add colors based on log level.
    """

    def format(self, record):
        level = record.levelname
        message = record.getMessage()

        if level == "INFO":
            color = COLOR_INFO
        elif level == "WARNING":
            color = COLOR_WARNING
        elif level == "ERROR":
            color = COLOR_ERROR
        else:
            color = RESET

        # Check for custom 'NOTI' prefix
        if hasattr(record, "noti") and record.noti:
            color = COLOR_NOTI
            message = f"NOTI: {message}"

        # Apply color to level name
        record.levelname = f"{color}{level}{RESET}"
        record.msg = message
        return super().format(record)


class Logger:
    def __init__(self, log_path: str = ""):
        self.logger = logging.getLogger("PDF_Search")
        self.logger.setLevel(logging.INFO)

        # Prevent adding multiple handlers if logger already has handlers
        if not self.logger.handlers:
            # StreamHandler for console with colors
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_formatter = ColoredFormatter("%(levelname)s - %(message)s")
            stream_handler.setFormatter(stream_formatter)
            self.logger.addHandler(stream_handler)

            if log_path:
                # FileHandler without colors
                file_handler = logging.FileHandler(log_path)
                file_formatter = logging.Formatter("%(levelname)s - %(message)s")
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def noti(self, message: str):
        """
        Custom notification method with distinct color.
        """
        if self.logger.isEnabledFor(logging.INFO):
            # Create a LogRecord with a custom attribute 'noti'
            record = self.logger.makeRecord(
                name=self.logger.name,
                level=logging.INFO,
                fn="",
                lno=0,
                msg=message,
                args=None,
                exc_info=None,
            )
            record.noti = True
            self.logger.handle(record)


logger = Logger(log_path="")
