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
from pathlib import Path

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


def ran_alone(command: str, cwd: Path, timeout: int) -> tuple[int | None, str]:
    """One shell line, in its own process group, and what it said.

    Two callers, and they are the two places the kit runs a command somebody
    else wrote: `verify`, over the commands a project declares, and
    `agent-kit manual check`, over the proof a chore carries. A second copy of
    this would be a second copy of the rule above — that the group is what dies
    — and three chances to fix two.

    `None` for the exit code is *it never came back with one*: it could not be
    started, or it said nothing for long enough to be stopped.
    """
    try:
        child = subprocess.Popen(
            command,
            shell=True,  # a declared command is a shell line, as its author wrote it
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
    except OSError as error:
        return None, f"it could not be run: {error}"

    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(child)
        return None, (
            f"it said nothing for {timeout} seconds and was stopped, along with everything it started"
        )
    return child.returncode, f"{stdout}\n{stderr}"
