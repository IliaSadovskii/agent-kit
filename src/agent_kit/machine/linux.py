"""The three things about this machine that no other module may know.

A boot identifier, whether a pid is alive, and what a systemd user unit looks
like. Everything OS-specific in the kit lives here, which is what makes the
plan's sentence — *macOS is one file later* — true rather than hopeful.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Where Linux keeps an identifier that changes on every boot.
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")

#: What a lease from a machine that cannot name its boot carries. Liveness and
#: the lease's own deadline still hold; only the reboot shortcut is lost, and a
#: reboot is not silent about it — the name says so wherever it is printed.
UNKNOWN_BOOT = "boot-unknown"


def boot_id() -> str:
    """This boot, by name. Every lease written before the last reboot is dead."""
    try:
        return BOOT_ID.read_text(encoding="utf-8").strip() or UNKNOWN_BOOT
    except OSError:
        return UNKNOWN_BOOT


def is_alive(pid: int) -> bool:
    """Is there a process under this number right now?

    A pid belonging to somebody else answers yes: it exists, which is the
    question. A pid that was reused is the one case this cannot see, and the
    lease's own deadline is the backstop for it.
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


UNIT = """\
[Unit]
Description=agent-kit — the machine's slots, limits and queue
After=network.target

[Service]
Type=simple
ExecStart={binary} daemon start --foreground
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


def unit_file(binary: str) -> str:
    """The systemd user unit, as text. Writing it is a command; this is only its shape."""
    return UNIT.format(binary=binary)


def unit_path(home: Path) -> Path:
    return home / ".config/systemd/user/agent-kit.service"
