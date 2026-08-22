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
from ..errors import KitError, ProviderError, StateError
from ..knowledge import DEFAULT_DIR as KNOWLEDGE_DIR, Knowledge
from ..logs import get_logger
from ..state import DEFAULT_STEPS, Run, RunStore
from ..steps import Registry, StepDefinition
from ..steps.contract import ContractRefusal, parse_output
from .compose import compose_input
from .executor import Executor, ExecutorFailed, ExecutorResult, StepRequest
from .workspace import StepWorkspace

ATTEMPTS_PER_PROVIDER = 3

#: How often a splittable step may stop short and be carried on. A step that
#: needs more than this is not a step that ran out of room; it is a step that
#: was too big, and that is a design error to fix rather than a night to survive.
CONTINUATIONS_ALLOWED = 3

log = get_logger("driver")


@dataclass
class AttemptRecord:
    attempt: int
    on_provider: int
    provider: str
    refusal: str | None = None
    #: False when asking this provider again is guaranteed to fail the same way.
    retryable: bool = True
    #: True when this was the method working rather than the kit breaking.
    expected: bool = False
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
        continuations_allowed: int = CONTINUATIONS_ALLOWED,
    ) -> None:
        self.store = store
        self.registry = registry
        self.executors = dict(executors)
        self.roles = dict(roles or {})
        self.default_provider = default_provider
        self.attempts = attempts_per_provider
        self.continuations = continuations_allowed

    # --- the one thing it does -------------------------------------------

    def run_next(self, slug: str) -> StepOutcome:
        run = self.store.load(slug)
        if run.finished:
            raise StateError("run-finished", f"{slug} is {run.status.value}; there is no next step")

        if run.running is not None:
            # A driver was killed between starting a step and hearing back. The
            # step is nobody's now; it goes back to pending and is tried again.
            left = run.running.name
            run = self.store.refuse_step(slug, f"{left}: the driver that started this step never came back")
            log.info("%s: %s was left running by a driver that vanished; trying again", slug, left)

        index = run.next_pending()
        if index is None:
            raise StateError("no-step-pending", f"{slug}: every step is done")

        definition = self.registry.get(run.steps[index].name)
        contract = definition.contract_in(self._keeps_knowledge(run))
        providers = self._providers_for(definition)
        workspace = StepWorkspace(self.store.run_root(slug), index, definition.name)
        enclosures, prior = self._enclosures(run, index, definition)

        outcome = StepOutcome(slug=slug, step=definition.name, passed=False)
        refusal: str | None = None
        seen: dict[str, int] = {}
        parts = workspace.read_parts() if definition.splittable else []

        remaining = list(providers)
        while remaining:
            provider = remaining.pop(0)
            seen[provider] = seen.get(provider, 0) + 1
            run = self.store.start_step(slug, provider=provider)
            try:
                record = self._attempt(
                    run, index, definition, workspace, provider, seen[provider], refusal,
                    enclosures + _parts_enclosure(parts), prior, len(parts), contract,
                )
            except BaseException as escaped:
                # Whatever broke, the state must not be left holding a step
                # nobody can move. The reason is written down before it is raised.
                self.store.refuse_step(slug, f"{definition.name} on {provider}: {_named(escaped)}")
                raise
            outcome.attempts.append(record)

            if record.passed:
                output = workspace.read_output() or {}
                if definition.splittable:
                    workspace.add_part(output)
                    parts.append(output)
                if definition.splittable and output.get("complete") is False:
                    room = self._carry_on(slug, definition, parts, outcome)
                    if room is None:
                        return outcome
                    # A part is real work, not a refused attempt: the provider
                    # chain starts again and no refusal is carried forward.
                    remaining, refusal, seen = list(providers), None, {}
                    continue

                if definition.splittable and len(parts) > 1:
                    # Several sessions did this step, each answering only for
                    # its own part. What the next step reads must be all of it.
                    output = contract.merge(parts)
                    workspace.accept(record.attempt, output, record.meta)
                self.store.pass_step(slug)
                outcome.passed = True
                outcome.output = output
                log.info("%s: %s passed on %s (attempt %s)", slug, definition.name, provider, record.attempt)

                if definition.gate and output.get(definition.gate) is False:
                    # The step did its work and what it recorded is that the run
                    # must not go on. Nothing was refused and nothing broke, so
                    # the run stops rather than fails: `failed` is for a kit that
                    # could not do its work, and this one did.
                    outcome.reason = (
                        f"gate-closed: {definition.name} passed and recorded {definition.gate} as "
                        "false; the run does not go past that"
                    )
                    self.store.halt(slug, outcome.reason)
                    log.info("%s: %s stopped the run: %s is false", slug, definition.name, definition.gate)
                return outcome

            refusal = record.refusal
            self.store.refuse_step(slug, f"{definition.name} on {provider}: {refusal}")
            log.info("%s: %s refused on %s — %s", slug, definition.name, provider, refusal)

            if not record.retryable:
                # Three tries at a missing binary is three times nothing, and
                # with a real provider each try is a session, and a session is
                # money. This provider has said its piece; ask the next one.
                remaining = [name for name in remaining if name != provider]

        last = outcome.attempts[-1]
        if last.expected:
            # The method said no. That is what it is for, and it is not a fault
            # of the kit, so the run is stopped and the reason is the answer.
            outcome.reason = f"{definition.name}: {refusal}"
            self.store.stop(slug, outcome.reason)
            log.info("%s: %s refused delivery — %s", slug, definition.name, refusal)
            return outcome

        outcome.reason = (
            f"{definition.name} was refused {len(outcome.attempts)} times, last on "
            f"{last.provider}: {refusal}"
        )
        self.store.fail_run(slug, outcome.reason)
        return outcome

    def _carry_on(
        self, slug: str, definition: StepDefinition, parts: list[dict[str, Any]], outcome: StepOutcome
    ) -> int | None:
        """A splittable step stopped short. Say so in its own words, or stop the run."""
        left = ", ".join(parts[-1].get("remaining") or []) or "it did not say what is left"
        if len(parts) > self.continuations:
            outcome.reason = (
                f"step-outgrew-its-room: {definition.name} had {len(parts)} sessions and is still not "
                f"finished — {left}"
            )
            self.store.fail_run(slug, outcome.reason)
            log.info("%s: %s outgrew its room after %s parts", slug, definition.name, len(parts))
            return None

        self.store.continue_step(
            slug, f"{definition.name} part {len(parts)} is done and it goes on: {left}"
        )
        log.info("%s: %s carries on after part %s", slug, definition.name, len(parts))
        return len(parts)



    # --- one attempt ------------------------------------------------------

    def _attempt(
        self,
        run: Run,
        index: int,
        definition: StepDefinition,
        workspace: StepWorkspace,
        provider: str,
        on_provider: int,
        refusal: str | None,
        enclosures: list[tuple[str, str]],
        prior: dict[str, dict[str, Any]],
        parts_done: int = 0,
        contract: Any = None,
    ) -> AttemptRecord:
        contract = definition.contract if contract is None else contract
        attempt = run.steps[index].attempts
        allowed = self.attempts if definition.by_agent else 1
        text = compose_input(
            run=run,
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
            slug=run.slug,
            step_name=definition.name,
            attempt=attempt,
            provider=provider,
            input_text=text,
            workdir=workspace.attempt_dir(attempt),
            project=Path(run.project) if run.project else self.store.paths.root.resolve(),
            branch=run.branch,
            brief=run.brief,
            prior=prior,
        )

        try:
            result = self.executors[provider].execute(request)
        except ExecutorFailed as failure:
            # What the attempt spent before it failed is recorded too: the spend
            # must be visible exactly when the kit is burning money on retries.
            return self._refused(
                workspace,
                attempt,
                on_provider,
                provider,
                f"{failure.code}: {failure.detail}",
                {"provider": provider, "attempt": attempt, "step": definition.name, **failure.facts.as_dict()},
                retryable=failure.retryable,
                expected=failure.expected,
            )
        except Exception as crash:
            # An adapter is somebody else's code around somebody else's CLI. A
            # surprise from it is an attempt that did not work, not a run that
            # cannot continue — and the type is written down, so it is fixable.
            return self._refused(
                workspace, attempt, on_provider, provider, f"provider-crashed: {_named(crash)}", {}
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
            return self._refused(
                workspace, attempt, on_provider, provider, f"{refused.code}: {refused.detail}", meta
            )

        workspace.accept(attempt, output, meta)
        return AttemptRecord(attempt=attempt, on_provider=on_provider, provider=provider, meta=meta)

    def _refused(
        self,
        workspace: StepWorkspace,
        attempt: int,
        on_provider: int,
        provider: str,
        reason: str,
        meta: dict,
        retryable: bool = True,
        expected: bool = False,
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
            meta=meta,
        )

    # --- who runs it, and what it is given --------------------------------

    def _providers_for(self, definition: StepDefinition) -> list[str]:
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

    def _project_of(self, run: Run):
        """What the project declares, or nothing when it declares nothing.

        A run against a project with no declaration is still a run — the probe
        needs none — so this never raises. The steps that cannot work without
        one refuse for themselves, by name.
        """
        from ..project import read_project

        try:
            return read_project(Path(run.project) if run.project else self.store.paths.root)
        except KitError:
            return None

    def _keeps_knowledge(self, run: Run) -> bool:
        project = self._project_of(run)
        return bool(project and project.keeps_knowledge)

    def _knowledge_of(self, run: Run) -> Knowledge:
        project = self._project_of(run)
        root = Path(run.project) if run.project else self.store.paths.root
        return Knowledge(project.knowledge_dir if project else root / KNOWLEDGE_DIR)

    def _enclosures(
        self, run: Run, index: int, definition: StepDefinition | None = None
    ) -> tuple[list[tuple[str, str]], dict[str, dict[str, Any]]]:
        """Everything an earlier step produced, so this one never goes looking.

        Twice, because the two kinds of executor read differently: a session is
        handed prose it can read, a program is handed the same outputs as data.

        A step that must address the knowledge is handed an index of it here for
        the same reason: reading is never an instruction, so there is no reading
        to skip and nothing to check that it happened.
        """
        enclosed: list[tuple[str, str]] = []
        prior: dict[str, dict[str, Any]] = {}
        for earlier in range(index):
            step = run.steps[earlier]
            workspace = StepWorkspace(self.store.run_root(run.slug), earlier, step.name)
            output = workspace.read_output()
            if output is not None:
                enclosed.append((f"{earlier}-{step.name} returned", json.dumps(output, indent=2, ensure_ascii=False)))
                prior[step.name] = output
        if definition is not None and definition.needs_knowledge:
            enclosed.append(("the project's knowledge, as an index", self._knowledge_of(run).index()))
        return enclosed, prior


def create_run(
    store: RunStore,
    registry: Registry,
    slug: str,
    steps: list[str] | None = None,
    project: str | None = None,
    brief: str | None = None,
) -> Run:
    """A run may only be created from steps that exist.

    The check lives here rather than in the state, so the arrow keeps pointing
    one way: state, then the step contract, then the driver.
    """
    wanted = list(steps or DEFAULT_STEPS)
    for name in wanted:
        definition = registry.get(name)
        if definition.needs_brief and not (brief or "").strip():
            raise StateError(
                "no-brief",
                f"{name} decides what to do about a feature, and this run does not say which",
                hint="agent-kit run new <slug> --brief '<what to build>'",
            )
    # A run always knows where it is. A session that does not is run wherever
    # the driver happened to keep its paperwork, which is nowhere useful.
    return store.create(
        slug, steps=steps, project=project or str(store.paths.root.resolve()), brief=brief
    )


def _parts_enclosure(parts: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """What the earlier sessions of this same step produced."""
    return [
        (f"this step already did part {number}", json.dumps(part, indent=2, ensure_ascii=False))
        for number, part in enumerate(parts, start=1)
    ]


def _named(error: BaseException) -> str:
    """A failure anybody can act on names its type as well as its message."""
    return f"{type(error).__name__}: {error}".strip().rstrip(":")
