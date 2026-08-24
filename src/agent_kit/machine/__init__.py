"""What is true on this machine right now.

`config.toml` is what this installation chose; this is what is happening. Two
files, one owner each — the plan's "Where everything lives", kept.

The driver depends on this; the daemon depends on this; this depends on nothing
but the paths and the errors. The arrow keeps pointing one way.
"""

from .ledger import (
    DEFAULT_TTL,
    RUN,
    SCHEMA_VERSION,
    SESSION,
    Busy,
    Ceilings,
    Lease,
    Ledger,
    Limited,
    Picture,
    Waiting,
    Want,
)
from .linux import boot_id, is_alive, unit_file, unit_path

__all__ = [
    "Busy",
    "Ceilings",
    "DEFAULT_TTL",
    "Lease",
    "Ledger",
    "Limited",
    "Picture",
    "RUN",
    "SCHEMA_VERSION",
    "SESSION",
    "Waiting",
    "Want",
    "boot_id",
    "is_alive",
    "ledger_path",
    "unit_file",
    "unit_path",
]


def ledger_path(paths) -> "object":
    """Where the ledger lives, by the name the plan gave it."""
    return paths.state_dir / "daemon.sqlite"
