"""What is true about a batch right now, and only the program writes it.

The same rule as a run's state, for the same reason: what a person or an agent
edits by hand is what nobody can trust in the morning. The batch driver is the
one writer; everybody else reads.

A feature's state is the run's own, read back rather than kept twice — except
`skipped`, which is the batch's word, because a skipped feature may have no run
at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .. import __version__
from ..errors import StateError
from ..logs import get_logger
from ..paths import project_paths
from ..state.schema import RunStatus, check_slug, release
from ..state.store import write_whole
from .declaration import Declaration

BATCH_FILE = "batch.json"
SCHEMA_VERSION = 3

log = get_logger("batch")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class FeatureStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    STOPPED = "stopped"
    #: The batch's own word: this one is not being built tonight. A run may
    #: never have existed for it, which is why it cannot be a run's status.
    SKIPPED = "skipped"


#: What a run's own status becomes when the batch reads it back. Every status a
#: run has, and `None` for the two that are not an ending at all: a child that
#: came back leaving its run `created` or `running` said what happened in its
#: exit code instead, and reading that as a build that failed is how a machine
#: with no room became a feature the owner is told could not be built.
OF_A_RUN: dict[RunStatus, FeatureStatus | None] = {
    RunStatus.CREATED: None,
    RunStatus.RUNNING: None,
    RunStatus.DONE: FeatureStatus.DONE,
    RunStatus.FAILED: FeatureStatus.FAILED,
    RunStatus.STOPPED: FeatureStatus.STOPPED,
}

_OVER = (FeatureStatus.DONE, FeatureStatus.FAILED, FeatureStatus.STOPPED, FeatureStatus.SKIPPED)


@dataclass
class FeatureState:
    slug: str
    brief: str
    needs: list[str] = field(default_factory=list)
    status: FeatureStatus = FeatureStatus.PENDING
    tree: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    reason: str | None = None
    pull_request: str | None = None

    @property
    def over(self) -> bool:
        return self.status in _OVER

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "brief": self.brief,
            "needs": list(self.needs),
            "status": self.status.value,
            "tree": self.tree,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "reason": self.reason,
            "pull_request": self.pull_request,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "FeatureState":
        if not isinstance(data, dict):
            raise StateError("bad-field: features", "a feature must be a table")
        return cls(
            slug=check_slug(data.get("slug")),
            brief=str(data.get("brief") or ""),
            needs=[check_slug(name) for name in (data.get("needs") or [])],
            status=_enum(data.get("status")),
            tree=_optional(data.get("tree")),
            started_at=_optional(data.get("started_at")),
            ended_at=_optional(data.get("ended_at")),
            reason=_optional(data.get("reason")),
            pull_request=_optional(data.get("pull_request")),
        )


@dataclass
class FrameState:
    """One frame of this work, as the batch holds it.

    It is here and not only in the declaration because `batch go` builds its
    children out of this file: a batch carried on in the morning must hand the
    same lines to the features it has left as it handed the ones that ran last
    night, and the declaration is a file the owner may have edited since.

    `id` names the block `batch compose` wrote into the knowledge, and it is
    what the batch closes when the work is over. Empty where the declaration
    was written by hand: there is no block, so there is nothing to close.
    """

    what: str
    id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"what": self.what, "id": self.id}

    @classmethod
    def from_dict(cls, data: Any) -> "FrameState":
        if not isinstance(data, dict):
            raise StateError("bad-field: frames", "a frame must be a table")
        what = data.get("what")
        if not isinstance(what, str) or not what.strip():
            raise StateError("bad-field: frames", "a frame says what every feature builds alike")
        return cls(what=what.strip(), id=str(data.get("id") or ""))


@dataclass
class DebtState:
    """One line of the ledger this evening has already laid.

    Held for the reason a frame's identifier is held: so that a second `batch
    go` does not lay again what the owner has read and taken away. The evening
    is the ledger's one writer, and a writer with no memory of what it wrote is
    a writer that undoes the owner's answer every time it runs.
    """

    key: str
    what: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "what": self.what}

    @classmethod
    def from_dict(cls, data: Any) -> "DebtState":
        if not isinstance(data, dict):
            raise StateError("bad-field: debt", "a line of the ledger must be a table")
        key = data.get("key")
        if not isinstance(key, str) or not key.strip():
            raise StateError("bad-field: debt", "a line of the ledger is named by its key")
        return cls(key=key.strip(), what=str(data.get("what") or ""))


@dataclass
class ManualState:
    """One chore this evening has already laid in `.agent-kit/v3/manual.md`.

    The same memory `DebtState` is, and here it holds one thing more: the
    closer of a chore is its own proof, so a line laid last week may be gone by
    tonight. Without this a second `batch go` would write it back — resurrecting
    work somebody has already done, which is worse than never laying it.
    """

    key: str
    what: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "what": self.what}

    @classmethod
    def from_dict(cls, data: Any) -> "ManualState":
        if not isinstance(data, dict):
            raise StateError("bad-field: manual", "a manual action must be a table")
        key = data.get("key")
        if not isinstance(key, str) or not key.strip():
            raise StateError("bad-field: manual", "a manual action is named by its key")
        return cls(key=key.strip(), what=str(data.get("what") or ""))


@dataclass
class Batch:
    name: str
    features: list[FeatureState]
    #: What every feature of this work builds alike. Read by the driver twice:
    #: once to hand each child its lines, and once at the end to close the
    #: blocks the composing sitting wrote.
    frames: list[FrameState] = field(default_factory=list)
    #: What this evening has already written into the owner's ledger.
    debt: list[DebtState] = field(default_factory=list)
    #: What this evening has already asked a person to do by hand.
    manual: list[ManualState] = field(default_factory=list)
    project: str | None = None
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    reason: str | None = None
    schema: int = SCHEMA_VERSION
    kit: str = __version__

    # --- reading ----------------------------------------------------------

    def feature(self, slug: str) -> FeatureState:
        for feature in self.features:
            if feature.slug == slug:
                return feature
        raise StateError("no-such-feature", f"{self.name} declares no feature called {slug!r}")

    def ready(self) -> list[str]:
        """What may start now: everything pending whose needs have all landed.

        The plan says *waves*. Built as a barrier — start a wave, wait for all
        of it — a batch would be as slow as the slowest member of every level.
        This is the same order with none of that: with edges it is a wave, with
        none it is all of them at once, and nothing has to decide which.
        """
        landed = {feature.slug for feature in self.features if feature.status is FeatureStatus.DONE}
        return [
            feature.slug
            for feature in self.features
            if feature.status is FeatureStatus.PENDING and set(feature.needs) <= landed
        ]

    @property
    def running(self) -> list[str]:
        return [feature.slug for feature in self.features if feature.status is FeatureStatus.RUNNING]

    @property
    def finished(self) -> bool:
        """Nothing is running and nothing may start: this batch is over.

        Not *every feature is over*: a batch a person stopped leaves features
        pending whose needs will never land, and asking after all of them would
        be a batch that can never be called finished.
        """
        return not self.running and not self.ready()

    @property
    def landed_everything(self) -> bool:
        return all(feature.status is FeatureStatus.DONE for feature in self.features)

    def first_that_did_not_land(self) -> FeatureState | None:
        """In the order they were declared, which is the order the owner reads them in."""
        for feature in self.features:
            if feature.status is not FeatureStatus.DONE:
                return feature
        return None

    # --- advancing --------------------------------------------------------

    def starting(self, slug: str, tree: str | None = None) -> FeatureState:
        feature = self.feature(slug)
        if feature.status is not FeatureStatus.PENDING:
            raise StateError(
                "feature-not-pending", f"{slug} is {feature.status.value}; it does not start again"
            )
        feature.status = FeatureStatus.RUNNING
        feature.tree = tree
        feature.started_at = now()
        feature.ended_at = None
        # Whatever stopped it last time is not true of it now. It is being built.
        feature.reason = None
        return self._touch(feature)

    def ended(
        self, slug: str, status: FeatureStatus, reason: str | None = None,
        pull_request: str | None = None, cascade: bool = True,
    ) -> FeatureState:
        feature = self.feature(slug)
        if status is not FeatureStatus.DONE and not (reason or "").strip():
            # The run store refuses this by the same name and for the same
            # reason: a feature recorded `failed` with nothing in `reason` is a
            # night the owner reads in the morning and cannot act on.
            raise StateError(
                "reason-required",
                f"{slug} does not end {status.value} without a reason anybody can read",
            )
        feature.status = status
        feature.ended_at = now()
        feature.reason = reason
        feature.pull_request = pull_request
        if status is not FeatureStatus.DONE and cascade:
            # Building on a feature that did not land is building on nothing.
            # A feature dropped on purpose takes what needed it the same way it
            # went itself — skipped, not stopped, because nobody tried to build
            # it either. Anything else is `stopped`: the kit did not try and
            # fail here, it never started.
            #
            # A person stopping the whole batch is the one case that does not
            # cascade, and `cascade` is the flag for it: what was never started
            # stays pending, so `batch go` again carries on with it.
            self._take_the_dependants(
                slug, status if status is FeatureStatus.SKIPPED else FeatureStatus.STOPPED
            )
        return self._touch(feature)

    def never_started(self, slug: str, reason: str) -> FeatureState:
        """Nobody is building it and its run did not move: it is still to build.

        Two writers and one meaning: the machine had no agent to give it, or
        the driver that started it never came back. Either way nobody is
        building it and its run is where it was left, so the feature goes back
        to pending, the batch is not over, and `batch go` again carries on with
        it. The reason is kept, so the report says why it stands where it does.
        """
        feature = self.feature(slug)
        feature.status = FeatureStatus.PENDING
        feature.started_at = None
        feature.ended_at = None
        feature.reason = reason
        return self._touch(feature)

    def skip(self, slug: str, reason: str) -> list[str]:
        """Do not build this one tonight — nor anything that needed it.

        The list it returns is what has to be printed at the moment somebody
        types the command: a person who wanted one feature dropped and got three
        must be told before it happens, not afterwards in a report.
        """
        feature = self.feature(slug)
        if feature.over:
            raise StateError(
                "feature-over", f"{slug} is {feature.status.value} already; there is nothing to skip"
            )
        feature.status = FeatureStatus.SKIPPED
        feature.ended_at = now()
        feature.reason = reason
        self._touch(feature)
        return [slug] + self._take_the_dependants(slug, FeatureStatus.SKIPPED)

    def reopen(self, slug: str) -> list[str]:
        """A feature the night stopped is to be built again — and so is what it took down.

        The inverse of the cascade in `ended`, and it goes exactly as far: what
        was stopped only because this one was carries `needed-<slug>` and has
        nothing else wrong with it, so it comes back too. A feature stopped on
        its own account is left where it is.

        The list is what has to be printed at the moment somebody types the
        command, for the reason `skip` prints its own: a person who asked for
        one feature back and got three must be told now, not in a report.
        """
        feature = self.feature(slug)
        if feature.status is not FeatureStatus.STOPPED:
            raise StateError(
                "feature-not-stopped",
                f"{slug} is {feature.status.value}; only a feature the night stopped is carried on",
            )
        return [self._to_build_again(feature).slug] + self._give_back_the_dependants(slug)

    def _to_build_again(self, feature: FeatureState) -> FeatureState:
        """Back to pending, and it keeps its reason: it says where the feature stands."""
        feature.status = FeatureStatus.PENDING
        feature.started_at = None
        feature.ended_at = None
        return self._touch(feature)

    def _give_back_the_dependants(self, slug: str) -> list[str]:
        given: list[str] = []
        for feature in self.features:
            if feature.status is not FeatureStatus.STOPPED or feature.reason != f"needed-{slug}":
                continue
            self._to_build_again(feature)
            given.append(feature.slug)
            given += self._give_back_the_dependants(feature.slug)
        return given

    def _take_the_dependants(self, slug: str, status: FeatureStatus) -> list[str]:
        taken: list[str] = []
        for feature in self.features:
            if slug not in feature.needs or feature.over:
                continue
            feature.status = status
            feature.ended_at = now()
            feature.reason = f"needed-{slug}"
            taken.append(feature.slug)
            taken += self._take_the_dependants(feature.slug, status)
        return taken

    def _touch(self, feature: FeatureState) -> FeatureState:
        self.updated_at = now()
        return feature

    # --- the file ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "kit": self.kit,
            "name": self.name,
            "project": self.project,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reason": self.reason,
            "frames": [frame.to_dict() for frame in self.frames],
            "debt": [line.to_dict() for line in self.debt],
            "manual": [line.to_dict() for line in self.manual],
            "features": [feature.to_dict() for feature in self.features],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Batch":
        if not isinstance(data, dict):
            raise StateError("unreadable-batch", "a batch file must hold a table")
        schema = data.get("schema", SCHEMA_VERSION)
        if not isinstance(schema, int) or isinstance(schema, bool):
            raise StateError("bad-field: schema", "schema must be a whole number")
        if schema > SCHEMA_VERSION:
            raise StateError(
                "schema-too-new",
                f"this batch was written by a newer kit (schema {schema}, this kit reads {SCHEMA_VERSION})",
                hint="upgrade agent-kit",
            )
        kit = data.get("kit")
        if isinstance(kit, str) and release(kit) > release(__version__):
            raise StateError("kit-too-new", f"this batch was written by agent-kit {kit}, and this is {__version__}")

        features = data.get("features")
        if not isinstance(features, list) or not features:
            raise StateError("bad-field: features", "a batch holds a non-empty list of features")
        return cls(
            name=check_slug(data.get("name")),
            features=[FeatureState.from_dict(feature) for feature in features],
            # Absent is empty, and that is the whole of what this kit does with
            # a batch file schema 1 wrote: there were no frames then, so a
            # batch written by that kit had none. There is no migration table
            # here and this is why one is not needed — said in words rather
            # than left for somebody to find out.
            frames=[FrameState.from_dict(frame) for frame in (data.get("frames") or [])],
            # Absent in a file schema 1 or 2 wrote: no evening had laid a line
            # then, so an empty list is the truth rather than a default.
            debt=[DebtState.from_dict(line) for line in (data.get("debt") or [])],
            manual=[ManualState.from_dict(line) for line in (data.get("manual") or [])],
            project=_optional(data.get("project")),
            created_at=str(data.get("created_at") or now()),
            updated_at=str(data.get("updated_at") or now()),
            reason=_optional(data.get("reason")),
            schema=schema,
            kit=str(kit or __version__),
        )


class BatchStore:
    """Batches of one project, under `.agent-kit/v3/batches/`."""

    def __init__(self, root: Path | str) -> None:
        self.paths = project_paths(root)

    @property
    def batches_dir(self) -> Path:
        return self.paths.kit_dir / "batches"

    def path_for(self, name: str) -> Path:
        return self.batches_dir / check_slug(name) / BATCH_FILE

    def exists(self, name: str) -> bool:
        return self.path_for(name).is_file()

    def list(self) -> list[str]:
        if not self.batches_dir.is_dir():
            return []
        return sorted(entry.name for entry in self.batches_dir.iterdir() if (entry / BATCH_FILE).is_file())

    def create(self, declaration: Declaration, project: str | None = None) -> Batch:
        if self.exists(declaration.name):
            raise StateError(
                "batch-exists", f"{declaration.name} exists already; a batch is created once"
            )
        batch = Batch(
            name=check_slug(declaration.name),
            project=project or str(self.paths.root.resolve()),
            frames=[FrameState(what=frame.what, id=frame.id) for frame in declaration.frames],
            features=[
                FeatureState(slug=feature.slug, brief=feature.brief, needs=list(feature.needs))
                for feature in declaration.features
            ],
        )
        self.save(batch)
        log.info("batch %s created with %s features", batch.name, len(batch.features))
        return batch

    def load(self, name: str) -> Batch:
        path = self.path_for(name)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise StateError("unknown-batch", f"{name}: no batch under {self.batches_dir}") from error
        except OSError as error:
            raise StateError("unreadable-batch", f"{path}: {error}") from error
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise StateError("unreadable-batch", f"{path} is not valid JSON: {error}") from error
        return Batch.from_dict(data)

    def save(self, batch: Batch) -> Batch:
        data = batch.to_dict()
        Batch.from_dict(data)  # checked on the way out as well as in
        directory = self.path_for(batch.name).parent
        directory.mkdir(parents=True, exist_ok=True)
        _keep_batches_out_of_git(self.batches_dir)
        write_whole(self.path_for(batch.name), json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return batch


def _keep_batches_out_of_git(where: Path) -> None:
    """The kit's own state is not repository content — the same rule as `runs/`."""
    ignore = where / ".gitignore"
    if ignore.exists():
        return
    where.mkdir(parents=True, exist_ok=True)
    write_whole(ignore, "# The kit's own state. Not repository content — the branches are.\n*\n")


def _optional(value: Any) -> str | None:
    return None if value is None else str(value)


def _enum(value: Any) -> FeatureStatus:
    try:
        return FeatureStatus(value)
    except ValueError:
        raise StateError(
            "bad-field: status",
            f"{value!r} is not one of {', '.join(one.value for one in FeatureStatus)}",
        ) from None
