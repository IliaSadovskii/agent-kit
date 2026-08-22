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
    again — never a crash of the run. Two things ride along, because both cost
    money when they are missing: whether trying again could possibly help, and
    what the attempt spent before it failed.
    """

    exit_code = ExitCode.PROVIDER

    def __init__(
        self,
        code: str,
        detail: str = "",
        *,
        hint: str = "",
        retryable: bool = True,
        expected: bool = False,
        until: str | None = None,
        facts: "SessionFacts | None" = None,
    ) -> None:
        super().__init__(code, detail, hint=hint)
        #: False when a second attempt is guaranteed to fail the same way.
        self.retryable = retryable
        #: True when this is the method working rather than the kit breaking —
        #: a blocked review, a red suite, a build that says it never finished.
        #: The run stops on these; it fails on everything else.
        self.expected = expected
        #: When a limited account comes back, in the provider's own words.
        self.until = until
        self.facts = facts or SessionFacts()


@dataclass(frozen=True)
class StepRequest:
    """What an executor is handed. A session reads `input_text` and nothing else.

    The three fields below it are for the executors that are programs: a
    program must not parse prose to find out which branch it is on or what an
    earlier step returned, so it is handed both as data. A session ignores
    them — everything they hold is already in the input the driver composed.
    """

    slug: str
    step_name: str
    attempt: int
    provider: str
    input_text: str
    workdir: Path
    project: Path | None = None
    branch: str = ""
    brief: str | None = None
    prior: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionFacts:
    """What level B knows and level A does not.

    A level-A adapter leaves this empty: it can start a session and read what
    it said, and that is all. Level B fills it, which is what makes a session
    safe to leave running for hours — somebody can see how full it is.
    """

    session: str | None = None
    model: str | None = None
    #: What the session was actually carrying when it last answered.
    context_used: int | None = None
    context_window: int | None = None
    #: Every token the account was billed for, cache re-reads included. Spend,
    #: not fullness: over several turns it outgrows the window many times over.
    tokens_billed: int | None = None
    cost_usd: float | None = None
    transcript: Path | None = None
    limited_until: str | None = None

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
            "tokens_billed": self.tokens_billed,
            "cost_usd": self.cost_usd,
            "transcript": str(self.transcript) if self.transcript else None,
            "limited_until": self.limited_until,
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
