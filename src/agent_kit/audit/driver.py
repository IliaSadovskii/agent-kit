"""One lens over one commit: measure, ask once, check the answer, write it down.

An audit is neither a run nor a sitting. It has no branch, no worktree that
survives, no sequence of the method and nobody standing at the terminal — so it
is not the hour with the owner; and it moves no state, opens no pull request
and lands nothing — so it is not a run. What it is, is the third caller of
`driver/session.py`: a program that borrows one turn.

There is no `audit.json`, for the reason S8a gave for there being no
`sitting.json`: an audit does not resume, cannot be stopped from elsewhere and
has no graph. State with no reader is not written.

Nothing below it learns the word *audit*. `Sessions`, `StepWorkspace`,
`compose_input` and the ledger see exactly the shapes they already saw — a
subject that is `Standing`, a step definition that is not in the builtin
registry, a workspace in a room. The one new noun is the lens.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import date as _date
from pathlib import Path
from typing import Any, Callable

from ..driver.session import Sessions, Standing
from ..driver.workspace import StepWorkspace
from ..errors import ProviderError, StateError
from ..logs import get_logger
from ..paths import project_paths
from ..project import require_project
from ..state.store import write_whole
from .lens import Lens
from .tree import unpack_head

AUDITS = "audits"
INVENTORY = "inventory.json"
REPORT = "report.md"
CANDIDATES = "candidates.md"

log = get_logger("audit")


@dataclass
class Outcome:
    """What one lens came to, for the person who typed the command."""

    name: str
    room: Path
    report: Path
    #: None where the lens found no work. An empty file saying *nothing to do*
    #: in prose is not an answer a script can read; `test -s` is.
    candidates: Path | None = None
    findings: int = 0
    said: list[str] = field(default_factory=list)


class Audit:
    """One lens, from the commit to the report."""

    def __init__(
        self,
        root: Path | str,
        lens: Lens,
        sessions: Sessions,
        today: str = "",
        say: Callable[[str], Any] | None = None,
        out: Path | None = None,
    ) -> None:
        self.root = Path(root)
        self.lens = lens
        self.sessions = sessions
        self.today = today or _date.today().isoformat()
        self.say = say or print
        #: Where the candidate list goes. None takes the kit's own place for it,
        #: inside the room.
        self.out = out

    # --- where its paperwork lives ----------------------------------------

    @property
    def audits(self) -> Path:
        return project_paths(self.root).kit_dir / AUDITS

    def name_for(self) -> str:
        """The lens and today, and an ordinal where today already had one."""
        name = f"{self.lens.name}-{self.today}"
        ordinal = 1
        while (self.audits / name).is_dir():
            ordinal += 1
            name = f"{self.lens.name}-{self.today}-{ordinal}"
        return name

    # --- the audit --------------------------------------------------------

    def run(self) -> Outcome:
        """Measure first, and refuse before a session is paid for.

        Finding 34: in the second version the audit was the one command that
        checked nothing before it started. What this one owes before it spends
        anything is a commit it can unpack and a manifest it can read, and both
        are refused by name.
        """
        # Read rather than required for anything of its own: the role table this
        # project declares is what decides who runs the lens, and the papers go
        # under this project's own kit directory.
        require_project(self.root)
        self.audits.mkdir(parents=True, exist_ok=True)
        keep_audits_out_of_git(self.audits)

        # Outside the project, and that is not tidiness. git looks for a
        # repository by walking up: a copy under `.agent-kit/` sits two
        # directories below the project's own `.git`, and a session standing in
        # it could commit to the repository the audit is supposed to be unable
        # to touch. `unpack_head` asks whether this really is outside one.
        tree = Path(tempfile.mkdtemp(prefix="agent-kit-audit-"))
        try:
            unpacked = unpack_head(self.root, tree)
            # Raises `nothing-to-measure` where this lens has nothing to look
            # at. Before the room is made: an audit that refused must not leave
            # a directory of paperwork about an audit that never happened.
            measured = self.lens.measure(tree, unpacked)

            room = self.audits / self.name_for()
            room.mkdir(parents=True)
            write_whole(room / INVENTORY, _as_json(self.lens.inventory(measured)))

            output = self._turn(room, tree, measured)
            judged = self.lens.judge(output, measured)
            outcome = self._write(room, measured, judged)
            self._told(outcome)
            return outcome
        finally:
            # Always. The tree is a copy of a commit, and everything the session
            # was worth is in the room.
            shutil.rmtree(tree, ignore_errors=True)

    # --- one headless turn ------------------------------------------------

    def _turn(self, room: Path, tree: Path, measured: Any) -> dict:
        definition = self.lens.definition
        workspace = StepWorkspace(room, 0, definition.name)
        # The session stands in the unpacked commit. There is no `.git` in it,
        # so it cannot commit, branch, push, or touch a file anybody will read
        # again: the possibility is gone rather than forbidden.
        subject = Standing(slug=room.name, project=str(self.root), tree=str(tree))
        attempts = {"n": 0}

        def on_start(provider: str):
            attempts["n"] += 1
            return subject, attempts["n"]

        walked = self.sessions.turn(
            subject, definition, workspace, definition.contract,
            self.lens.enclose(measured), {},
            on_start=on_start,
            judge=lambda output: self.lens.judge(output, measured),
        )
        if not walked.passed:
            last = walked.last
            if last is not None and last.busy is not None:
                # The machine said no before a session started. Nothing was
                # spent and nothing was written — which is exactly what code 4
                # means, and unlike a sitting there is no hour of somebody's
                # speech being held for them.
                raise ProviderError(last.busy.code, last.busy.detail)
            raise StateError(
                "audit-refused",
                f"{definition.name} was refused {len(walked.attempts)} times, last: "
                f"{last.refusal if last else 'and said nothing'}",
            )
        return workspace.read_output() or {}

    # --- writing, and only the program writes -----------------------------

    def _write(self, room: Path, measured: Any, judged: Any) -> Outcome:
        report = room / REPORT
        write_whole(report, self.lens.report(measured, judged, room.name))

        lines = self.lens.candidates(measured, judged, self.today)
        candidates = None
        if lines.strip():
            candidates = self.out or (room / CANDIDATES)
            candidates.parent.mkdir(parents=True, exist_ok=True)
            write_whole(candidates, lines)

        findings = len(getattr(judged, "findings", []) or [])
        log.info("%s: %s finding(s), report at %s", room.name, findings, report)
        return Outcome(
            name=room.name,
            room=room,
            report=report,
            candidates=candidates,
            findings=findings,
            said=self.lens.said(measured, judged),
        )

    def _told(self, outcome: Outcome) -> None:
        self.say("")
        for line in outcome.said:
            self.say(line)
        self.say("")
        self.say(f"  {outcome.report}")
        if outcome.candidates is None:
            self.say("  Работы не нашлось, поэтому списка кандидатов нет.")
            return
        self.say(f"  {outcome.candidates}")
        self.say("")
        self.say(f"  Дальше: agent-kit batch compose <имя> --from {outcome.candidates}")


def keep_audits_out_of_git(audits: Path) -> None:
    """A lens's paperwork is not repository content.

    The same shape `runs/` and `sittings/` have. It holds the raw text of every
    attempt and a report the kit regenerates on demand, and the audit's whole
    claim is that it leaves the working copy exactly as it found it — a claim a
    directory of untracked files would spoil.
    """
    ignore = audits / ".gitignore"
    if ignore.exists():
        return
    audits.mkdir(parents=True, exist_ok=True)
    write_whole(
        ignore,
        "# The kit's own paperwork for one lens over one commit: what was measured, what\n"
        "# each attempt returned, and the report. Not repository content.\n*\n",
    )


def _as_json(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
