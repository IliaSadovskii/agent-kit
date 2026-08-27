"""One turn of a session, and the chain of attempts around it.

Everything that costs money to get wrong lives here exactly once: the slot the
machine grants, the pause that grows between attempts, the fallback provider,
the reason for the last refusal enclosed in the next input, and the paperwork
every attempt leaves behind.

Two callers use it and neither owns it. `runner.py` drives the steps of a run,
where an attempt that passed may still be one part of a split step, a question
for the owner, or a closed gate — so what happens *after* a pass stays there.
`sitting/` drives the hour with the owner, where an attempt that passed is
simply the answer. Writing the chain twice would put a second copy of the one
mechanism the bench has a dozen traps for beside the copy those traps watch,
and the second copy would have none of them.

What the chain needs to know about who it is running for is seven fields, and
`Subject` is those seven. A `Run` is one; a sitting is another.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from ..config import DEFAULT_BACKOFF, DEFAULT_WAIT, RoleConfig
from ..errors import ProviderError
from ..logs import get_logger
from ..machine import Busy, Ceilings, Lease, Ledger, Want
from ..steps import StepDefinition
from ..steps.contract import Contract, ContractRefusal, parse_output
from .compose import compose_input
from .executor import Executor, ExecutorFailed, ExecutorResult, StepRequest
from .workspace import StepWorkspace

ATTEMPTS_PER_PROVIDER = 3

#: How long a refused step waits before it is tried again, doubling with each
#: refusal. The machine may name its own — `machine.backoff` — and zero means
#: what every kit before this number did: straight back round the chain.
BACKOFF = DEFAULT_BACKOFF

#: How often a waiting driver asks the ledger again. There is no signal and no
#: socket: a poll of a local file is cheaper than a protocol to get wrong.
POLL = 1.0

#: How often a splittable step may stop short and be carried on. A step that
#: needs more than this is not a step that ran out of room; it is a step that
#: was too big, and that is a design error to fix rather than a night to survive.
CONTINUATIONS_ALLOWED = 3

log = get_logger("driver")


@runtime_checkable
class Subject(Protocol):
    """Who a turn is being run for, in the only seven facts a turn reads."""

    slug: str
    branch: str
    project: str | None
    tree: str | None
    base: str
    brief: str | None
    needs: list[str]


@dataclass
class Standing:
    """A subject that is not a run: the sitting's own, and the tests'."""

    slug: str
    branch: str = ""
    project: str | None = None
    tree: str | None = None
    base: str = ""
    brief: str | None = None
    needs: list[str] = field(default_factory=list)


@dataclass
class AttemptRecord:
    attempt: int
    on_provider: int
    provider: str
    refusal: str | None = None
    #: False when asking this provider again is guaranteed to fail the same way.
    retryable: bool = True
    #: True when it was the tool that refused — a session that died, timed out,
    #: crashed — rather than the answer failing the contract. The pause between
    #: attempts reads it: waiting mends a provider having a bad minute, and
    #: mends nothing about a model that wrote the wrong JSON.
    from_the_tool: bool = False
    #: True when this was the method working rather than the kit breaking.
    expected: bool = False
    #: Set when the machine said no before any session was started: the ceiling
    #: was reached, or the account is known to be limited. Nothing was spent and
    #: nothing about the run changed, so this is not a failed attempt at all.
    busy: Busy | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.refusal is None


@dataclass
class Turn:
    """What one walk down the chain came to."""

    attempts: list[AttemptRecord] = field(default_factory=list)
    #: The attempt that satisfied the contract, where one did.
    record: AttemptRecord | None = None
    #: True when the caller asked for the chain to be dropped mid-way — today,
    #: only because somebody asked the run to stop while it waited for a slot.
    abandoned: bool = False

    @property
    def passed(self) -> bool:
        return self.record is not None

    @property
    def last(self) -> AttemptRecord | None:
        return self.attempts[-1] if self.attempts else None


class Sessions:
    """The chain, the slot and the pause — held once, used by every driver."""

    def __init__(
        self,
        executors: Mapping[str, Executor],
        root: Path,
        ledger: Ledger,
        roles: Mapping[str, RoleConfig] | None = None,
        default_provider: str | None = None,
        attempts_per_provider: int = ATTEMPTS_PER_PROVIDER,
        backoff: int = BACKOFF,
        continuations_allowed: int = CONTINUATIONS_ALLOWED,
        ceilings: Ceilings | None = None,
        accounts: Mapping[str, str] | None = None,
        wait: int = DEFAULT_WAIT,
        pause: Callable[[float], Any] | None = None,
        say: Callable[[str], Any] | None = None,
    ) -> None:
        self.executors = dict(executors)
        self.root = Path(root)
        self.ledger = ledger
        self.roles = dict(roles or {})
        self.default_provider = default_provider
        self.attempts = attempts_per_provider
        self.backoff = backoff
        self.continuations = continuations_allowed
        self.ceilings = ceilings or Ceilings()
        self.accounts = dict(accounts or {})
        self.wait = wait
        self.pause = pause or time.sleep
        self.say = say or log.info

    # --- who runs it ------------------------------------------------------

    def account(self, provider: str) -> str:
        """The quota pool. Where a machine names none, a provider is its own."""
        return self.accounts.get(provider) or provider

    def providers_for(self, definition: StepDefinition) -> list[str]:
        if not definition.by_agent:
            # A program has no role, no fallback and no second chance: what it
            # refused once it refuses the same way, and each retry costs the
            # project's whole suite.
            if definition.executor not in self.executors:
                raise ProviderError(
                    "unknown-program",
                    f"{definition.name} is executed by {definition.executor}, which is not configured here",
                )
            return [definition.executor]

        role = self.roles.get(definition.role)
        if role is None:
            if self.default_provider is None:
                raise ProviderError(
                    "no-provider", f"role {definition.role!r} is not in the role table and there is no default"
                )
            chain = [self.default_provider] * self.attempts
        else:
            spares = [name for name in dict.fromkeys(role.fallback) if name != role.provider]
            chain = [role.provider] * self.attempts + spares

        for provider in dict.fromkeys(chain):
            if provider not in self.executors:
                raise ProviderError(
                    "unknown-provider",
                    f"{provider!r} runs role {definition.role!r} but no such provider is configured here",
                )
        return chain

    # --- what the machine grants ------------------------------------------

    def where(self, subject: Subject) -> str:
        return str(Path(subject.project) if subject.project else self.root.resolve())

    def slot(
        self, subject: Subject, step_name: str, provider: str, others_left: bool = False,
        stop_pending: Callable[[str, str], Any] | None = None,
    ) -> Lease | Busy:
        """One live session's worth of machine, waited for if waiting is the best there is."""
        want = Want(
            account=self.account(provider),
            provider=provider,
            project=self.where(subject),
            slug=subject.slug,
            step=step_name,
        )
        got = self.ledger.take(want, self.ceilings)
        if got.granted or self.wait <= 0 or self._ask_somebody_else(got, others_left):
            return got

        deadline = time.monotonic() + self.wait
        said = ""
        self.ledger.wants_one(want)
        try:
            while not got.granted:
                if got.detail != said:
                    # Once, when the answer changes. A night's log that scrolls
                    # a line a second is a night's log nobody reads.
                    said = got.detail
                    self.say(f"{subject.slug}: waiting — {got.code}: {got.detail}")
                # A run that is stuck is the run somebody is most likely to want
                # stopped, so the stop is read here as well as at the step
                # boundary. Left standing for the caller to consume and act on.
                if stop_pending is not None and stop_pending(want.project, subject.slug) is not None:
                    return Busy("stopped-by-request", "the run was asked to stop while it waited")
                if time.monotonic() >= deadline:
                    return got
                self.pause(POLL)
                got = self.ledger.take(want, self.ceilings)
        finally:
            self.ledger.gives_up(want)
        return got

    @staticmethod
    def _ask_somebody_else(got: Busy, others_left: bool) -> bool:
        """Waiting hours for a reset while a free account stands by is not waiting, it is idling.

        A full machine binds every provider, so waiting for a slot is right
        whoever is next in the chain. A limit binds one account, and the chain
        exists precisely because another one may be answering.
        """
        return others_left and got.code == "provider-limited"

    def breathe(self, subject: Subject, step_name: str, attempts: list[AttemptRecord]) -> None:
        """Wait before the next attempt, and wait longer the more of them there have been.

        A provider that is briefly overloaded answers a session started a second
        later exactly as it answered this one, so a chain with no pause in it
        spends every attempt it has inside the minute the trouble lasts. The
        doubling needs no ceiling of its own: what bounds the waiting is the
        ceiling on attempts, which is three on a provider and one on each spare.

        Only the tool's own refusals are waited out. An answer that failed the
        contract is a model that wrote the wrong JSON, and what mends that is the
        reason enclosed in the next input, not a minute of nothing.
        """
        refusals = sum(1 for one in attempts if one.refusal is not None and one.busy is None)
        seconds = self.backoff * 2 ** max(refusals - 1, 0)
        if seconds <= 0:
            return
        self.say(f"{subject.slug}: backing-off {seconds}s — {step_name} was refused by the tool")
        log.info("%s: backing-off %ss before %s is tried again", subject.slug, seconds, step_name)
        self.pause(seconds)

    # --- the chain --------------------------------------------------------

    def turn(
        self,
        subject: Subject,
        definition: StepDefinition,
        workspace: StepWorkspace,
        contract: Contract,
        enclosures: list[tuple[str, str]],
        prior: dict[str, dict[str, Any]],
        *,
        on_start: Callable[[str], tuple[Subject, int]],
        on_refusal: Callable[[str, str], Any] | None = None,
        on_broke: Callable[[str, BaseException], Any] | None = None,
        on_busy: Callable[[str, Busy], bool] | None = None,
        stop_pending: Callable[[str, str], Any] | None = None,
        attempt_now: Callable[[], int] | None = None,
        parts_done: int = 0,
        providers: list[str] | None = None,
    ) -> Turn:
        """Down the chain until something satisfies the contract or nothing is left.

        The caller says what a start and a refusal mean for its own state; this
        says what an attempt is. Nothing here writes anybody's state, and that
        is what lets a run and a sitting share it.
        """
        remaining = list(self.providers_for(definition) if providers is None else providers)
        walked = Turn()
        seen: dict[str, int] = {}
        refusal: str | None = None

        while remaining:
            provider = remaining.pop(0)

            lease = None
            if definition.by_agent:
                # The machine is asked before the state moves. A caller that
                # cannot have a session has not attempted anything, and its step
                # must look exactly as it did.
                others = [name for name in remaining if name != provider]
                got = self.slot(subject, definition.name, provider, bool(others), stop_pending)
                if not got.granted:
                    if on_busy is not None and on_busy(provider, got):
                        walked.abandoned = True
                        return walked
                    walked.attempts.append(
                        AttemptRecord(
                            attempt=attempt_now() if attempt_now else 0,
                            on_provider=seen.get(provider, 0),
                            provider=provider,
                            refusal=f"{got.code}: {got.detail}",
                            retryable=False,
                            busy=got,
                        )
                    )
                    remaining = [name for name in remaining if name != provider]
                    continue
                lease = got

            seen[provider] = seen.get(provider, 0) + 1
            try:
                subject, number = on_start(provider)
                record = self.attempt(
                    subject, number, definition, workspace, provider, seen[provider], refusal,
                    enclosures, prior, parts_done, contract,
                )
            except BaseException as escaped:
                # Whatever broke, the state must not be left holding a step
                # nobody can move. The reason is written down before it is raised.
                if on_broke is not None:
                    on_broke(provider, escaped)
                raise
            finally:
                # A slot that outlives its session is a slot nobody gets back
                # until the driver dies, and the driver is what is still running.
                self.ledger.release(lease)
            walked.attempts.append(record)

            if record.passed:
                walked.record = record
                return walked

            refusal = record.refusal
            if on_refusal is not None:
                on_refusal(provider, refusal or "")

            if not record.retryable:
                # Three tries at a missing binary is three times nothing, and
                # with a real provider each try is a session, and a session is
                # money. This provider has said its piece; ask the next one.
                remaining = [name for name in remaining if name != provider]
            elif remaining and record.from_the_tool:
                self.breathe(subject, definition.name, walked.attempts)

        return walked

    # --- one attempt ------------------------------------------------------

    def attempt(
        self,
        subject: Subject,
        attempt: int,
        definition: StepDefinition,
        workspace: StepWorkspace,
        provider: str,
        on_provider: int,
        refusal: str | None,
        enclosures: list[tuple[str, str]],
        prior: dict[str, dict[str, Any]],
        parts_done: int = 0,
        contract: Contract | None = None,
    ) -> AttemptRecord:
        contract = definition.contract if contract is None else contract
        allowed = self.attempts if definition.by_agent else 1
        text = compose_input(
            run=subject,
            definition=definition,
            attempt=on_provider,
            provider=provider,
            enclosures=enclosures,
            refusal=refusal,
            attempts_allowed=allowed,
            parts_done=parts_done,
            parts_allowed=self.continuations,
            contract=contract,
        )
        workspace.write_input(attempt, text)

        request = StepRequest(
            slug=subject.slug,
            step_name=definition.name,
            attempt=attempt,
            provider=provider,
            input_text=text,
            workdir=workspace.attempt_dir(attempt),
            project=Path(subject.project) if subject.project else self.root.resolve(),
            tree=Path(subject.tree) if subject.tree else None,
            branch=subject.branch,
            base=subject.base,
            brief=subject.brief,
            prior=prior,
        )

        try:
            result = self.executors[provider].execute(request)
        except ExecutorFailed as failure:
            if failure.code == "provider-limited":
                # One session paid to learn this. Writing it down is what makes
                # it cost the next one nothing — and the next one may be in
                # another project, which is why it goes to the machine's ledger
                # and not into this run's record.
                self.ledger.limit(
                    self.account(provider),
                    failure.until,
                    said_by=f"{subject.slug}/{definition.name}",
                )
            # What the attempt spent before it failed is recorded too: the spend
            # must be visible exactly when the kit is burning money on retries.
            return self.refused(
                workspace,
                attempt,
                on_provider,
                provider,
                f"{failure.code}: {failure.detail}",
                {"provider": provider, "attempt": attempt, "step": definition.name, **failure.facts.as_dict()},
                retryable=failure.retryable,
                expected=failure.expected,
                from_the_tool=True,
            )
        except Exception as crash:
            # An adapter is somebody else's code around somebody else's CLI. A
            # surprise from it is an attempt that did not work, not a run that
            # cannot continue — and the type is written down, so it is fixable.
            return self.refused(
                workspace, attempt, on_provider, provider, f"provider-crashed: {named(crash)}", {},
                from_the_tool=True,
            )

        result = result if isinstance(result, ExecutorResult) else ExecutorResult(raw=str(result))
        workspace.write_raw(attempt, result.raw)
        meta = {
            "provider": provider,
            "attempt": attempt,
            "attempt_on_provider": on_provider,
            "step": definition.name,
            **result.facts.as_dict(),
            **result.meta,
        }
        workspace.write_meta(attempt, meta)

        try:
            output = contract.check(parse_output(result.raw))
        except ContractRefusal as refused:
            return self.refused(
                workspace, attempt, on_provider, provider, f"{refused.code}: {refused.detail}", meta
            )

        workspace.accept(attempt, output, meta)
        return AttemptRecord(attempt=attempt, on_provider=on_provider, provider=provider, meta=meta)

    def refused(
        self,
        workspace: StepWorkspace,
        attempt: int,
        on_provider: int,
        provider: str,
        reason: str,
        meta: dict,
        retryable: bool = True,
        expected: bool = False,
        from_the_tool: bool = False,
    ) -> AttemptRecord:
        workspace.write_refusal(attempt, reason)
        if meta:
            workspace.write_meta(attempt, meta)
        return AttemptRecord(
            attempt=attempt,
            on_provider=on_provider,
            provider=provider,
            refusal=reason,
            retryable=retryable,
            expected=expected,
            from_the_tool=from_the_tool,
            meta=meta,
        )


def named(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"
