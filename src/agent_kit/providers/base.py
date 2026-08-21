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
class SessionFacts:
    """What level B knows and level A does not.

    A level-A adapter leaves this empty: it can start a session and read what
    it said, and that is all. Level B fills it, which is what makes a session
    safe to leave running for hours — somebody can see how full it is.
    """

    session: str | None = None
    model: str | None = None
    context_used: int | None = None
    context_window: int | None = None
    cost_usd: float | None = None
    transcript: Path | None = None

    @property
    def observed(self) -> bool:
        """True when the session's context could actually be measured."""
        return self.context_used is not None and self.context_window is not None

    @property
    def context_share(self) -> float | None:
        if not self.observed or not self.context_window:
            return None
        return self.context_used / self.context_window

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "model": self.model,
            "context_used": self.context_used,
            "context_window": self.context_window,
            "cost_usd": self.cost_usd,
            "transcript": str(self.transcript) if self.transcript else None,
        }


@dataclass(frozen=True)
class ExecutorResult:
    raw: str
    meta: dict[str, Any] = field(default_factory=dict)
    facts: SessionFacts = field(default_factory=lambda: SessionFacts())


@runtime_checkable
class Executor(Protocol):
    name: str

    def execute(self, request: StepRequest) -> ExecutorResult: ...
