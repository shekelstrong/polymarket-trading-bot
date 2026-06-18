"""Structured logging with Rich for nice terminal output."""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

_console = Console(stderr=True)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(
            console=_console,
            show_path=False,
            show_time=True,
            markup=True,
            rich_tracebacks=True,
        )
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
