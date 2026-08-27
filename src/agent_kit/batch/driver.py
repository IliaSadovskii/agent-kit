"""Running a batch: which of its runs may start now, and nothing else.

One driver per batch, one child process per feature, and every child is the
driver S4 to S7a already proved. This layer decides three things — who starts,
what a feature's ending does to the rest, and what the owner is told at the end.

Nothing below it knows what a batch is. That is the test of the shape: if the
runner, a step, an adapter or the ledger had to learn the word, a batch would be
a concept inside the driver rather than a layer above it.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..driver import create_run
from ..driver.tree import make_tree, remove_tree
from ..errors import ExitCode, KitError, StateError
from ..knowledge import Knowledge, KnowledgeError
from ..logs import get_logger
from ..machine import Ceilings, Ledger, ledger_path
from ..paths import Paths
from ..project import read_project
from ..state import RunStore
from ..steps import Registry
from .merge import Conflict, check_merges as _check_merges
from .state import OF_A_RUN, Batch, BatchStore, FeatureState, FeatureStatus

#: How often the driver looks at its children and at the ledger. A poll of a
#: local file and a `waitpid` are cheaper than a protocol to get wrong.
POLL = 1.0

#: What is written down about a feature the machine had no agent for. Not an
#: ending: `batch go` again is what happens to it. It covers a child turned
#: away before its first step and one turned away before its fourth alike —
#: both left their run exactly where it was, which is the whole claim.
NO_AGENT = "no agent could be run for it, and its run was left where it was"

log = get_logger("batch.driver")


@dataclass
class BatchOutcome:
    batch: Batch
    interrupted: bool = False
    conflicts: list[Conflict] = field(default_factory=list)


@dataclass
class Running:
    slug: str
    child: Any
    skipping: str | None = None


class BatchDriver:
    def __init__(
        self,
        project: Path | str,
        store: BatchStore,
        runs: RunStore,
        registry: Registry,
        ledger: Ledger | None = None,
        ceilings: Ceilings | None = None,
        owner: Any = None,
        options: list[str] | None = None,
        provider: str | None = None,
        spawn: Callable[..., Any] | None = None,
        check_merges: Callable[..., list[Conflict]] | None = None,
        say: Callable[[str], None] | None = None,
        pause: Callable[[float], None] | None = None,
    ) -> None:
        self.project = Path(project)
        self.store = store
        self.runs = runs
        self.registry = registry
        self.ledger = ledger or Ledger(ledger_path(Paths.from_env()))
        self.ceilings = ceilings or Ceilings()
        self.owner = owner
        self.options = list(options or [])
        self.provider = provider
        self.spawn = spawn or self._spawn
        self.check_merges = check_merges or _check_merges
        self.say = say or log.info
        self.pause = pause or time.sleep

    # --- the one thing it does --------------------------------------------

    def go(self, name: str) -> BatchOutcome:
        batch = self.store.load(name)
        if batch.finished:
            raise StateError(
                "batch-finished", f"{name}: nothing is running and nothing is ready to start"
            )
        held = self.ledger.hold_batch(str(self.project), name)
        if not held.granted:
            raise StateError(held.code, held.detail)

        self._whoever_was_left_running(batch)

        running: dict[str, Running] = {}
        #: Features this night has already asked the machine for and been
        #: turned away with. They are pending — nothing was attempted — and
        #: starting them again in the same pass is a loop of children that come
        #: straight back. Tomorrow's `batch go` is where they are asked again.
        turned_away: set[str] = set()
        interrupted = False
        try:
            while True:
                if not interrupted and self._stop_asked(name):
                    interrupted = True
                    self._ask_the_children_to_stop(running)
                if not interrupted:
                    self._skips_asked(name, batch, running)
                self._settle_whoever_ended(batch, running, turned_away, interrupted=interrupted)

                if not running and (interrupted or not self._what_may_start(batch, turned_away)):
                    break
                if not interrupted:
                    self._start_what_is_ready(batch, running, turned_away)
                if running:
                    self.pause(POLL)
        finally:
            if running:
                self._see_the_children_off(batch, running)
            self.store.save(batch)
            self.ledger.release(held)

        conflicts = self._will_they_merge(batch)
        self._close_the_frames(batch)
        self._take_away_the_trees_of_what_landed(batch)
        self._tell_the_owner(batch, conflicts, interrupted)
        return BatchOutcome(batch=batch, interrupted=interrupted, conflicts=conflicts)

    # --- starting -----------------------------------------------------------

    def _what_may_start(self, batch: Batch, turned_away: set[str]) -> list[str]:
        """Ready, less whatever the machine has already turned away tonight."""
        return [slug for slug in batch.ready() if slug not in turned_away]

    def _start_what_is_ready(
        self, batch: Batch, running: dict[str, Running], turned_away: set[str]
    ) -> None:
        """Whatever may go, up to as many children as the machine could ever run.

        The ceiling itself is the ledger's — it is what other projects share —
        and this is arithmetic about how many processes are worth raising: a
        child that cannot possibly get a slot is a python process idling in a
        poll loop.
        """
        for slug in self._what_may_start(batch, turned_away):
            if len(running) >= max(1, self.ceilings.max_sessions):
                return
            try:
                self._start(batch, slug, running)
            except (KitError, OSError, subprocess.SubprocessError) as could_not:
                # One feature that cannot be started is one feature. Raised out
                # of `go` — which is where it went — it left every child already
                # spawned building against a record that had them running for
                # good: they finish their features and open their pull requests,
                # and nothing can ever account for them.
                self._could_not_be_started(batch, slug, could_not)

    def _start(self, batch: Batch, slug: str, running: dict[str, Running]) -> None:
        feature = batch.feature(slug)
        base = self._base_of(batch, feature)
        tree = make_tree(self.project, slug, branch=f"kit/{slug}", base=base)

        if self.runs.exists(slug):
            run = self.runs.load(slug)
            if run.finished:
                # A batch gone on with, whose feature already landed the first
                # time round. Nothing to start; the ending is read as any
                # other, and no session is paid for twice.
                batch.starting(slug, tree=str(tree))
                self._ended(batch, slug, run, code=None)
                self.store.save(batch)
                return
        else:
            run = create_run(
                self.runs, self.registry, slug,
                project=str(self.project), brief=feature.brief,
                base=base, tree=str(tree), needs=list(feature.needs),
                # Out of the batch's own file and not the declaration: a batch
                # carried on in the morning hands its remaining features the
                # same lines it handed the ones that ran last night, whatever
                # the owner has edited since.
                frame=[frame.what for frame in batch.frames],
            )

        batch.starting(slug, tree=str(tree))
        self.store.save(batch)
        argv = self._argv_for(slug)
        self.say(f"{batch.name}: {slug} starts, on {base}")
        running[slug] = Running(slug=slug, child=self.spawn(run, argv))

    def _base_of(self, batch: Batch, feature: FeatureState) -> str:
        """What this feature builds on: the branch of what it needs, or the trunk."""
        if not feature.needs:
            project = read_project(self.project)
            return project.default_branch if project else "main"
        return f"kit/{feature.needs[0]}"

    def _argv_for(self, slug: str) -> list[str]:
        """What the child is told, and one flag it is told that a lone run is not.

        `--silent` says *somebody else is telling the owner about this run*: a
        batch of five would otherwise wake a phone five times at 03:00. An
        option may be addressed to one feature — `rates:reply=…` — because two
        features are two runs and what a provider is told about them may differ.
        """
        argv = ["run", "go", slug, "--silent"]
        if self.provider:
            argv += ["--provider", self.provider]
        for option in self.options:
            named, _, rest = option.partition(":")
            if rest and "=" in rest:
                if named == slug:
                    argv += ["--option", rest]
                continue
            argv += ["--option", option]
        return argv

    def _spawn(self, run: Any, argv: list[str]) -> subprocess.Popen:
        """One child, one run, its own process group.

        The kit as a command and not as an import, exactly as the bench runs it:
        a driver is one process per run and it dies with it, which is the plan's
        own table.
        """
        log_file = self.runs.run_root(run.slug) / "driver.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # Closed here and not left to the garbage collector: the child is given
        # a copy of the descriptor, so this one has nothing left to do. A batch
        # of five features on a long night is five handles nobody closes.
        with open(log_file, "a", encoding="utf-8") as handle:
            return subprocess.Popen(
                [sys.executable, "-m", "agent_kit", "-C", str(self.project), *argv],
                cwd=str(self.project), stdin=subprocess.DEVNULL, stdout=handle, stderr=handle,
                start_new_session=True,
            )

    # --- endings ------------------------------------------------------------

    def _settle_whoever_ended(
        self, batch: Batch, running: dict[str, Running], turned_away: set[str],
        interrupted: bool = False,
    ) -> None:
        for slug in list(running):
            code = running[slug].child.poll()
            if code is None:
                continue
            skipping = running.pop(slug).skipping
            run = self.runs.load(slug)
            if skipping is not None:
                batch.ended(slug, FeatureStatus.SKIPPED, reason=skipping)
            elif code == int(ExitCode.PROVIDER) and OF_A_RUN[run.status] is None:
                # The machine said no and the child touched nothing. It is not a
                # feature that failed: it is a feature nobody tried to build.
                turned_away.add(slug)
                batch.never_started(slug, NO_AGENT)
                self.say(f"{batch.name}: {slug} — still to build: {NO_AGENT}")
            else:
                self._ended(batch, slug, run, code, cascade=not interrupted)
            self.store.save(batch)

    def _ended(
        self, batch: Batch, slug: str, run: Any, code: int | None, cascade: bool = True
    ) -> None:
        """A feature's ending is its run's own, read back rather than invented.

        Read back where the run has one. A child that came back leaving its run
        exactly as it found it said what happened in its exit code instead, and
        every code the kit uses means one thing: a person stopped it, or it
        broke. `code` is `None` where there was no child to hear from at all.
        """
        status = OF_A_RUN[run.status]
        reason = run.reason
        if status is None:
            status, reason = _what_the_child_said(code, run)
        batch.ended(
            slug, status,
            reason=None if status is FeatureStatus.DONE else reason,
            pull_request=self._pull_request(slug, run), cascade=cascade,
        )
        self.say(f"{batch.name}: {slug} — {status.value}{': ' + reason if reason else ''}")

    def _could_not_be_started(self, batch: Batch, slug: str, could_not: Exception) -> None:
        said = (
            f"{could_not.code}: {could_not.detail}"
            if isinstance(could_not, KitError)
            else str(could_not)
        )
        batch.ended(slug, FeatureStatus.FAILED, reason=f"it could not be started — {said}")
        self.store.save(batch)
        self.say(f"{batch.name}: {slug} — failed: it could not be started — {said}")

    def _see_the_children_off(self, batch: Batch, running: dict[str, Running]) -> None:
        """Nobody is left building against a record that has stopped moving.

        The loop leaves nothing running, so this is the way out through an
        exception, and it is the one that made orphans: a child abandoned here
        finishes its feature, pushes its branch and opens its pull request while
        the batch has it `running` for good. It is stopped the way a person's
        stop stops it — at its own step boundary, never mid-edit — and its
        ending is read back like any other.
        """
        self._ask_the_children_to_stop(running)
        while running:
            self._settle_whoever_ended(batch, running, set(), interrupted=True)
            if running:
                self.pause(POLL)

    def _whoever_was_left_running(self, batch: Batch) -> None:
        """A feature the record has running that no driver is on any more.

        The layer below does exactly this, and for the same reason: a step left
        running by a driver that never came back goes back to pending and is
        tried again. This driver holds the batch, so no other batch driver is
        on this one — but a child outlives the parent that spawned it, and it
        may have finished the feature before it was orphaned.
        """
        driving = {lease.slug for lease in self.ledger.runs() if lease.project == str(self.project)}
        for slug in batch.running:
            if slug in driving:
                continue  # somebody is building it: it is not this driver's to take
            run = self.runs.load(slug) if self.runs.exists(slug) else None
            if run is not None and run.finished:
                self._ended(batch, slug, run, code=None)
                continue
            batch.never_started(slug, "the driver that started it never came back")
            self.say(f"{batch.name}: {slug} was left running by a driver that vanished")
        self.store.save(batch)

    def _pull_request(self, slug: str, run: Any) -> str | None:
        from ..driver.workspace import StepWorkspace
        from ..state import StepStatus

        for index, step in enumerate(run.steps):
            if step.name != "deliver" or step.status is not StepStatus.PASSED:
                continue
            output = StepWorkspace(self.runs.run_root(slug), index, step.name).read_output() or {}
            return str(output.get("pull_request") or "") or None
        return None

    # --- a person, mid-batch -------------------------------------------------

    def _stop_asked(self, name: str) -> bool:
        reason = self.ledger.stop_asked(str(self.project), name)
        if reason is None:
            return False
        self.say(f"{name}: stopped-by-request: {reason}")
        return True

    def _ask_the_children_to_stop(self, running: dict[str, Running]) -> None:
        """Each child stops itself, at its own step boundary, as it always has.

        Killing a session mid-edit is how a working copy is left half-written,
        and there is already a door that does this properly.
        """
        for slug in running:
            self.ledger.ask_stop(str(self.project), slug, reason="the batch was asked to stop")

    def _skips_asked(self, name: str, batch: Batch, running: dict[str, Running]) -> None:
        for feature, reason in self.ledger.skips_asked(str(self.project), name):
            try:
                held = batch.feature(feature)
            except StateError as unknown:
                self.say(f"{name}: {unknown.detail}")
                continue
            if held.status is FeatureStatus.RUNNING and feature in running:
                # It is being built right now, so it is stopped the way anything
                # running is stopped, and recorded as skipped when it comes back.
                running[feature].skipping = reason
                self.ledger.ask_stop(str(self.project), feature, reason=f"skipped: {reason}")
                self.say(f"{name}: {feature} is being skipped — its driver stops at the next step")
                continue
            taken = batch.skip(feature, reason)
            self.store.save(batch)
            self.say(f"{name}: skipping {', '.join(taken)} — {reason}")

    # --- when it is over -----------------------------------------------------

    def _will_they_merge(self, batch: Batch) -> list[Conflict]:
        project = read_project(self.project)
        base = project.default_branch if project else "main"
        landed = [
            (feature.slug, f"kit/{feature.slug}")
            for feature in batch.features
            if feature.status is FeatureStatus.DONE
        ]
        return list(self.check_merges(self.project, base, landed))

    def _close_the_frames(self, batch: Batch) -> None:
        """A frame is choreography, and the work it framed is over.

        Closed by the evening that wrote them and by nothing below: a feature
        deleting a frame would be deleting what its neighbours are still being
        held to, which is why `record` refuses the kind by name. The measurement
        behind this is the second version's: frames were the most written kind
        there, and a writer with no closer leaves the index of the owner's
        knowledge growing by a line per frame for ever — and that index is
        enclosed in every `design` afterwards.

        **Only when there is nothing left to build.** A batch a person stopped
        keeps features `pending`, and `batch go` again carries on with them; the
        lines they are held to must still be standing when it does.

        Nothing here fails the night. A block the owner deleted, a knowledge
        directory that moved: the work landed, the pull requests are open, and
        throwing that away over bookkeeping would be the worst trade in the kit.
        """
        if any(not feature.over for feature in batch.features):
            return
        standing = [frame for frame in batch.frames if frame.id]
        if not standing:
            return
        project = read_project(self.project)
        knowledge = Knowledge(project.knowledge_in(self.project) if project else None)
        if not knowledge.exists:
            return
        for frame in standing:
            try:
                knowledge.close_frame(frame.id, batch.name)
            except KnowledgeError as could_not:
                log.info("%s: %s stays where it is — %s", batch.name, frame.id, could_not.code)
                self.say(f"{batch.name}: рамку {frame.id} закрыть не вышло — {could_not.code}")
                continue
            # The record follows the file: the block is gone, so the batch no
            # longer claims to hold one.
            frame.id = ""
        self.store.save(batch)

    def _take_away_the_trees_of_what_landed(self, batch: Batch) -> None:
        """A landed feature's tree is a copy of a branch; a stalled one's is evidence."""
        for feature in batch.features:
            if feature.status is FeatureStatus.DONE:
                remove_tree(self.project, feature.slug)

    def _tell_the_owner(self, batch: Batch, conflicts: list[Conflict], interrupted: bool) -> None:
        if self.owner is None:
            return
        self.owner.news(said(batch, conflicts, interrupted))


def _what_the_child_said(code: int | None, run: Any) -> tuple[FeatureStatus, str]:
    """A child that left the run where it was, read by the code it came back with."""
    if code is None:
        return FeatureStatus.FAILED, f"its driver never came back, and the run is {run.status.value}"
    if code == int(ExitCode.INTERRUPTED):
        # A person, and the kit gives that code to nothing else. The child was
        # stopped before it could write down why, which is not a build failing.
        return FeatureStatus.STOPPED, "its driver was stopped before it could say why"
    died = f"was killed by signal {-code}" if code < 0 else f"exited {code}"
    return FeatureStatus.FAILED, f"its driver {died} and left the run {run.status.value}"


def said(batch: Batch, conflicts: list[Conflict], interrupted: bool = False) -> str:
    """One message for the whole batch, and it is the report in miniature.

    S7a made a run say so when it ends, which was right when a night was one
    run. Five features would wake the owner five times at 03:00, so the children
    are silent and this is what is sent.
    """
    lines = [f"{batch.name} — {'stopped' if interrupted else 'over'}"]
    for feature in batch.features:
        mark = feature.pull_request or feature.reason or ""
        lines.append(f"{feature.slug}: {feature.status.value}{' — ' + mark if mark else ''}")
    if conflicts:
        lines.append("")
        lines.append("These will not merge as they are:")
        lines += [f"- {conflict.said()}" for conflict in conflicts]
    return "\n".join(lines)
