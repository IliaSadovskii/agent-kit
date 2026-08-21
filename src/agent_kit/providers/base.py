"""The adapter contract — the only file that defines it.

A provider is a folder. What the driver knows about one is exactly this: it
hands over an input and is given back raw text. Nothing about tmux, transcripts
or flags reaches the driver, and nothing outside this package names a provider.

Level A — start a session, write into it, stop it — is what `Executor` needs.
Level B, which S3 adds beside it, is knowing whether a session is alive, how
much context it holds, and whether the account is limited and until when.
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
