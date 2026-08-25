"""What is true on this machine right now.

`config.toml` is what this installation chose; this is what is happening. Two
files, one owner each — the plan's "Where everything lives", kept.

The driver depends on this; the daemon depends on this; this depends on the
errors and on nothing else in the kit. The arrow keeps pointing one way.
"""

from pathlib import Path

from .ledger import (
    BATCH,
    RUN,
    SCHEMA_VERSION,
    SESSION,
    Ask,
    Busy,
    Ceilings,
    Lease,
    Ledger,
    Limited,
    Picture,
    Waiting,
    Want,
)
from .linux import is_alive, is_ours, unit_file, unit_path

__all__ = [
    "Ask",
    "Busy",
    "Ceilings",
    "Lease",
    "Ledger",
    "Limited",
    "Picture",
    "BATCH",
    "RUN",
    "SCHEMA_VERSION",
    "SESSION",
    "Waiting",
    "Want",
    "is_alive",
    "is_ours",
    "ledger_path",
    "unit_file",
    "unit_path",
]


def ledger_path(paths) -> Path:
    """Where the ledger lives, by the name the plan gave it."""
    return paths.state_dir / "daemon.sqlite"
