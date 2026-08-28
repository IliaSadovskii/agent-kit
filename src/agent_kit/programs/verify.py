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
from ..verification.owed import UnprovedKind, proving, refuse_unless_every_kind_is_answered
from ..shell import kill_group
from ..providers.base import ExecutorFailed, ExecutorResult, StepRequest
from .proved import stood_on

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

        kinds = self._walk(request, project, where, waiting, ran) if all(one["passed"] for one in ran) else []
        passed = all(record["passed"] for record in (*ran, *kinds))
        # What the result is about. A claim bound to nothing is what let a
        # build change six files, name four, and deliver a green run on a
        # branch missing two of them — see `proved.py`, and `deliver` reads it.
        head, held = stood_on(where)
        return ExecutorResult(
            raw=json.dumps(
                {
                    "commands": ran,
                    "kinds": kinds,
                    "passed": passed,
                    "proved_at": head,
                    "proved_over": held,
                },
                indent=2, ensure_ascii=False,
            ),
            # No `model`: a program is not a session and must not appear in the
            # record as one. `run show` reads that field to say who did the work.
            # Distinct commands, because a kind proved by one the project had
            # already run in this step did not cost a second run of it, and a
            # count that said otherwise would be the record overstating itself.
            meta={"commands_run": len({one["command"] for one in (*ran, *kinds)})},
        )

    def _walk(self, request: StepRequest, project, where: Path, waiting: int, ran: list[dict]) -> list[dict]:
        """The list the design decided, walked rather than decided again.

        Two things happen here and they are one sentence of the plan each.
        Every kind the project owes must have been answered — and it is asked
        here as well as at the design, because a run assembled from other steps
        may carry no design at all, and then nobody has answered.

        Then each answered kind is run. A command already run in this step is
        not run twice: on a real project `[commands].test` and the answer to
        `suite` are the same line, and a feature that paid for it twice would
        pay every night. What that costs is a record where the same command
        appears against a kind and against the project, which is exactly what
        makes the two agreeing visible instead of accidental.
        """
        design = request.prior.get("design") or {}
        try:
            refuse_unless_every_kind_is_answered(design, project)
        except UnprovedKind as unproved:
            # Not retryable: the design is on file and a second attempt at this
            # step reads the same file. At the design it was an attempt refused
            # and asked again; here it is a step that cannot pass.
            raise ExecutorFailed(unproved.code, unproved.detail, retryable=False) from None

        already = {record["command"]: record for record in ran}
        kinds: list[dict] = []
        for name, command in proving(design):
            standing = already.get(command)
            if standing is not None:
                log.info("verify: %s — proved by %s, which has already run", name, standing["name"])
                kinds.append({**standing, "kind": name, "name": standing["name"]})
                continue
            log.info("verify: %s — %s", name, command)
            record = self._one(name, command, where, waiting)
            already[command] = record
            kinds.append({**record, "kind": name})
            if not record["passed"]:
                break
        return kinds

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
