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
from ..errors import StateError
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

        running: dict[str, Running] = {}
        interrupted = False
        try:
            while True:
                if not interrupted and self._stop_asked(name):
                    interrupted = True
                    self._ask_the_children_to_stop(running)
                if not interrupted:
                    self._skips_asked(name, batch, running)
                self._settle_whoever_ended(batch, running, interrupted=interrupted)

                if not running and (interrupted or not batch.ready()):
                    break
                if not interrupted:
                    self._start_what_is_ready(batch, running)
                if running:
                    self.pause(POLL)
        finally:
            self.store.save(batch)
            self.ledger.release(held)

        conflicts = self._will_they_merge(batch)
        self._take_away_the_trees_of_what_landed(batch)
        self._tell_the_owner(batch, conflicts, interrupted)
        return BatchOutcome(batch=batch, interrupted=interrupted, conflicts=conflicts)

    # --- starting -----------------------------------------------------------

    def _start_what_is_ready(self, batch: Batch, running: dict[str, Running]) -> None:
        """Whatever may go, up to as many children as the machine could ever run.

        The ceiling itself is the ledger's — it is what other projects share —
        and this is arithmetic about how many processes are worth raising: a
        child that cannot possibly get a slot is a python process idling in a
        poll loop.
        """
        for slug in batch.ready():
            if len(running) >= max(1, self.ceilings.max_sessions):
                return
            self._start(batch, slug, running)

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
                self._ended(batch, slug, run)
                self.store.save(batch)
                return
        else:
            run = create_run(
                self.runs, self.registry, slug,
                project=str(self.project), brief=feature.brief,
                base=base, tree=str(tree), needs=list(feature.needs),
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
        handle = open(log_file, "a", encoding="utf-8")
        return subprocess.Popen(
            [sys.executable, "-m", "agent_kit", "-C", str(self.project), *argv],
            cwd=str(self.project), stdin=subprocess.DEVNULL, stdout=handle, stderr=handle,
            start_new_session=True,
        )

    # --- endings ------------------------------------------------------------

    def _settle_whoever_ended(
        self, batch: Batch, running: dict[str, Running], interrupted: bool = False
    ) -> None:
        for slug in list(running):
            child = running[slug].child
            if child.poll() is None:
                continue
            skipping = running.pop(slug).skipping
            run = self.runs.load(slug)
            if skipping is not None:
                batch.ended(slug, FeatureStatus.SKIPPED, reason=skipping)
            else:
                self._ended(batch, slug, run, cascade=not interrupted)
            self.store.save(batch)

    def _ended(self, batch: Batch, slug: str, run: Any, cascade: bool = True) -> None:
        """A feature's ending is its run's own, read back rather than invented."""
        status = OF_A_RUN.get(run.status, FeatureStatus.FAILED)
        reason = run.reason if status is not FeatureStatus.DONE else None
        batch.ended(
            slug, status, reason=reason, pull_request=self._pull_request(slug, run), cascade=cascade
        )
        self.say(f"{batch.name}: {slug} — {status.value}{': ' + reason if reason else ''}")

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

    def _take_away_the_trees_of_what_landed(self, batch: Batch) -> None:
        """A landed feature's tree is a copy of a branch; a stalled one's is evidence."""
        for feature in batch.features:
            if feature.status is FeatureStatus.DONE:
                remove_tree(self.project, feature.slug)

    def _tell_the_owner(self, batch: Batch, conflicts: list[Conflict], interrupted: bool) -> None:
        if self.owner is None:
            return
        self.owner.news(said(batch, conflicts, interrupted))


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
