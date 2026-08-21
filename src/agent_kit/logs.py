"""Logging. Human lines on stderr, and a file on the machine that survives the terminal."""

from __future__ import annotations

import logging
import os
from pathlib import Path

LOG_ENV = "AGENT_KIT_LOG"
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s  %(message)s"


def setup_logging(verbose: bool = False, log_dir: Path | None = None) -> None:
    level = logging.DEBUG if verbose else _level_from_env()
    root = logging.getLogger("agent_kit")
    root.handlers.clear()
    root.setLevel(level)
    root.propagate = False

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(levelname)-7s %(message)s"))
    root.addHandler(stream)

    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_dir / "agent-kit.log", encoding="utf-8")
            handler.setFormatter(logging.Formatter(_FORMAT))
            root.addHandler(handler)
        except OSError:
            root.debug("no log file: %s is not writable", log_dir)


def _level_from_env() -> int:
    name = os.environ.get(LOG_ENV, "warning").upper()
    return getattr(logging, name, logging.WARNING) if isinstance(getattr(logging, name, None), int) else logging.WARNING


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"agent_kit.{name}")
