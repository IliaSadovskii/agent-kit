"""verify — the kit runs the project's own commands and records what they printed.

The second version asked an agent to report whether the tests were green. The
measurement is what that was worth: the kit checks the end state of delivery and
almost no act along the way. So this step has no role and no session. It runs
what `.agent-kit/v3/project.toml` declares, in the order it declares them, and
returns exit codes.

A command that fails stops the ones after it. Running a test suite over code the
linter already refused costs minutes and tells nobody anything new.

How long it waits is the project's to say — `command_timeout` in its own
declaration. A project knows whether its suite is seconds or half an hour, and
the kit does not.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..logs import get_logger
from ..project import require_project
from ..shell import kill_group
from ..providers.base import ExecutorFailed, ExecutorResult, StepRequest

#: What is kept of a command's output. Failures announce themselves at the end,
#: so it is the tail that is kept, and the whole of it is in the step's raw.txt.
KEPT = 8000

log = get_logger("programs.verify")


class Verify:
    name = "program:verify"

    def __init__(self, root: Path, timeout: int | None = None) -> None:
        self.root = Path(root)
        #: None means the project decides, which is the usual case. A number
        #: here is somebody overruling it on purpose.
        self.timeout = timeout

    def execute(self, request: StepRequest) -> ExecutorResult:
        root = Path(request.project) if request.project else self.root
        project = require_project(root)
        # Declared by the project, run in the working copy this run holds: with
        # a tree per run, the project's own checkout is somebody else's feature.
        where = request.where
        if not project.commands:
            raise ExecutorFailed(
                "no-commands",
                f"{project.source} declares no commands, so there is no way to verify this project",
                hint="agent-kit init --force",
                retryable=False,  # the file will not have changed by the next attempt
            )

        waiting = self.timeout if self.timeout is not None else project.command_timeout
        ran: list[dict] = []
        for command in project.commands:
            log.info("verify: %s — %s", command.name, command.command)
            record = self._one(command.name, command.command, where, waiting)
            ran.append(record)
            if not record["passed"]:
                # Everything after this would be run over code already refused.
                break

        passed = all(record["passed"] for record in ran)
        return ExecutorResult(
            raw=json.dumps({"commands": ran, "passed": passed}, indent=2, ensure_ascii=False),
            # No `model`: a program is not a session and must not appear in the
            # record as one. `run show` reads that field to say who did the work.
            meta={"commands_run": len(ran)},
        )

    def _one(self, name: str, command: str, root: Path, waiting: int) -> dict:
        """One declared command, and everything it started dies with it.

        A project's test command is usually a wrapper — here it is `make test`,
        which is `docker compose exec`. Killing the wrapper and leaving what it
        started is how a stuck build keeps a shared machine busy all night, so
        the command gets its own process group and the group is what dies.
        """
        try:
            finished = subprocess.Popen(
                command,
                shell=True,  # a declared command is a shell line, as its author wrote it
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=True,
            )
        except OSError as error:
            return {
                "name": name,
                "command": command,
                "exit_code": None,
                "passed": False,
                "output": f"it could not be run: {error}",
            }

        try:
            stdout, stderr = finished.communicate(timeout=waiting)
        except subprocess.TimeoutExpired:
            kill_group(finished)
            return {
                "name": name,
                "command": command,
                "exit_code": None,
                "passed": False,
                "output": f"it said nothing for {waiting} seconds and was stopped, along with everything it started",
            }

        return {
            "name": name,
            "command": command,
            "exit_code": finished.returncode,
            "passed": finished.returncode == 0,
            "output": _tail(f"{stdout}\n{stderr}"),
        }


def _tail(text: str | bytes | None) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = (text or "").strip()
    if not text:
        return "it printed nothing"
    return text if len(text) <= KEPT else "…\n" + text[-KEPT:]
