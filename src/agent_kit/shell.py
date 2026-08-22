"""Killing a command and everything it started.

Three places start other people's processes — a provider's CLI, a project's
declared command, git and gh — and all three want the same thing: what the
child spawned must not outlive it. An agent CLI spawns tools, `make test` here
is `docker compose exec`, git spawns a credential helper. A tool that outlives
the session it belongs to keeps editing files and keeps spending; a build that
outlives its timeout keeps a shared machine busy all night.

So the child is started in its own process group, and the group is what dies.
One home for it, because three copies of a rule is three chances to fix two.
"""

from __future__ import annotations

import os
import signal
import subprocess

from .logs import get_logger

log = get_logger("shell")


def kill_group(child: subprocess.Popen) -> None:
    """The command and every process it started."""
    try:
        os.killpg(os.getpgid(child.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        child.kill()
    try:
        child.communicate(timeout=10)
    except subprocess.TimeoutExpired:  # pragma: no cover - the group is gone by now
        log.warning("a killed process group did not go away")
