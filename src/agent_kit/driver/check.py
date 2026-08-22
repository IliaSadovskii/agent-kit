"""Measuring what a provider can actually do.

A level nobody measured is the same class of claim as a rule nobody tested. So
the kit climbs a ladder and says which rung failed:

    binary     the thing is there and can be run
    answers    it answers when asked what it is
    login      the account behind it answers, not just the binary
    one_shot   given a step's input, it returns something
    contract   what it returned satisfies the step's contract
    observed   it can say how much context that session holds
    limits     it can tell a limited account from a working one

The plan's own list, and level B is the last two together: *is it alive, how
much context, is it limited and until when.* A rung a provider cannot be asked
is marked so and counts as neither passed nor failed. The probe step is what is
asked, which is why it exists.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import KitError
from ..logs import get_logger
from ..providers.base import ExecutorFailed, SessionFacts
from ..providers.measured import remember as remembered
from ..providers.registry import build_executor, facts as declared_facts
from ..state import RunStore
from .compose import compose_input
from .executor import StepRequest
from ..steps import builtin_registry
from ..steps.contract import ContractRefusal, parse_output

#: In order. Getting this far is level A: it started and it answered.
RUNGS = ("binary", "answers", "login", "one_shot", "contract", "observed", "limits")

#: Level A is these; level B is every rung that applies.
LEVEL_A = ("binary", "answers", "login", "one_shot")

log = get_logger("providers.check")


@dataclass
class Rung:
    name: str
    passed: bool = False
    detail: str = ""
    #: False when this provider cannot be asked this question at all. Not a
    #: pass: a rung nobody climbed is not a rung anybody climbed.
    applies: bool = True

    @property
    def held(self) -> bool:
        """True when this rung is not in the way — passed, or not applicable."""
        return self.passed or not self.applies


@dataclass
class CheckReport:
    provider: str
    declared_level: str
    rungs: list[Rung] = field(default_factory=list)
    facts: SessionFacts = field(default_factory=SessionFacts)
    raw: str = ""

    @property
    def failed(self) -> str | None:
        return next((rung.name for rung in self.rungs if not rung.held), None)

    @property
    def level(self) -> str | None:
        """A or B, measured. None if it could not even do a one-shot job."""
        held = {rung.name for rung in self.rungs if rung.held}
        if not set(LEVEL_A) <= held:
            return None
        return "B" if len(held) == len(RUNGS) else "A"

    @property
    def earns_what_it_declares(self) -> bool:
        """False only when it earned *less* than it claims. More is good news."""
        order = {None: 0, "A": 1, "B": 2}
        return order[self.level] >= order.get(self.declared_level, 0)


def check_provider(
    name: str,
    options: dict[str, list[str]] | None = None,
    project: Path | None = None,
    remember: bool = False,
) -> CheckReport:
    """Climb the ladder. Nothing is left behind in the project it was run from."""
    declaration = declared_facts(name)
    report = CheckReport(provider=name, declared_level=declaration.level)
    rungs = {rung: Rung(rung) for rung in RUNGS}
    report.rungs = [rungs[rung] for rung in RUNGS]

    def done() -> CheckReport:
        if remember:
            remembered(name, report.level, report.failed,
                       next((rung.detail for rung in report.rungs if not rung.held), ""))
        return report

    try:
        executor = build_executor(name, options or {})
    except KitError as failure:
        rungs["binary"].detail = f"{failure.code}: {failure.detail}"
        return done()

    _fill(rungs["binary"], *_binary(executor))
    if not rungs["binary"].held:
        return done()

    _fill(rungs["answers"], *_answers(executor))
    if not rungs["answers"].held:
        return done()

    try:
        result = _one_shot(executor, name, project)
        rungs["login"].passed = True
        rungs["login"].detail = "the account answered"
        rungs["one_shot"].passed = True
        rungs["one_shot"].detail = f"{len(result.raw)} characters came back"
    except ExecutorFailed as failure:
        reason = f"{failure.code}: {failure.detail}"
        if _is_about_login(reason):
            rungs["login"].detail = reason
        else:
            rungs["login"].passed = True
            rungs["login"].detail = "the account answered, and then the job failed"
            rungs["one_shot"].detail = reason
        return done()

    report.raw = result.raw
    report.facts = result.facts

    probe = builtin_registry().get("probe")
    try:
        probe.contract.check(parse_output(result.raw))
        rungs["contract"].passed = True
        rungs["contract"].detail = "the answer satisfied the probe's contract"
    except ContractRefusal as refused:
        rungs["contract"].detail = f"{refused.code}: {refused.detail}"

    if result.facts.observed:
        rungs["observed"].passed = True
        rungs["observed"].detail = (
            f"{result.facts.context_used:,} of {result.facts.context_window:,} tokens"
        )
    else:
        rungs["observed"].detail = "it cannot say how much context the session holds"

    _fill(rungs["limits"], *_limits(executor))
    return done()


def _fill(rung: Rung, passed: bool, detail: str, applies: bool = True) -> None:
    rung.passed, rung.detail, rung.applies = passed, detail, applies


def _is_about_login(reason: str) -> bool:
    words = reason.lower()
    return any(phrase in words for phrase in ("login", "log in", "api key", "unauthor", "authenticat", "credential"))


def _limits(executor: Any) -> tuple[bool, str, bool]:
    """Can this provider tell a limited account from a working one?

    Measured, not assumed: the declared phrases are run through the adapter's own
    detection, and it has to come back with an hour attached.
    """
    declared = getattr(executor, "declared", None)
    refuse = getattr(executor, "_refuse_if_limited", None)
    if declared is None or refuse is None:
        return False, "it cannot be asked about limits", False
    if not getattr(declared, "reads_limits", False):
        return False, "it declares no way of telling a limited account", True

    sample = f"{declared.limit_says[0]}. Your limit will reset at 5pm (UTC)."
    try:
        refuse(sample)
    except ExecutorFailed as refused:
        if refused.code == "provider-limited" and refused.until:
            return True, f"a limited account is read, with the hour it resets ({refused.until})", True
        return False, f"a limit is noticed but the hour is not read: {refused.detail}", True
    return False, "its own declared phrases are not recognised", True


def _binary(executor: Any) -> tuple[bool, str, bool]:
    binary = getattr(executor, "binary", None)
    if binary is None:
        return False, "this provider is not a process; there is nothing to find", False
    path = Path(binary)
    if path.is_absolute() or "/" in binary:
        return (True, str(path), True) if path.is_file() else (False, f"{path} is not there", True)
    from shutil import which

    found = which(binary)
    return (bool(found), found or f"{binary} is not on PATH", True)


def _answers(executor: Any) -> tuple[bool, str, bool]:
    version = getattr(executor, "version", None)
    if version is None:
        return False, "it cannot be asked what it is", False
    try:
        return True, version(), True
    except ExecutorFailed as failure:
        return False, f"{failure.code}: {failure.detail}", True


def _one_shot(executor: Any, provider: str, project: Path | None) -> Any:
    """Ask the probe step, in a directory the check owns and then throws away."""
    with tempfile.TemporaryDirectory(prefix="agent-kit-check-") as scratch:
        workdir = Path(scratch)
        run = RunStore(workdir).create("provider-check", steps=["probe"], project=str(project or workdir))
        probe = builtin_registry().get("probe")
        text = compose_input(run=run, definition=probe, attempt=1, provider=provider, attempts_allowed=1)
        return executor.execute(
            StepRequest(
                slug=run.slug,
                step_name=probe.name,
                attempt=1,
                provider=provider,
                input_text=text,
                workdir=workdir,
                project=project,
            )
        )
