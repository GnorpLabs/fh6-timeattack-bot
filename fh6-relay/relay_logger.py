import logging
import os
import threading
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.path.join(os.environ.get("APPDATA", "."), "FH6BotRelay")
LOG_PATH = os.path.join(_LOG_DIR, "relay.log")


@dataclass
class DebugStats:
    packets_total: int = 0
    bad_size_count: int = 0
    last_size: int = 0
    last_bad_size: int = 0
    is_race_on: int = -1
    lap_number: int = 0
    last_lap_s: float = 0.0
    laps_recorded: int = 0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def snapshot(self) -> dict:
        with self._lock:
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


def setup_logger() -> logging.Logger:
    os.makedirs(_LOG_DIR, exist_ok=True)
    logger = logging.getLogger("fh6relay")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s")
    fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    return logger


log = setup_logger()
