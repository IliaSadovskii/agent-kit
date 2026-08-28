"""S8d — the door: where this project stands, and the one thing to do next.

A program, not a session. It spends nothing: everything it reads is already on
disk, and the only thing it measures rather than reads is whether the first
word of a declared command is on this machine's PATH.

**One program rather than two.** The plan of 22 August promised *one door
instead of nine* and no step owned it; the second version kept the raw view of
a project and the ranked recommendation in two places that had to agree. Here
they are one pass over one set of data: the answer is the first rung of the
ladder with anything on it, and the view is the rest of the same ladder with
the counters beside it.

**What the codes are.** Where a state is one that a command already refuses by
name, the door prints *that* command's code rather than a synonym of it —
`no-description`, `no-commands`, `no-such-command`, `unreadable-project`,
`unreadable-batch`. That is the whole of §5's defect answered: *miss the door,
miss the check* becomes *the door says every check's code before you type the
command*. Only states that no refusal covers get a word of their own, and those
are named mechanically after the record they come from: `run-failed`,
`run-stopped`, `run-created`, `run-running`.

**No rung depends on the time of day.** Nothing is ranked by age and no answer
changes at midnight, which is the rule about a fixture encoding a shape rather
than a moment: two records are compared against each other and never against
the present, and that is the only ordering there is. What does read a clock is
the ledger, which is asked whether a lease has expired — a question about now
by its nature, and the only one here.

**What no trap holds, said here rather than only in a note.** Three of the
rules above are held by `tests/test_door.py` alone, and each was broken by hand
to prove it: the trunk being asked as well as the base — the bench cannot make
a stacked run, because a base is set by the batch driver and no command surface
sets one, and a judge that merged a branch itself would plant a world the
disarm cannot take away; `batch reopen` being the command where a batch owns a
stopped run — no case leaves a finished batch holding one; and an unreadable
batch hiding no run but its own. So is `ledger-too-new` against
`unreadable-ledger`, and so is `doctor` not building the ledger it then calls
missing.

**It refuses once, and not about a project.** `not-a-directory` is a path
somebody typed wrong; every state it actually finds — including a project
nothing can be run in — is its output rather than its exit code, because a door
that refuses is a door somebody can miss.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigError, KitError, StateError, UsageError
from .knowledge import ASSUMED, FRAME, Knowledge, KnowledgeError
from .manual import Manual, ManualError
from .verification.kinds import kind_named
from .paths import Paths, project_paths

#: How long git is given to answer a question about a ref. It is a local
#: repository and nothing here talks to a forge, so this is a bound on a
#: hang rather than a wait anybody will sit through.
GIT_TIMEOUT = 20


@dataclass(frozen=True)
class Line:
    """One state the door found: its code, what it is about, and what to type.

    `command` is empty where the kit has none, and that is honest rather than
    missing: for a failed run there is nothing to type that would resume it —
    `failed` is terminal by the kit's own rule — so the door names the record
    to read instead of inventing a command that would refuse.
    """

    code: str
    what: str = ""
    why: str = ""
    command: str = ""
    #: The record's own moment, used to order several lines inside one rung.
    #: Never compared against the present.
    at: str = ""
    #: The last tiebreak, so the order is total and a judge can predict it.
    name: str = ""


@dataclass
class Reading:
    """Everything one pass found. The answer is the first line of the ladder."""

    ladder: list[Line] = field(default_factory=list)
    unread: list[Line] = field(default_factory=list)
    view: list[tuple[str, list[str]]] = field(default_factory=list)

    @property
    def answer(self) -> Line:
        return self.ladder[0]


def _in_order(lines: list[Line]) -> list[Line]:
    """Newest record first, then by name. No comparison with the present."""
    return sorted(lines, key=lambda line: (line.at, line.name), reverse=True)


class Door:
    """One project, read once.

    Every source is read in its own `try`, so one unreadable file becomes a
    named line rather than silence over everything else. A run.json that has
    been broken since March must not stop the door from naming tonight's work.
    """

    def __init__(self, root: Path | str, paths: Paths | None = None) -> None:
        self.root = Path(root)
        if not self.root.is_dir():
            # Not a state of any project: there is no project here to have
            # one. A path typed wrong is the command being typed wrong, which
            # is what exit code 1 means and the only code this command has.
            raise UsageError(
                "not-a-directory",
                f"{self.root} is not a directory, so there is no project to stand in",
            )
        self.root = self.root.resolve()
        self.paths = paths or Paths.from_env()
        self.dirs = project_paths(self.root)
        self.project = None
        self.unreadable_project: Line | None = None
        self.unreadable_knowledge: Line | None = None

    # --- reading ------------------------------------------------------------

    def read(self) -> Reading:
        reading = Reading()

        self.project, self.unreadable_project = self._project()
        project = self.project
        knowledge, self.unreadable_knowledge = self._knowledge(project)
        # Neither goes into `unread`: both are on the first rung, because both
        # are what the next command would be refused by. Printing them twice
        # would be the door disagreeing with itself about which it is.

        runs, broken = self._runs()
        reading.unread += broken
        batches, unreadable_batches = self._batches()

        standing, unreadable = self._standing()
        if unreadable is not None:
            reading.unread.append(unreadable)

        chores, unreadable_manual = self._chores()
        if unreadable_manual is not None:
            reading.unread.append(unreadable_manual)

        owner_of = {
            feature.slug: batch.name for batch in batches for feature in batch.features
        }
        # A batch that cannot be read stands on the first rung — `batch go`
        # refuses it by exactly this code — and hides nothing else. Which runs
        # were its features is unknown, so those runs keep their own lines
        # rather than being swept out of sight with it: one unreadable source
        # hides none of the rest.

        reading.ladder = (
            self._running_now(standing)
            + self._the_night_would_refuse(knowledge, unreadable_batches)
            + self._work_that_was_spent(runs, owner_of)
            + self._work_that_is_unfinished(runs, batches, owner_of, standing)
            + self._work_a_person_owes(chores)
            + self._waiting_for_a_person(runs, owner_of, project, reading)
        )
        if not reading.ladder:
            # The bottom rung answers only when nothing above it did. Printed
            # under *also standing* beneath a night that failed, it would be
            # the door contradicting its own first line.
            reading.ladder.append(self._nothing_is_due(project))
        reading.view = self._view(project, knowledge, runs, batches, standing, chores)
        return reading

    # --- the sources ---------------------------------------------------------

    def _project(self):
        """The declaration, or the code that says it could not be read."""
        from .project import project_file, read_project

        try:
            return read_project(self.root), None
        except ConfigError as unreadable:
            return None, Line(unreadable.code, str(project_file(self.root)), why=unreadable.detail)

    def _knowledge(self, project):
        """Whether this project has written down what its product is.

        Three states and not two, exactly as the driver's preflight reads them:
        described, said out loud to be undescribed (`knowledge = ""`), and
        silence. The third is the only one that stands in the way of a night.
        """
        if project is None:
            return None, None
        try:
            held = Knowledge(project.knowledge_dir)
            held.described  # noqa: B018 - the read is the check
            return held, None
        except KnowledgeError as unreadable:
            return None, Line(unreadable.code, str(project.knowledge_dir or ""), why=unreadable.detail)

    def _runs(self):
        """Every run this project holds, and a line for each one that will not parse."""
        from .state import RunStore

        store = RunStore(self.root)
        held, broken = {}, []
        for slug in store.list():
            try:
                held[slug] = store.load(slug)
            except StateError as unreadable:
                broken.append(
                    Line(unreadable.code, slug, why=unreadable.detail, name=slug)
                )
        return held, broken

    def _batches(self):
        """Every batch, and a line on the ladder for each one that will not parse."""
        from .batch import BatchStore

        store = BatchStore(self.root)
        held, broken = [], []
        for name in store.list():
            try:
                held.append(store.load(name))
            except StateError as unreadable:
                broken.append(
                    Line(
                        unreadable.code, name, why=unreadable.detail, name=name,
                        command=f"agent-kit batch show {name}",
                    )
                )
        return held, broken

    def _standing(self):
        """What of this project is alive right now — the ledger's one question.

        The file is asked for before the ledger object is made, because making
        one creates the database: a machine where the kit has never run would
        otherwise be given a ledger by the command that came to look at it.
        """
        from .machine import Ledger, ledger_path

        where = ledger_path(self.paths)
        if not where.exists():
            return None, None
        try:
            return Ledger(where).standing(str(self.root)), None
        except (KitError, OSError) as unreadable:
            # The ledger's own words, not a synonym of them: it has two codes
            # here — one for a file that is not a database and one for a
            # schema this kit is too old for — and they want different things
            # done about them. Nothing wider is caught: a defect inside the
            # read is a defect, and printing it as a state would hide it.
            code = getattr(unreadable, "code", "unreadable-ledger")
            return None, Line(code, str(where), why=str(getattr(unreadable, "detail", unreadable)))

    # --- the ladder, top to bottom -------------------------------------------

    def _chores(self):
        """What a person still owes this project by hand, read off the disk.

        Its own `try`, like every other source: a file somebody broke by hand
        must not take down a door whose one refusal is a path typed wrong.
        """
        try:
            return Manual(self.root).actions(), None
        except ManualError as unreadable:
            return [], Line(
                unreadable.code,
                str(Manual(self.root).path),
                why=unreadable.detail,
                name="manual",
            )

    def _running_now(self, standing) -> list[Line]:
        """Rung 0. Something of this project is being written right now.

        Above everything, and the reason is mechanical rather than a judgement:
        every command the rungs below name would be refused by the lease this
        one is reading — `run-held-elsewhere`, `batch-held-elsewhere`,
        `checkout-held-elsewhere`. Its own word, because the door was refused
        nothing: those codes belong to whoever was turned away.
        """
        if standing is None or not standing.anything:
            return []
        asked = "; ".join(f"{ask.step} asks: {ask.question}" for ask in standing.asks)
        # One line per thing being driven rather than per lease: a run with no
        # worktree holds two of them — the run and the project's working copy —
        # and it is one night either way.
        held: dict[str, tuple] = {}
        for lease, kind in (
            [(one, "run") for one in standing.runs]
            + [(one, "batch") for one in standing.batches]
            + [(one, "working copy") for one in standing.checkouts]
        ):
            held.setdefault(lease.slug, (lease, kind))
        return _in_order(
            [
                Line(
                    "a-night-is-running",
                    f"{slug} — a {kind} has a driver on it since {lease.taken_at}",
                    why=asked or "nothing is waiting on you; it is building",
                    command="agent-kit machine",
                    at=lease.taken_at,
                    name=slug,
                )
                for slug, (lease, kind) in held.items()
            ]
        )

    def _the_night_would_refuse(self, knowledge, unreadable_batches) -> list[Line]:
        """Rung 1. What a night would be refused for, said before it is typed.

        In the order the kit itself raises them, and every code here is a code
        some other command already owns.
        """
        from .project import commands_that_start_nothing, starts_nothing

        project = self.project
        if self.unreadable_project is not None:
            # A declaration that will not parse is the end of the questions:
            # everything below reads it, so asking them would be guessing.
            return [self.unreadable_project]

        lines: list[Line] = []
        if self.unreadable_knowledge is not None:
            # Not the same state as *nothing is written down*, and the kit has
            # two codes for exactly that reason.
            lines.append(self.unreadable_knowledge)
        elif not self._is_described(project, knowledge):
            lines.append(
                Line(
                    "no-description",
                    "this project has not written down what its product is",
                    why=(
                        "a run carrying `design` is refused before its first session, because "
                        "there is nothing for a design to be designed against"
                    ),
                    command="agent-kit knowledge tell",
                )
            )
        if project is None or not project.commands:
            lines.append(
                Line(
                    "no-commands",
                    "nothing here says how this project is checked",
                    why="`verify` has nothing to run and the gate refuses a batch before it is created",
                    command="agent-kit init",
                )
            )
        elif project is not None:
            lost = commands_that_start_nothing(project)
            if lost:
                named = "; ".join(
                    f"{one.name} — {starts_nothing(one.command)!r} is not on this machine" for one in lost
                )
                lines.append(
                    Line(
                        "no-such-command",
                        named,
                        why="`verify` would run these, so a run is refused before its first session",
                    )
                )
        return lines + _in_order(unreadable_batches)

    def _is_described(self, project, knowledge) -> bool:
        """The driver's own question, asked the way the driver asks it.

        A project that says `knowledge = ""` has said out loud that nobody is
        describing it, and that is an answer: it goes past this rung. Silence
        does not.
        """
        if project is None:
            return False
        return not project.declares_knowledge or bool(knowledge and knowledge.described)

    def _work_that_was_spent(self, runs, owner_of) -> list[Line]:
        """Rung 2. A night was spent and there is nothing to show for it.

        Above the unfinished work because nothing will pick it up on its own:
        `failed` is terminal by the kit's own rule and `reopen` refuses it. So
        the rung has no command — naming one that would be refused is exactly
        the defect this whole layer is written against — and it names the record
        to read and the trace that is still standing.

        And it comes off the ladder when that trace is gone. `agent-kit tree
        remove` is a person saying *I have taken this apart*, and a run made by
        hand has no tree, so for that one the branch is the trace. Both are on
        disk and neither is a clock.
        """
        lines = []
        for slug, run in runs.items():
            if run.status.value != "failed" or not self._trace_stands(run):
                continue
            trace = run.tree or f"the branch {run.branch}"
            lines.append(
                Line(
                    "run-failed",
                    f"{self._named(slug, owner_of)} — {_the_code_in(run.reason)}",
                    why=f"{run.reason or 'nothing was written down'}; its trace still stands: {trace}",
                    command=f"agent-kit run show {slug}",
                    at=run.updated_at,
                    name=slug,
                )
            )
        return _in_order(lines)

    def _work_that_is_unfinished(self, runs, batches, owner_of, standing) -> list[Line]:
        """Rung 3. Work that stopped short and that a command will carry on.

        A batch stands for its own features here: `batch go` is what continues
        them, and naming a pending feature separately would be naming work
        whose driver is somebody else. That ownership is about the *name*,
        though, and not about the rank — a feature that failed is on the rung
        above, because `batch go` will never build it again.

        **And nothing a driver is holding appears here at all.** Rung zero
        names it already; printing it again below with `run go` or `batch go`
        would be the door offering a command the lease refuses by name, which
        is the defect this whole layer is written against.
        """
        driven = self._being_driven(standing)
        batch_lines, run_lines = [], []
        for batch in batches:
            if batch.finished or batch.name in driven:
                continue
            landed = sum(1 for feature in batch.features if feature.status.value == "done")
            batch_lines.append(
                Line(
                    "batch-unfinished",
                    f"{batch.name} — {landed} of {len(batch.features)} features landed",
                    why=batch.reason or "there is still something in it that can start",
                    command=f"agent-kit batch go {batch.name}",
                    at=batch.updated_at,
                    name=batch.name,
                )
            )

        unfinished_batches = {batch.name for batch in batches if not batch.finished}
        for slug, run in runs.items():
            if slug in driven:
                continue
            owner = owner_of.get(slug)
            if owner in unfinished_batches:
                continue
            code, command, why = self._where_it_stopped(run, owner)
            if code is None:
                continue
            run_lines.append(
                Line(
                    code,
                    self._named(slug, owner_of),
                    why=why,
                    command=command,
                    at=run.updated_at,
                    name=slug,
                )
            )
        # A batch stands before the runs it holds, because it is what carries
        # them on. Inside each group the record's own moment orders them.
        return _in_order(batch_lines) + _in_order(run_lines)

    def _being_driven(self, standing) -> set[str]:
        """Every name a live lease of this project stands against."""
        if standing is None:
            return set()
        return {
            lease.slug for lease in standing.runs + standing.batches + standing.checkouts
        }

    def _where_it_stopped(self, run, owner: str | None = None):
        """Three ways a run is unfinished, and the command for each.

        The codes are the run's own statuses, so there is one word for one
        state and no synonym to keep in step with anything. The command is the
        batch's wherever a batch owns the run: `run reopen` is not what carries
        a feature on, and offering it reopens work the batch will not then look
        at.
        """
        status = run.status.value
        if status == "stopped":
            closed = (
                f"a gate closed on {run.steps[run.gate_closed_on].name}"
                if run.gate_closed_on is not None
                else "it was stopped"
            )
            carry_on = (
                f"agent-kit batch reopen {owner} {run.slug}"
                if owner
                else f"agent-kit run reopen {run.slug}"
            )
            return "run-stopped", carry_on, f"{closed} — {run.reason or ''}".strip(" —")
        if status == "created":
            return "run-created", f"agent-kit run go {run.slug}", "it was created and nothing has started it"
        if status == "running":
            return (
                "run-running",
                f"agent-kit run go {run.slug}",
                "its record says running and no driver holds it: the machine it was on went away",
            )
        return None, "", ""

    def _work_a_person_owes(self, chores) -> list[Line]:
        """Rung 4. Something a night could not do for itself is waiting on a person.

        Above a report that is waiting, because the report describes work that
        does nothing until the key is placed; below work that is unfinished,
        because a night not finished costs more than a chore.

        **Only a chore the kit can take away stands here.** A line that says no
        command can prove it is closed by nobody but the owner deleting it, and
        a rung nothing can remove is a rung the door stops descending at — the
        defect the review found in `run-failed` and the reason `debt.md` has no
        rung at all. Those are counted in the view instead.

        Nothing is run here. The door names the command that runs the proofs; a
        door that acts is not a door.
        """
        provable = [chore for chore in chores if chore.provable]
        if not provable:
            return []
        first = provable[0]
        return [
            Line(
                "manual-due",
                f"{len(provable)} по этому проекту — {first.what}"
                + (f" (+{len(provable) - 1})" if len(provable) > 1 else ""),
                why="это работа, которую ночь сделать не может; доказательство снимет строку само",
                command="agent-kit manual check",
                name="manual",
            )
        ]

    def _waiting_for_a_person(self, runs, owner_of, project, reading) -> list[Line]:
        """Rung 5. The work landed and its report is waiting to be read.

        The forge is not asked. The door does not talk to the network, so what
        it knows is what `deliver` wrote down: a branch, a commit and a URL.
        The local repository is asked one thing — whether that work is already
        in the trunk — and that question may only ever *take this rung away*,
        never put a run on it. Neither `--is-ancestor` nor `git cherry` can see
        a merge that has not been fetched, so a *no* from them means nothing.
        """
        from .driver.workspace import StepWorkspace
        from .state import RunStore

        store = RunStore(self.root)
        lines = []
        for slug, run in runs.items():
            if run.status.value != "done":
                continue
            index = next(
                (number for number, step in enumerate(run.steps) if step.name == "deliver"), None
            )
            if index is None:
                continue
            workspace = StepWorkspace(store.run_root(slug), index, "deliver")
            output = workspace.read_output()
            if output is None:
                if (workspace.dir / "output.json").exists():
                    # `read_output` answers None for a file that is not there
                    # and for one that will not parse. The second silently
                    # takes a pull request off this rung, so it is said out
                    # loud rather than looked like the first.
                    reading.unread.append(
                        Line(
                            "unreadable-step-output",
                            str(workspace.dir / "output.json"),
                            why="what `deliver` recorded cannot be read, so its pull request is not named",
                            name=slug,
                        )
                    )
                continue
            url = str(output.get("pull_request") or "")
            if not url:
                continue
            trunk = project.default_branch if project else "main"
            base = run.base or trunk
            landed = self._has_landed(run.branch, str(output.get("commit") or ""), base, trunk)
            if landed is True:
                continue
            told = (
                f"this checkout does not have it in {base}"
                if landed is False
                else f"git could not be asked whether it is in {base}"
            )
            lines.append(
                Line(
                    "pull-request-waiting",
                    f"{self._named(slug, owner_of)} — {url}",
                    why=f"the work is on {run.branch} and {told}; the forge was not asked",
                    command=f"gh pr view {url}",
                    at=run.updated_at,
                    name=slug,
                )
            )
        return _in_order(lines)

    def _nothing_is_due(self, project) -> Line:
        """Rung 6. It always answers, which is what makes the door always answer.

        The name of the evening is left blank on purpose: it is the owner's
        word for their own work, and a kit that invents one is a kit naming
        somebody else's night.

        The candidate list is looked for under `audits/`, which is where an
        audit leaves one. `agent-kit audit --out` can put it anywhere, and a
        list written elsewhere is simply not named here — the door reads the
        place the kit writes to, and does not go looking.
        """
        standing = sorted((self.dirs.kit_dir / "audits").glob("*/candidates.md"))
        found = (
            f"a candidate list from an audit stands at {standing[-1]}, and `batch compose` reads a "
            "telling like it"
            if standing
            else "nothing is running, nothing failed and nothing is waiting to be read"
        )
        return Line(
            "nothing-is-due",
            why=found,
            command="agent-kit batch compose <name>",
        )

    # --- git, asked twice and never trusted to say yes ------------------------

    def _trace_stands(self, run) -> bool:
        """Is there still anything left of this failed run to look at?

        A tree that was taken away is a person saying they have dealt with it.
        Where git cannot answer, the rung stands: a failure does not disappear
        because a question about it could not be put.
        """
        if run.tree:
            return Path(run.tree).is_dir()
        answered = self._git("rev-parse", "--verify", "--quiet", f"refs/heads/{run.branch}")
        return answered is None or answered[0] != 1

    def _has_landed(self, branch: str, commit: str, base: str, trunk: str) -> bool | None:
        """The pair of questions, put to the base and to the trunk both.

        A feature that needs another is based on that one's branch, and that
        branch never receives a merge: the owner merges the stack into the
        trunk and tidies the branches away. Asked only against its base, such a
        report would be named for ever — and that is the commonest way a batch
        ends.

        Asking twice is safe because a question here may only ever *take* the
        rung away. A yes from either branch is landed; a no from either and
        nothing else is *not yet*; nothing answerable at all is `None`.
        """
        answered_at_all = False
        for against in dict.fromkeys((base, trunk)):
            said = self._asked_of(branch, commit, against)
            if said is True:
                return True
            answered_at_all = answered_at_all or said is False
        return False if answered_at_all else None

    def _asked_of(self, branch: str, commit: str, base: str) -> bool | None:
        """Two questions of the same price against one branch, and three answers.

        `merge-base --is-ancestor` sees a merge commit and nothing else: the
        kit's own rules allow `gh pr merge --squash`, and a squashed branch is
        an ancestor of nothing. `git cherry` compares patches instead and marks
        a change already upstream with `-`, which survives both a squash and a
        rebase.

        Either saying yes is *landed*. Both being asked and neither saying yes
        is *not yet*. Neither being answerable at all — no git, no repository —
        is `None`, and it is printed as itself: the pull request keeps standing,
        because a question that could not be put is not a no.
        """
        answered_at_all = False
        if commit:
            # 0 is yes and 1 is no; anything else — 128 for a commit this
            # repository has never heard of, or for no repository at all — is
            # not an answer and may not be read as one.
            said = self._git("merge-base", "--is-ancestor", commit, base)
            if said is not None and said[0] in (0, 1):
                answered_at_all = True
                if said[0] == 0:
                    return True
        said = self._git("cherry", base, branch)
        if said is not None and said[0] == 0:
            answered_at_all = True
            marks = [line[:1] for line in said[1].splitlines() if line.strip()]
            if marks and all(mark == "-" for mark in marks):
                return True
        return False if answered_at_all else None

    def _git(self, *argv: str):
        """git's own exit code and output, or None where it could not be asked."""
        try:
            done = subprocess.run(
                ["git", "-C", str(self.root), *argv],
                capture_output=True, text=True, timeout=GIT_TIMEOUT,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return done.returncode, done.stdout

    # --- the view -------------------------------------------------------------

    def _named(self, slug: str, owner_of: dict) -> str:
        """A run a batch owns is printed under both names, never under one."""
        owner = owner_of.get(slug)
        return f"{owner}/{slug}" if owner else slug

    def _view(self, project, knowledge, runs, batches, standing, chores=()) -> list[tuple[str, list[str]]]:
        counted: dict[str, int] = {}
        for run in runs.values():
            counted[run.status.value] = counted.get(run.status.value, 0) + 1
        sections = [
            (
                "runs",
                [f"{len(runs)}" + (": " + ", ".join(f"{n} {s}" for s, n in sorted(counted.items())) if counted else "")],
            ),
            (
                "batches",
                [
                    f"{batch.name}: "
                    f"{sum(1 for one in batch.features if one.status.value == 'done')}"
                    f" of {len(batch.features)} landed"
                    for batch in batches
                ]
                or ["none"],
            ),
            ("knowledge", self._knowledge_view(project, knowledge)),
            ("by hand", self._manual_view(chores)),
            ("commands", self._commands_view(project)),
            ("verification", self._verification_view(project)),
        ]
        if standing is not None and standing.asks:
            sections.append(
                (
                    "waiting on you",
                    [f"{ask.slug} · {ask.step} until {ask.until}: {ask.question}" for ask in standing.asks],
                )
            )
        return sections

    def _knowledge_view(self, project, knowledge) -> list[str]:
        if project is not None and not project.declares_knowledge:
            return ['knowledge = "" — this project says out loud that nobody describes it']
        if knowledge is None:
            return ["nothing declared, and nothing written"]
        try:
            blocks = knowledge.blocks()
            # Inside the same `try`, and that is the whole of why it is here: a
            # ledger the kit cannot read must not take down a door whose one
            # refusal is a path typed wrong.
            debt = knowledge.debt()
        except KnowledgeError as unreadable:
            return [f"{unreadable.code}: {unreadable.detail}"]
        assumed = sum(1 for block in blocks if block.kind == ASSUMED)
        frames = sum(1 for block in blocks if block.kind == FRAME)
        said = [
            f"{knowledge.root} — "
            + ("described" if knowledge.described else "declared, and nothing written in it")
            + f"; standing: {assumed} assumed, {frames} frame, {len(debt)} in the ledger"
        ]
        if debt:
            # A counter and never a rung. A rung is what a night would be
            # refused for, and nothing refuses a project that owes itself work —
            # and no command closes a line: the work that answers it does, named
            # by a feature that says so. A rung the kit cannot take away is a
            # rung the door stops descending at.
            said.append(
                "the ledger holds what is built and works badly; a line goes when the work "
                "that answers it lands, or when you take it out yourself"
            )
        if assumed:
            said.append(
                "an assumption nobody confirmed is settled where the owner talks: "
                "`agent-kit knowledge tell`"
            )
        return said

    def _manual_view(self, chores) -> list[str]:
        """Every chore standing, and the ones no command will ever close.

        The second kind is printed here and ranked nowhere. The plan wanted a
        *stage* to decide what is shown; there is no stage on disk and inventing
        one would be a field with a reader, no writer and no closer. What the
        door does instead is name one thing — the count and the first chore —
        and leave the list to the command that walks it.
        """
        if not chores:
            return ["nothing standing"]
        said = []
        for chore in chores:
            how = f"proof: {chore.proof}" if chore.provable else f"by hand: {chore.by_hand}"
            said.append(f"{chore.key}  {chore.what} — {how}")
        if any(not chore.provable for chore in chores):
            said.append(
                "a chore no command can prove is closed by nobody but you, so it is never ranked: "
                "delete the line in the commit that does the work"
            )
        return said

    def _verification_view(self, project) -> list[str]:
        """What this project checks itself for, and what it has said nothing about.

        The view and never a rung. A rung is what a night would be *refused*
        for, and nothing refuses an unanswered kind: the catalogue is the kit's,
        every project in the world begins with none of it answered, and a
        baseline frozen where nobody may move it could never answer at all. A
        rung nothing can take away is a rung the door stops descending, which is
        the one thing S8d must not do.

        The answer that could never fail is the exception, and it is not an
        exception to that rule: it *is* refused, before the first session of any
        run that carries `verify`, and it is printed here in the same words.
        """
        from .verification import commands_that_prove_nothing, proves_nothing, unanswered
        from .verification.said import about

        if project is None:
            return ["nothing declared, and no project to answer"]
        empty = {answer.kind for answer in commands_that_prove_nothing(project)}
        said = []
        for answer in project.verification:
            kind = kind_named(answer.kind)
            line = about(kind, answer) if kind is not None else answer.kind
            if answer.kind in empty:
                line += (
                    f"   ← command-that-proves-nothing: "
                    f"{proves_nothing(answer.command)!r} exits zero whatever is wrong"
                )
            said.append(line)
        left = unanswered(project)
        if left:
            said.append(
                "kind-unanswered: " + ", ".join(kind.name for kind in left)
                + " — nothing here says whether this project checks for them"
            )
        return said or ["none of the kinds the kit knows has been answered"]

    def _commands_view(self, project) -> list[str]:
        from .project import starts_nothing

        if project is None or not project.commands:
            return ["none declared"]
        said = []
        for command in project.commands:
            lost = starts_nothing(command.command)
            said.append(
                f"{command.name:8}{command.command}"
                + (f"   ← {lost!r} is not on this machine" if lost else "")
            )
        return said


def _the_code_in(reason: str | None) -> str:
    """The code a record's reason begins with, which is what a judge reads.

    The kit writes `<code>: <detail>` everywhere it refuses, so the leading
    token is the code and the rest is prose. A reason that carries none is
    printed as it stands rather than trimmed into something that looks like one.
    """
    said = (reason or "").strip()
    if not said:
        return "nothing was written down"
    head = said.split(":", 1)[0].strip()
    return head if head and " " not in head else said


def render(reading: Reading) -> str:
    """The answer, then everything else the same pass found."""
    answer = reading.answer
    said = [f"{answer.code}: {answer.what}" if answer.what else answer.code]
    if answer.why:
        said.append(f"  {answer.why}")
    if answer.command:
        said.append(f"$ {answer.command}")

    said += ["", "where this project stands"]
    for title, lines in reading.view:
        for index, line in enumerate(lines):
            said.append(f"  {title if index == 0 else '':<12}{line}")

    if reading.unread:
        said += ["", "what could not be read"]
        for line in reading.unread:
            said.append(f"  {line.code}: {line.what}")
            if line.why:
                said.append(f"    {line.why}")

    below = reading.ladder[1:]
    if below:
        said += ["", "also standing"]
        for line in below:
            said.append(f"  {line.code}: {line.what}".rstrip(": "))
            if line.command:
                said.append(f"    $ {line.command}")
    return "\n".join(said)


def what_now(root: Path | str, paths: Paths | None = None) -> str:
    return render(Door(root, paths).read())
