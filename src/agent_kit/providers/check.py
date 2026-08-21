"""Measuring what a provider can actually do.

A level nobody measured is the same class of claim as a rule nobody tested. So
the kit climbs a ladder and says which rung failed:

    binary     the thing is there and can be run
    answers    it answers when asked what it is
    one_shot   given a step's input, it returns something
    contract   what it returned satisfies the step's contract
    observed   it can say how much context that session holds

Everything up to `one_shot` is level A. All five is level B. The probe step is
what is asked, which is why it exists.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..driver.compose import compose_input
from ..driver.executor import StepRequest
from ..logs import get_logger
from ..state import RunStore
from ..steps import builtin_registry
from ..steps.contract import ContractRefusal, parse_output
from .base import ExecutorFailed, SessionFacts
from .registry import build_executor, facts as declared_facts

#: In order. The first four are level A; all five are level B.
RUNGS = ("binary", "answers", "one_shot", "contract", "observed")

LEVEL_A_AT = "one_shot"

log = get_logger("providers.check")


@dataclass
class Rung:
    name: str
    passed: bool = False
    detail: str = ""


@dataclass
class CheckReport:
    provider: str
    declared_level: str
    rungs: list[Rung] = field(default_factory=list)
    facts: SessionFacts = field(default_factory=SessionFacts)
    raw: str = ""

    @property
    def failed(self) -> str | None:
        return next((rung.name for rung in self.rungs if not rung.passed), None)

    @property
    def level(self) -> str | None:
        """A or B, measured. None if it could not even do a one-shot job."""
        reached = {rung.name for rung in self.rungs if rung.passed}
        if not {"binary", "answers", "one_shot"} <= reached:
            return None
        return "B" if len(reached) == len(RUNGS) else "A"

    @property
    def matches_declaration(self) -> bool:
        return self.level == self.declared_level


def check_provider(name: str, options: dict[str, list[str]] | None = None, project: Path | None = None) -> CheckReport:
    """Climb the ladder. Nothing is left behind in the project it was run from."""
    declaration = declared_facts(name)
    report = CheckReport(provider=name, declared_level=declaration.level)
    rungs = {rung: Rung(rung) for rung in RUNGS}
    report.rungs = [rungs[name] for name in RUNGS]

    try:
        executor = build_executor(name, options or {})
    except ExecutorFailed as failure:
        rungs["binary"].detail = f"{failure.code}: {failure.detail}"
        return report

    rungs["binary"].passed, rungs["binary"].detail = _binary(executor, declaration.binary)
    if not rungs["binary"].passed:
        return report

    rungs["answers"].passed, rungs["answers"].detail = _answers(executor)
    if not rungs["answers"].passed:
        return report

    result = None
    try:
        result = _one_shot(executor, name, project)
        rungs["one_shot"].passed = True
        rungs["one_shot"].detail = f"{len(result.raw)} characters came back"
    except ExecutorFailed as failure:
        rungs["one_shot"].detail = f"{failure.code}: {failure.detail}"
        return report

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

    return report


def _binary(executor: Any, declared: str | None) -> tuple[bool, str]:
    binary = getattr(executor, "binary", None)
    if binary is None:
        return True, "nothing to run: this provider is not a process"
    path = Path(binary)
    if path.is_absolute() or "/" in binary:
        return (path.is_file(), str(path)) if path.is_file() else (False, f"{path} is not there")
    from shutil import which

    found = which(binary)
    return (bool(found), found or f"{binary} is not on PATH")


def _answers(executor: Any) -> tuple[bool, str]:
    version = getattr(executor, "version", None)
    if version is None:
        return True, "it does not answer questions about itself; nothing to ask"
    try:
        return True, version()
    except ExecutorFailed as failure:
        return False, f"{failure.code}: {failure.detail}"


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
