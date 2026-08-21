"""What runs a step, seen from the driver.

The driver knows nothing about tmux, transcripts or flags: it hands over an
input and is given back raw text. S3 wraps a real agent CLI in this shape; the
fake in `providers/fake` is the same shape with no CLI at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..errors import ExitCode, KitError


class ExecutorFailed(KitError):
    """The session did not answer: it died, it hung, the provider is limited.

    This is an attempt like any other — the driver encloses the reason and tries
    again — never a crash of the run.
    """

    exit_code = ExitCode.PROVIDER


@dataclass(frozen=True)
class StepRequest:
    slug: str
    step_name: str
    attempt: int
    provider: str
    input_text: str
    workdir: Path
    project: Path | None = None


@dataclass(frozen=True)
class ExecutorResult:
    raw: str
    meta: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Executor(Protocol):
    name: str

    def execute(self, request: StepRequest) -> ExecutorResult: ...
