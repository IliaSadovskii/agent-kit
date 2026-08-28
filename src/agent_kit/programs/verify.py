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
from pathlib import Path

from ..logs import get_logger
from ..project import require_project, starts_nothing
from ..verification import owed_by_a_feature
from ..verification.owed import UnprovedKind, proving, refuse_unless_every_kind_is_answered
from ..shell import ran_alone
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

        # Before a single command is paid for. A run that will be refused for a
        # kind must not run the suite first: the refusal was knowable before it,
        # and — where a command comes back red — the kind would never be named
        # at all, because the walk below would not be reached.
        owed = self._asked_first(request, project)

        waiting = self.timeout if self.timeout is not None else project.command_timeout
        ran: list[dict] = []
        for command in project.commands:
            log.info("verify: %s — %s", command.name, command.command)
            record = self._one(command.name, command.command, where, waiting)
            ran.append(record)
            if not record["passed"]:
                # Everything after this would be run over code already refused.
                break

        kinds = (
            self._walk(owed, where, waiting, ran)
            if all(one["passed"] for one in ran)
            else []
        )
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

    def _asked_first(self, request: StepRequest, project) -> list[tuple[str, str]]:
        """Every kind the project owes must have been answered, asked before anything runs.

        The same judgement the design's own contract asks, asked again because a
        run assembled from other steps may carry no `design` at all — and then
        nobody has answered. At the design it was an attempt refused and asked
        again; here it is a step that cannot pass, because the design is on file
        and a second attempt reads the same file.

        What comes back is the *white list*: kinds the project owes, in the
        catalogue's order, each with the command the feature named. Nothing a
        session wrote about a kind the project never answered is in it, and on a
        project that has answered none it is empty whatever the design returned.
        """
        design = request.prior.get("design") or {}
        try:
            refuse_unless_every_kind_is_answered(design, project)
        except UnprovedKind as unproved:
            raise ExecutorFailed(unproved.code, unproved.detail, retryable=False) from None
        return proving(design, owed_by_a_feature(project))

    def _walk(
        self, owed: list[tuple[str, str]], where: Path, waiting: int, ran: list[dict]
    ) -> list[dict]:
        """Each owed kind's command, run in the tree this step already stands in.

        A command already run in this step is not run twice: on a real project
        `[commands].test` and the answer to `suite` are the same line, and a
        feature that paid for it twice would pay every night. The link between
        the two records is the command string itself, compared exactly — so
        `sh check.sh` and `sh  check.sh` are two commands and are paid for
        twice. That costs money and never green: two runs of the same work
        cannot disagree about whether it passed.

        The first word is looked for before the command is started, by the code
        every other declared command is refused by. It is the last of the three
        questions asked of a string a session wrote, and the only one that has
        to wait for the machine the run is on.

        No trap holds that last one. `a-command-that-starts-nothing` is about a
        word the *project* declared, and taking this call away reddens nothing:
        the world it needs is one where a session names a command that is not on
        the machine, and the bench has none. Tests hold it, and this says so.
        """
        already = {record["command"]: record for record in ran}
        kinds: list[dict] = []
        for name, command in owed:
            standing = already.get(command)
            if standing is not None:
                log.info("verify: %s — proved by %s, which has already run", name, standing["name"])
                kinds.append({**standing, "kind": name, "name": standing["name"]})
                continue
            lost = starts_nothing(command)
            if lost:
                raise ExecutorFailed(
                    "no-such-command",
                    f"{name} is proved by {command!r} and {lost!r} is not on this machine; "
                    "nothing was run for it",
                    retryable=False,
                )
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
        That last part is `shell.ran_alone`, which `agent-kit manual check` runs
        a chore's proof with: one home, two callers.
        """
        code, output = ran_alone(command, root, waiting)
        return {
            "name": name,
            "command": command,
            "exit_code": code,
            "passed": code == 0,
            "output": _tail(output),
        }


def _tail(text: str | bytes | None) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = (text or "").strip()
    if not text:
        return "it printed nothing"
    return text if len(text) <= KEPT else "…\n" + text[-KEPT:]
