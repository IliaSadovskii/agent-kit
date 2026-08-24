"""What a run is, as data.

One shape, validated on the way in and on the way out. No agent's editor ever
writes a field here — the driver does, through `RunStore`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .. import __version__
from ..errors import StateError

SCHEMA_VERSION = 3
BRANCH_PREFIX = "kit/"

#: What a run does when nobody says otherwise: one feature, end to end.
DEFAULT_STEPS = ("design", "build", "verify", "review", "record", "deliver")

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    STOPPED = "stopped"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    #: The session answered and the driver is waiting for a person. The step is
    #: nobody's work at this moment: it holds no slot, because a slot is one
    #: live session and this one is closed. It still holds its run.
    ASKING = "asking"
    PASSED = "passed"
    FAILED = "failed"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def release(version: str) -> tuple[int, ...]:
    """The comparable part of a version: 3.0.0.dev0 and 3.0.0 are the same release."""
    head = version.split("+")[0].lstrip("vV")
    numbers: list[int] = []
    for part in head.split("."):
        digits = ""
        for character in part:
            if not character.isdigit():
                break
            digits += character
        if not digits:
            break
        numbers.append(int(digits))
    return tuple(numbers)


def check_slug(slug: Any) -> str:
    if not isinstance(slug, str) or not _SLUG.match(slug):
        raise StateError("bad-slug", f"{slug!r} is not a run name: lower case, digits, dot, dash, underscore")
    return slug


@dataclass
class Step:
    name: str
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    provider: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "attempts": self.attempts,
            "provider": self.provider,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Any, index: int) -> "Step":
        where = f"steps[{index}]"
        data = _dict(data, where)
        return cls(
            name=_text(data.get("name"), f"{where}.name"),
            status=_enum(StepStatus, data.get("status"), f"{where}.status"),
            attempts=_count(data.get("attempts", 0), f"{where}.attempts"),
            provider=_optional_text(data.get("provider"), f"{where}.provider"),
            started_at=_optional_text(data.get("started_at"), f"{where}.started_at"),
            ended_at=_optional_text(data.get("ended_at"), f"{where}.ended_at"),
            reason=_optional_text(data.get("reason"), f"{where}.reason"),
        )


@dataclass
class Run:
    slug: str
    steps: list[Step]
    status: RunStatus = RunStatus.CREATED
    branch: str = ""
    project: str | None = None
    #: What this run is for, in the owner's own words. Every step's input
    #: encloses it, so no step is ever told to go and find out.
    brief: str | None = None
    current_step: int | None = None
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    finished_at: str | None = None
    reason: str | None = None
    schema: int = SCHEMA_VERSION
    kit: str = __version__

    @classmethod
    def new(cls, slug: str, steps: list[str] | tuple[str, ...] | None = None, project: str | None = None,
            branch: str | None = None, brief: str | None = None) -> "Run":
        check_slug(slug)
        names = list(steps or DEFAULT_STEPS)
        if not names:
            raise StateError("no-steps", "a run with no steps has nothing to advance")
        return cls(
            slug=slug,
            steps=[Step(name=_text(name, "steps[].name")) for name in names],
            branch=branch or f"{BRANCH_PREFIX}{slug}",
            project=project,
            brief=_optional_text(brief, "brief"),
        )

    # --- reading ----------------------------------------------------------

    @property
    def current(self) -> Step | None:
        """The step the run is on, whatever it is doing: running, or asking.

        Named for the pointer rather than for one of the two, because a run
        waiting twenty minutes on a person is as much *where the run is* as one
        with a session open.
        """
        return None if self.current_step is None else self.steps[self.current_step]


    @property
    def finished(self) -> bool:
        """Done, stopped or failed: three ways a run has nothing left to advance.

        A failed run does not quietly resume. The plan is explicit — the run
        stops and says which step, which provider and what was missing — and a
        resumption that erases that reason is the second version's defect: the
        record forgets what the attempt directories still remember.
        """
        return self.status in (RunStatus.DONE, RunStatus.STOPPED, RunStatus.FAILED)

    def next_pending(self) -> int | None:
        for index, step in enumerate(self.steps):
            if step.status is StepStatus.PENDING:
                return index
        return None

    # --- advancing --------------------------------------------------------

    def start_step(self, provider: str | None = None) -> Step:
        if self.finished:
            raise StateError("run-finished", f"{self.slug} is {self.status.value}; it does not start again")
        if self.current_step is not None:
            raise StateError("step-already-running", f"{self.slug}: step {self.current.name!r} is still running")
        index = self.next_pending()
        if index is None:
            raise StateError("no-step-pending", f"{self.slug}: every step is done")

        step = self.steps[index]
        step.status = StepStatus.RUNNING
        step.attempts += 1
        step.provider = provider
        step.started_at = now()
        step.ended_at = None
        step.reason = None
        self.current_step = index
        self.status = RunStatus.RUNNING
        self.reason = None
        return self._touch(step)

    def pass_step(self) -> Step:
        """The step is done — by its session, or by a default nobody answered."""
        step = self._require_current()
        step.status = StepStatus.PASSED
        step.ended_at = now()
        self.current_step = None
        if self.next_pending() is None:
            self.status = RunStatus.DONE
            self.finished_at = now()
        return self._touch(step)

    def ask_step(self, note: str) -> Step:
        """The session answered, and what it returned is a question for a person.

        A fourth thing that can happen to a running step, and it has its own
        word because it is neither a refusal nor a failure nor running out of
        room: the step did its work and named what only the owner can settle.
        """
        step = self._require_running()
        step.status = StepStatus.ASKING
        step.reason = _reason(note)
        return self._touch(step)

    def answered(self, note: str) -> Step:
        """A person answered, so the step is done again with what they said.

        Its own word beside `refuse_step` and `continue_step`: nothing was
        refused and nothing ran out of room. What comes next is a fresh session
        with the answer enclosed, which is the only way the design on file is
        the design that was built.
        """
        self._require_asking()
        return self._park(note)

    def refuse_step(self, reason: str) -> Step:
        """One attempt was not accepted. The step waits for the next one.

        The run stays running: this is the driver's retry policy at work, not a
        decision that the run is over.
        """
        return self._park(reason)

    def continue_step(self, note: str) -> Step:
        """The step did real work and ran out of room. It goes on in a new session.

        A third event, and it has its own word: nothing here was refused, and
        nothing here failed. What the session produced is kept and handed to
        the one that carries on.
        """
        return self._park(note)

    def _park(self, reason: str) -> Step:
        step = self._require_current()
        step.status = StepStatus.PENDING
        step.ended_at = now()
        step.reason = _reason(reason)
        self.current_step = None
        return self._touch(step)

    def fail_step(self, reason: str) -> Step:
        """No attempt will be accepted. The step and the run both stop here."""
        step = self._require_current()
        step.status = StepStatus.FAILED
        step.ended_at = now()
        step.reason = _reason(reason)
        self.current_step = None
        self.status = RunStatus.FAILED
        self.reason = step.reason
        self.finished_at = now()
        return self._touch(step)

    def fail(self, reason: str) -> "Run":
        """The run stops because a step could not be made to pass. It says which and why."""
        step = self.current or self._last_touched()
        if step is not None and step.status is not StepStatus.PASSED:
            step.status = StepStatus.FAILED
            step.ended_at = step.ended_at or now()
            # A failed step with no reason is the one thing the kit refuses to
            # write anywhere else; `fail_step` has always required it and this
            # path quietly did not, so `run show` printed a failure and no cause.
            step.reason = _reason(reason)
        self.current_step = None
        self.status = RunStatus.FAILED
        self.reason = _reason(reason)
        self.finished_at = now()
        self.updated_at = now()
        return self

    def halt(self, reason: str) -> "Run":
        """A step passed, and what it recorded is that the run must not go on.

        Legal from `done`, and that is the whole reason it exists: the last step
        passing does not make a run done when the thing that step recorded is
        that the work is not deliverable. The step keeps its `passed` — it did
        its job — and the run says why it stopped.
        """
        self.current_step = None
        self.status = RunStatus.STOPPED
        self.finished_at = now()
        self.reason = _reason(reason)
        self.updated_at = now()
        return self

    def stop(self, reason: str) -> "Run":
        if self.finished:
            raise StateError("run-finished", f"{self.slug} is already {self.status.value}")
        step = self.current
        if step is not None:
            step.status = StepStatus.PENDING
            step.ended_at = now()
        self.current_step = None
        self.status = RunStatus.STOPPED
        self.finished_at = now()
        self.reason = _reason(reason)
        self.updated_at = now()
        return self

    def _last_touched(self) -> Step | None:
        """The step the run got to: the last one started that did not pass."""
        reached = [step for step in self.steps if step.attempts and step.status is not StepStatus.PASSED]
        return reached[-1] if reached else None

    def _require_current(self) -> Step:
        """A step the run is on: running, or waiting for a person."""
        step = self.current
        if step is None:
            raise StateError("no-step-running", f"{self.slug}: no step is running")
        return step

    def _require_running(self) -> Step:
        step = self._require_current()
        if step.status is not StepStatus.RUNNING:
            raise StateError("no-step-running", f"{self.slug}: {step.name} is {step.status.value}, not running")
        return step

    def _require_asking(self) -> Step:
        step = self.current
        if step is None or step.status is not StepStatus.ASKING:
            raise StateError("no-step-asking", f"{self.slug}: no step is waiting for an answer")
        return step

    def _touch(self, step: Step) -> Step:
        self.updated_at = now()
        return step

    # --- the file ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "kit": self.kit,
            "slug": self.slug,
            "project": self.project,
            "brief": self.brief,
            "branch": self.branch,
            "status": self.status.value,
            "current_step": self.current_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "finished_at": self.finished_at,
            "reason": self.reason,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Run":
        data = _dict(data, "run")
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise StateError("bad-field: steps", "steps must be a non-empty list")

        slug = data.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            _bad("slug", "a run needs a name")

        run = cls(
            slug=check_slug(slug),
            steps=[Step.from_dict(step, index) for index, step in enumerate(raw_steps)],
            status=_enum(RunStatus, data.get("status"), "status"),
            branch=_text(data.get("branch"), "branch"),
            project=_optional_text(data.get("project"), "project"),
            brief=_optional_text(data.get("brief"), "brief"),
            current_step=_step_index(data.get("current_step"), len(raw_steps)),
            created_at=_text(data.get("created_at"), "created_at"),
            updated_at=_text(data.get("updated_at"), "updated_at"),
            finished_at=_optional_text(data.get("finished_at"), "finished_at"),
            reason=_optional_text(data.get("reason"), "reason"),
            schema=_count(data.get("schema", SCHEMA_VERSION), "schema"),
            kit=_text(data.get("kit", __version__), "kit"),
        )
        if run.current_step is not None and run.steps[run.current_step].status not in (
            StepStatus.RUNNING,
            StepStatus.ASKING,
        ):
            raise StateError(
                "bad-field: current_step", "current_step points at a step that is neither running nor asking"
            )
        return run


# --- field checks, each naming what it refused -----------------------------


def _bad(field_name: str, detail: str) -> Any:
    raise StateError(f"bad-field: {field_name}", detail)


def _dict(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _bad(where, f"{where} must be a table")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _bad(where, f"{where} must be a non-empty string")
    return value


def _optional_text(value: Any, where: str) -> str | None:
    return None if value is None else _text(value, where)


def _count(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _bad(where, f"{where} must be a whole number of at least 0")
    return value


def _enum(kind: type[Enum], value: Any, where: str) -> Any:
    try:
        return kind(value)
    except ValueError:
        _bad(where, f"{value!r} is not one of {', '.join(item.value for item in kind)}")


def _step_index(value: Any, count: int) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < count:
        _bad("current_step", f"{value!r} is not a step of this run")
    return value


def _reason(reason: Any) -> str:
    if not isinstance(reason, str) or not reason.strip():
        raise StateError("reason-required", "a step does not fail or stop without a reason anybody can read")
    return reason.strip()
