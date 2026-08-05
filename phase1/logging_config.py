import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_LOG_PATH = Path(__file__).resolve().parent.parent / "dump.log"
_ROOT_LOGGER_NAME = "market_analyst"
_MAX_BYTES = 2_000_000  # 2 MB per file
_BACKUP_COUNT = 3        # dump.log, dump.log.1, dump.log.2, dump.log.3
_configured = False


def _configure():
    global _configured
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(level)
    root.propagate = False

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        _LOG_PATH, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name):
    if not _configured:
        _configure()
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
