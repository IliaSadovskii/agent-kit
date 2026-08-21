"""Running one step: compose the input, execute it, validate what comes back.

What happens when a step fails was settled with the plan: three attempts on the
role's provider, each enclosing why the last was refused, then the fallback
provider gets one, then the run stops and says which step, which provider, and
what the output was missing. Never silent, never infinite, and never a nudge —
typing "continue" at a stuck session is a guess wearing the clothes of a recovery.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..config import RoleConfig
from ..errors import ProviderError, StateError
from ..logs import get_logger
from ..state import Run, RunStore, Step
from ..steps import Registry, StepDefinition
from ..steps.contract import ContractRefusal, parse_output
from .compose import compose_input
from .executor import Executor, ExecutorFailed, ExecutorResult, StepRequest
from .workspace import StepWorkspace

ATTEMPTS_PER_PROVIDER = 3

log = get_logger("driver")


@dataclass
class AttemptRecord:
    attempt: int
    provider: str
    refusal: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.refusal is None


@dataclass
class StepOutcome:
    slug: str
    step: str
    passed: bool
    output: dict[str, Any] | None = None
    reason: str | None = None
    attempts: list[AttemptRecord] = field(default_factory=list)


class StepRunner:
    def __init__(
        self,
        store: RunStore,
        registry: Registry,
        executors: Mapping[str, Executor],
        roles: Mapping[str, RoleConfig] | None = None,
        default_provider: str | None = None,
        attempts_per_provider: int = ATTEMPTS_PER_PROVIDER,
    ) -> None:
        self.store = store
        self.registry = registry
        self.executors = dict(executors)
        self.roles = dict(roles or {})
        self.default_provider = default_provider
        self.attempts = attempts_per_provider

    # --- the one thing it does -------------------------------------------

    def run_next(self, slug: str) -> StepOutcome:
        run = self.store.load(slug)
        if run.finished:
            raise StateError("run-finished", f"{slug} is {run.status.value}; there is no next step")
        index = run.next_pending()
        if index is None:
            raise StateError("no-step-pending", f"{slug}: every step is done")

        definition = self.registry.get(run.steps[index].name)
        providers = self._providers_for(definition)
        workspace = StepWorkspace(self.store.run_root(slug), index, definition.name)
        enclosures = self._enclosures(run, index)

        outcome = StepOutcome(slug=slug, step=definition.name, passed=False)
        refusal: str | None = None

        for provider in providers:
            run = self.store.start_step(slug, provider=provider)
            step = run.steps[index]
            record = self._attempt(run, step, definition, workspace, provider, refusal, enclosures)
            outcome.attempts.append(record)

            if record.passed:
                self.store.pass_step(slug)
                outcome.passed = True
                outcome.output = workspace.read_output()
                log.info("%s: %s passed on %s (attempt %s)", slug, definition.name, provider, record.attempt)
                return outcome

            refusal = record.refusal
            self.store.fail_step(slug, f"{definition.name} on {provider}: {refusal}")
            log.info("%s: %s refused on %s — %s", slug, definition.name, provider, refusal)

        outcome.reason = (
            f"{definition.name} was refused {len(outcome.attempts)} times, last on "
            f"{outcome.attempts[-1].provider}: {refusal}"
        )
        self.store.fail_run(slug, outcome.reason)
        return outcome

    # --- one attempt ------------------------------------------------------

    def _attempt(
        self,
        run: Run,
        step: Step,
        definition: StepDefinition,
        workspace: StepWorkspace,
        provider: str,
        refusal: str | None,
        enclosures: list[tuple[str, str]],
    ) -> AttemptRecord:
        attempt = step.attempts
        text = compose_input(
            run=run,
            step=step,
            definition=definition,
            attempt=attempt,
            provider=provider,
            enclosures=enclosures,
            refusal=refusal,
            attempts_allowed=self.attempts,
        )
        workspace.write_input(attempt, text)

        request = StepRequest(
            slug=run.slug,
            step_name=definition.name,
            attempt=attempt,
            provider=provider,
            input_text=text,
            workdir=workspace.attempt_dir(attempt),
            project=Path(run.project) if run.project else None,
        )

        try:
            result = self.executors[provider].execute(request)
        except ExecutorFailed as failure:
            return self._refused(workspace, attempt, provider, f"{failure.code}: {failure.detail}", {})

        result = result if isinstance(result, ExecutorResult) else ExecutorResult(raw=str(result))
        workspace.write_raw(attempt, result.raw)
        meta = {"provider": provider, "attempt": attempt, "step": definition.name, **result.meta}
        workspace.write_meta(attempt, meta)

        try:
            output = definition.contract.check(parse_output(result.raw))
        except ContractRefusal as refused:
            return self._refused(workspace, attempt, provider, f"{refused.code}: {refused.detail}", meta)

        workspace.accept(attempt, output, meta)
        return AttemptRecord(attempt=attempt, provider=provider, meta=meta)

    def _refused(self, workspace: StepWorkspace, attempt: int, provider: str, reason: str, meta: dict) -> AttemptRecord:
        workspace.write_refusal(attempt, reason)
        return AttemptRecord(attempt=attempt, provider=provider, refusal=reason, meta=meta)

    # --- who runs it, and what it is given --------------------------------

    def _providers_for(self, definition: StepDefinition) -> list[str]:
        role = self.roles.get(definition.role)
        if role is None:
            if self.default_provider is None:
                raise ProviderError(
                    "no-provider", f"role {definition.role!r} is not in the role table and there is no default"
                )
            chain = [self.default_provider] * self.attempts
        else:
            chain = [role.provider] * self.attempts + list(role.fallback)

        for provider in dict.fromkeys(chain):
            if provider not in self.executors:
                raise ProviderError(
                    "unknown-provider",
                    f"{provider!r} runs role {definition.role!r} but no such provider is configured here",
                )
        return chain

    def _enclosures(self, run: Run, index: int) -> list[tuple[str, str]]:
        """Everything an earlier step produced, so this one never goes looking."""
        enclosed: list[tuple[str, str]] = []
        for earlier in range(index):
            step = run.steps[earlier]
            workspace = StepWorkspace(self.store.run_root(run.slug), earlier, step.name)
            output = workspace.read_output()
            if output is not None:
                enclosed.append((f"{earlier}-{step.name} returned", json.dumps(output, indent=2, ensure_ascii=False)))
        return enclosed
