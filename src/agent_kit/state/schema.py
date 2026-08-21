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

SCHEMA_VERSION = 1
BRANCH_PREFIX = "kit/"

#: What a run does when nobody says otherwise. S4 replaces this with the four
#: steps of a feature — design, build, verify, deliver — once they have contracts.
DEFAULT_STEPS = ("probe",)

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
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
    current_step: int | None = None
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    finished_at: str | None = None
    reason: str | None = None
    schema: int = SCHEMA_VERSION
    kit: str = __version__

    @classmethod
    def new(cls, slug: str, steps: list[str] | tuple[str, ...] | None = None, project: str | None = None,
            branch: str | None = None) -> "Run":
        check_slug(slug)
        names = list(steps or DEFAULT_STEPS)
        if not names:
            raise StateError("no-steps", "a run with no steps has nothing to advance")
        return cls(
            slug=slug,
            steps=[Step(name=_text(name, "steps[].name")) for name in names],
            branch=branch or f"{BRANCH_PREFIX}{slug}",
            project=project,
        )

    # --- reading ----------------------------------------------------------

    @property
    def running(self) -> Step | None:
        return None if self.current_step is None else self.steps[self.current_step]

    @property
    def finished(self) -> bool:
        return self.status in (RunStatus.DONE, RunStatus.STOPPED)

    def next_pending(self) -> int | None:
        for index, step in enumerate(self.steps):
            if step.status in (StepStatus.PENDING, StepStatus.FAILED):
                return index
        return None

    # --- advancing --------------------------------------------------------

    def start_step(self, provider: str | None = None) -> Step:
        if self.finished:
            raise StateError("run-finished", f"{self.slug} is {self.status.value}; it does not start again")
        if self.current_step is not None:
            raise StateError("step-already-running", f"{self.slug}: step {self.running.name!r} is still running")
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
        step = self._require_running()
        step.status = StepStatus.PASSED
        step.ended_at = now()
        self.current_step = None
        if self.next_pending() is None:
            self.status = RunStatus.DONE
            self.finished_at = now()
        return self._touch(step)

    def fail_step(self, reason: str) -> Step:
        step = self._require_running()
        step.status = StepStatus.FAILED
        step.ended_at = now()
        step.reason = _reason(reason)
        self.current_step = None
        self.status = RunStatus.FAILED
        self.reason = step.reason
        return self._touch(step)

    def skip_step(self, reason: str) -> Step:
        step = self._require_running()
        step.status = StepStatus.SKIPPED
        step.ended_at = now()
        step.reason = _reason(reason)
        self.current_step = None
        if self.next_pending() is None:
            self.status = RunStatus.DONE
            self.finished_at = now()
        return self._touch(step)

    def fail(self, reason: str) -> "Run":
        """The run stops because a step could not be made to pass. It says which and why."""
        self.status = RunStatus.FAILED
        self.reason = _reason(reason)
        self.updated_at = now()
        return self

    def stop(self, reason: str) -> "Run":
        if self.finished:
            raise StateError("run-finished", f"{self.slug} is already {self.status.value}")
        step = self.running
        if step is not None:
            step.status = StepStatus.PENDING
            step.ended_at = now()
        self.current_step = None
        self.status = RunStatus.STOPPED
        self.finished_at = now()
        self.reason = _reason(reason)
        self.updated_at = now()
        return self

    def _require_running(self) -> Step:
        step = self.running
        if step is None:
            raise StateError("no-step-running", f"{self.slug}: no step is running")
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
            current_step=_step_index(data.get("current_step"), len(raw_steps)),
            created_at=_text(data.get("created_at"), "created_at"),
            updated_at=_text(data.get("updated_at"), "updated_at"),
            finished_at=_optional_text(data.get("finished_at"), "finished_at"),
            reason=_optional_text(data.get("reason"), "reason"),
            schema=_count(data.get("schema", SCHEMA_VERSION), "schema"),
            kit=_text(data.get("kit", __version__), "kit"),
        )
        if run.current_step is not None and run.steps[run.current_step].status is not StepStatus.RUNNING:
            raise StateError("bad-field: current_step", "current_step points at a step that is not running")
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
