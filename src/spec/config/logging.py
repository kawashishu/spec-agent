import logging
import sys

# ANSI escape codes
RESET = "\033[0m"
COLOR_INFO = "\033[32m"     # Green
COLOR_WARNING = "\033[33m"  # Yellow
COLOR_ERROR = "\033[31m"    # Red

class LevelColorFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname

        if record.levelno == logging.INFO:
            color = COLOR_INFO
        elif record.levelno == logging.WARNING:
            color = COLOR_WARNING
        elif record.levelno == logging.ERROR:
            color = COLOR_ERROR
        else:
            color = RESET

        # Chỉ tô màu levelname
        record.levelname = f"{color}{levelname}{RESET}"

        return super().format(record)

# Setup logger
logger = logging.getLogger("spec")
logger.setLevel(logging.ERROR)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(LevelColorFormatter("%(levelname)s - %(message)s"))
logger.addHandler(console_handler)
