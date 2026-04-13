import logging
import os
import sys
from pathlib import Path


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = "[%(asctime)s] %(levelname)-5s %(name)s — %(message)s"
    datefmt = "%H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    handlers.append(
        logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
    )

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, handlers=handlers)
