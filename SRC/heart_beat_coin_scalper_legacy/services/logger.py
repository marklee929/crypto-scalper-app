from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def build_logger(
    name: str,
    log_path: str | Path,
    level: int = logging.INFO,
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
