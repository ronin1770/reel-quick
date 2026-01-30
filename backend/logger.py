"""Custom logger setup for the backend."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import find_dotenv, load_dotenv

LOG_ENV_VAR = "LOG_LOCATION"
DEFAULT_LOG_PATH = "./log/backend.log"

_loggers: Dict[str, logging.Logger] = {}


def get_logger(
    log_path: Optional[str] = None,
    name: str = "instagram_reel_creation",
) -> logging.Logger:
    """Return a logger configured with a file handler."""
    cache_key = f"{name}:{log_path or ''}"
    if cache_key in _loggers:
        return _loggers[cache_key]

    load_dotenv(find_dotenv())
    resolved_path = log_path or os.getenv(LOG_ENV_VAR, DEFAULT_LOG_PATH)
    path = Path(resolved_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    has_handler = any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", None) == str(path)
        for handler in logger.handlers
    )
    if not has_handler:
        handler = logging.FileHandler(path)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _loggers[cache_key] = logger
    return logger
