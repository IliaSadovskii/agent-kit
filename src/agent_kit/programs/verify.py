"""verify — the kit runs the project's own commands and records what they printed.

The second version asked an agent to report whether the tests were green. The
measurement is what that was worth: the kit checks the end state of delivery and
almost no act along the way. So this step has no role and no session. It runs
what `.agent-kit/v3/project.toml` declares, in the order it declares them, and
returns exit codes.

A command that fails stops the ones after it. Running a test suite over code the
linter already refused costs minutes and tells nobody anything new.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..logs import get_logger
from ..project import require_project
from ..providers.base import ExecutorFailed, ExecutorResult, StepRequest

#: A project's own suite is minutes. One that has said nothing for this long is
#: not slow, it is stuck, and a night must not wait on it.
DEFAULT_TIMEOUT = 3600

#: What is kept of a command's output. Failures announce themselves at the end,
#: so it is the tail that is kept, and the whole of it is in the step's raw.txt.
KEPT = 8000

log = get_logger("programs.verify")


class Verify:
    name = "program:verify"

    def __init__(self, root: Path, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.root = Path(root)
        self.timeout = timeout

    def execute(self, request: StepRequest) -> ExecutorResult:
        root = Path(request.project) if request.project else self.root
        project = require_project(root)
        if not project.commands:
            raise ExecutorFailed(
                "no-commands",
                f"{project.source} declares no commands, so there is no way to verify this project",
                hint="agent-kit init --force",
                retryable=False,  # the file will not have changed by the next attempt
            )

        ran: list[dict] = []
        for command in project.commands:
            log.info("verify: %s — %s", command.name, command.command)
            record = self._one(command.name, command.command, root)
            ran.append(record)
            if not record["passed"]:
                # Everything after this would be run over code already refused.
                break

        passed = all(record["passed"] for record in ran)
        return ExecutorResult(
            raw=json.dumps({"commands": ran, "passed": passed}, indent=2, ensure_ascii=False),
            meta={"model": self.name, "commands_run": len(ran)},
        )

    def _one(self, name: str, command: str, root: Path) -> dict:
        try:
            finished = subprocess.run(
                command,
                shell=True,  # a declared command is a shell line, as its author wrote it
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                start_new_session=True,
            )
        except subprocess.TimeoutExpired as expired:
            return {
                "name": name,
                "command": command,
                "exit_code": None,
                "passed": False,
                "output": f"it said nothing for {self.timeout} seconds and was stopped: {_tail(expired.stdout)}",
            }
        except OSError as error:
            return {
                "name": name,
                "command": command,
                "exit_code": None,
                "passed": False,
                "output": f"it could not be run: {error}",
            }

        return {
            "name": name,
            "command": command,
            "exit_code": finished.returncode,
            "passed": finished.returncode == 0,
            "output": _tail(f"{finished.stdout}\n{finished.stderr}"),
        }


def _tail(text: str | bytes | None) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = (text or "").strip()
    if not text:
        return "it printed nothing"
    return text if len(text) <= KEPT else "…\n" + text[-KEPT:]
