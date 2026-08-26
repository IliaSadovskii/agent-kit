"""Running one step: compose the input, execute it, validate what comes back.

What happens when a step fails was settled with the plan: three attempts on the
role's provider, each enclosing why the last was refused, then the fallback
provider gets one, then the run stops and says which step, which provider, and
what the output was missing. Never silent, never infinite, and never a nudge —
typing "continue" at a stuck session is a guess wearing the clothes of a recovery.

Between attempts there is a pause, and it grows: a provider having a bad minute
is answered by waiting it out, and a chain with no pause in it spends all four
of its attempts in the time four cold starts take.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..config import DEFAULT_BACKOFF, DEFAULT_WAIT, RoleConfig
from ..errors import ConfigError, KitError, ProviderError, StateError
from ..hook import write_pre_push
from ..knowledge import DEFAULT_DIR as KNOWLEDGE_DIR, Knowledge
from ..logs import get_logger
from ..machine import Busy, Ceilings, Lease, Ledger, Want, ledger_path
from ..owner import ANSWERED, HAD_ROUND, NOBODY, Owner, Question, Settled, as_assumption, questions_of
from ..paths import Paths
from ..project import DEFAULT_BRANCH, read_project, refuse_commands_that_start_nothing
from ..state import DEFAULT_STEPS, Run, RunStore, StepStatus
from ..steps import Registry, StepDefinition
from ..steps.contract import ContractRefusal, parse_output
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
class Asked:
    """What one round of asking the owner came to."""

    settled: list[Settled]
    answers: bool
    stopped: bool
    note: str


@dataclass
class StepOutcome:
    slug: str
    step: str
    passed: bool
    output: dict[str, Any] | None = None
    reason: str | None = None
    attempts: list[AttemptRecord] = field(default_factory=list)
    #: True when a person stopped this run rather than the method refusing it.
    #: The exit code that means *the operator stopped it* is 130, and reading a
    #: person's decision as the method's would be a lie about who said no.
    interrupted: bool = False


class StepRunner:
    def __init__(
        self,
        store: RunStore,
        registry: Registry,
        executors: Mapping[str, Executor],
        roles: Mapping[str, RoleConfig] | None = None,
        default_provider: str | None = None,
        attempts_per_provider: int = ATTEMPTS_PER_PROVIDER,
        backoff: int = BACKOFF,
        continuations_allowed: int = CONTINUATIONS_ALLOWED,
        ledger: Ledger | None = None,
        ceilings: Ceilings | None = None,
        accounts: Mapping[str, str] | None = None,
        wait: int = DEFAULT_WAIT,
        pause: Any = None,
        say: Any = None,
        owner: Owner | None = None,
    ) -> None:
        self.store = store
        self.registry = registry
        self.executors = dict(executors)
        self.roles = dict(roles or {})
        self.default_provider = default_provider
        self.attempts = attempts_per_provider
        self.backoff = backoff
        self.continuations = continuations_allowed
        # There is no driver without a ledger. A ceiling that can be left out is
        # a ceiling that is off wherever somebody forgot it, which is the shape
        # of every defect the plan's measurement found.
        self.ledger = ledger or Ledger(ledger_path(Paths.from_env()))
        self.ceilings = ceilings or Ceilings()
        self.accounts = dict(accounts or {})
        self.wait = wait
        self.pause = pause or time.sleep
        self.say = say or log.info
        # There is no driver without an owner either. A machine that configured
        # no channel gets one that has none: the question still takes its
        # default, and the default is still written down as an assumption.
        self.owner = owner or Owner(channel=None, ledger=self.ledger, wait=0, say=self.say)

    # --- the one thing it does -------------------------------------------

    def run_next(self, slug: str) -> StepOutcome:
        outcome = self._advance(slug)
        run = self.store.load(slug)
        if run.finished:
            self.owner.news(self._how_it_ended(run))
            self.let_go(slug)
        return outcome

    def _how_it_ended(self, run: Run) -> str:
        """What the owner is told, in the one place that already knows a run is over.

        Here rather than in the command, so `run go` and `step run` say the same
        thing — and so a night that ends at 03:00 says so without anybody
        opening a terminal.
        """
        lines = [f"{run.slug} — {run.status.value}"]
        if run.reason:
            lines.append(run.reason)
        where = self._delivered(run)
        if where:
            lines.append(where)
        return "\n".join(lines)

    def _delivered(self, run: Run) -> str:
        for index, step in enumerate(run.steps):
            if step.name != "deliver" or step.status is not StepStatus.PASSED:
                continue
            output = StepWorkspace(self.store.run_root(run.slug), index, step.name).read_output() or {}
            return str(output.get("pull_request") or "")
        return ""

    def let_go(self, slug: str) -> None:
        """Stop holding the run. What the process dies with is reclaimed anyway.

        Addressed the way it was taken — by the run's own project, not by where
        the store happens to stand. The two are the same path today and a
        symlink is all it would take for them not to be.
        """
        where = self._where(self.store.load(slug))
        for lease in self.ledger.runs() + self.ledger.checkouts():
            if lease.slug == slug and lease.project == where:
                self.ledger.release(lease)

    # --- the machine, asked before anything is spent ----------------------

    def _hold(self, run: Run) -> None:
        """One driver per run, one writer per working copy, and the refusals in place.

        Open question 2 was the first of those and the only one enforced. The
        second is what a batch already had and a run started by hand did not: it
        has no worktree, so it builds in the project's own checkout, and a second
        one of those would edit the same files under it.
        """
        where = self._where(run)
        held = self.ledger.hold_run(where, run.slug)
        if not held.granted:
            raise StateError(held.code, held.detail)

        if not run.tree:
            checkout = self.ledger.hold_checkout(where, run.slug)
            if not checkout.granted:
                raise StateError(checkout.code, checkout.detail)

        self._refusals_in_place(run)

    def _refusals_in_place(self, run: Run) -> None:
        """The pre-push hook, put in before a session is let loose in the checkout.

        `agent-kit init` writes it too, and that is not enough on its own:
        `.git/hooks` is not repository content, so a project whose declaration is
        committed and cloned arrives without one. A worktree shares the hook of
        the repository it belongs to, so this covers a batch's children as well.

        A hook the project owns is written to the log and not said out loud: it
        is the same sentence at every step of every run, and the person who can
        act on it is the one who typed `agent-kit init`, which prints it.
        """
        where = self._where(run)
        hook = write_pre_push(where, trunk=self._trunk(where))
        if hook.said():
            log.info("%s: %s", run.slug, hook.said())

    def _trunk(self, where: str) -> str:
        """What this project calls its trunk, and `main` where it will not say.

        A declaration the kit cannot read is refused by the step that needs it,
        with the field named. Refusing it here would stop a run of steps that
        never read the file, and would name the wrong place.
        """
        try:
            project = read_project(where)
        except ConfigError as unreadable:
            log.info("%s could not say what its trunk is: %s", where, unreadable)
            return DEFAULT_BRANCH
        return project.default_branch if project else DEFAULT_BRANCH

    def _can_be_verified_at_all(self, run: Run) -> None:
        """The project's own commands, asked about before the first session.

        `verify` is the only reader of them, so a run without that step is not
        held to them. The question is the cheapest there is — does the first
        word of each name anything this machine can start — and it is asked
        once, before the first step: a project declaring `make test` where
        there is no make used to pass design and build, at a session each, and
        fail at verify, and do it again every night until somebody noticed.
        """
        if run.next_pending() != 0 or not any(step.name == "verify" for step in run.steps):
            return
        try:
            project = read_project(self._where(run))
        except ConfigError as unreadable:
            # The step that needs the declaration refuses it and names the
            # field. Refusing here would name the wrong place.
            log.info("%s could not be read: %s", run.slug, unreadable)
            return
        if project is not None:
            refuse_commands_that_start_nothing(project)

    def _stop_asked(self, run: Run) -> StepOutcome | None:
        """A person's stop, read where the run's own driver can act on it.

        At a step boundary and nowhere else: a session that is running is doing
        work somebody will have to pay for again, and killing it mid-edit is how
        a working copy is left half-written.
        """
        reason = self.ledger.stop_asked(self._where(run), run.slug)
        if reason is None:
            return None
        said = f"stopped-by-request: {reason}"
        self.store.stop(run.slug, said)
        self.say(f"{run.slug}: {said}")
        log.info("%s: %s", run.slug, said)
        return StepOutcome(
            slug=run.slug,
            step=run.steps[run.next_pending() or 0].name,
            passed=False,
            reason=said,
            interrupted=True,
        )

    def _slot(
        self, run: Run, definition: StepDefinition, provider: str, others_left: bool = False
    ) -> Lease | Busy:
        """One live session's worth of machine, waited for if waiting is the best there is."""
        want = Want(
            account=self._account(provider),
            provider=provider,
            project=self._where(run),
            slug=run.slug,
            step=definition.name,
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
                    self.say(f"{run.slug}: waiting — {got.code}: {got.detail}")
                # A run that is stuck is the run somebody is most likely to want
                # stopped, so the stop is read here as well as at the step
                # boundary. Left standing for `_advance` to consume and act on.
                if self.ledger.stop_pending(want.project, run.slug) is not None:
                    return Busy("stopped-by-request", "the run was asked to stop while it waited")
                if time.monotonic() >= deadline:
                    return got
                self.pause(POLL)
                got = self.ledger.take(want, self.ceilings)
        finally:
            self.ledger.gives_up(want)
        return got

    def _breathe(self, run: Run, definition: StepDefinition, attempts: list[AttemptRecord]) -> None:
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
        self.say(f"{run.slug}: backing-off {seconds}s — {definition.name} was refused by the tool")
        log.info("%s: backing-off %ss before %s is tried again", run.slug, seconds, definition.name)
        self.pause(seconds)

    @staticmethod
    def _ask_somebody_else(got: Busy, others_left: bool) -> bool:
        """Waiting hours for a reset while a free account stands by is not waiting, it is idling.

        A full machine binds every provider, so waiting for a slot is right
        whoever is next in the chain. A limit binds one account, and the chain
        exists precisely because another one may be answering.
        """
        return others_left and got.code == "provider-limited"

    def _account(self, provider: str) -> str:
        """The quota pool. Where a machine names none, a provider is its own."""
        return self.accounts.get(provider) or provider

    def _where(self, run: Run) -> str:
        return str(Path(run.project) if run.project else self.store.paths.root.resolve())

    def _advance(self, slug: str) -> StepOutcome:
        run = self.store.load(slug)
        if run.finished:
            raise StateError("run-finished", f"{slug} is {run.status.value}; there is no next step")

        self._can_be_verified_at_all(run)
        self._hold(run)

        stopped = self._stop_asked(run)
        if stopped is not None:
            return stopped

        if run.current is not None:
            # A driver was killed between starting a step and hearing back. The
            # step is nobody's now; it goes back to pending and is tried again.
            left = run.current.name
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
        # Из файла шага, а не с нуля: драйвер мог умереть после того, как
        # владелец ответил, и тогда ответ лежит здесь и обязан быть вложен.
        settled: list[Settled] = _asked_before(workspace)
        refusal: str | None = None
        seen: dict[str, int] = {}
        parts = workspace.read_parts() if definition.splittable else []

        remaining = list(providers)
        while remaining:
            provider = remaining.pop(0)

            lease = None
            if definition.by_agent:
                # The machine is asked before the state moves. A run that cannot
                # have a session has not attempted anything, and its step must
                # look exactly as it did — pending, with the attempts it had.
                others = [name for name in remaining if name != provider]
                got = self._slot(run, definition, provider, others_left=bool(others))
                if not got.granted and got.code == "stopped-by-request":
                    stopped = self._stop_asked(run)
                    if stopped is not None:
                        return stopped
                if not got.granted:
                    outcome.attempts.append(
                        AttemptRecord(
                            attempt=run.steps[index].attempts,
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
                run = self.store.start_step(slug, provider=provider)
                record = self._attempt(
                    run, index, definition, workspace, provider, seen[provider], refusal,
                    enclosures + _parts_enclosure(parts) + _answers_enclosure(settled),
                    prior, len(parts), contract,
                )
            except BaseException as escaped:
                # Whatever broke, the state must not be left holding a step
                # nobody can move. The reason is written down before it is raised.
                self.store.refuse_step(slug, f"{definition.name} on {provider}: {_named(escaped)}")
                raise
            finally:
                # A slot that outlives its session is a slot nobody gets back
                # until the driver dies, and the driver is what is still running.
                self.ledger.release(lease)
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

                # The step named something only the owner can settle. The slot
                # is already given back — a run waiting for a person holds no
                # session — and the run is still held, so a stop can reach it.
                asked = self._ask_the_owner(run, workspace, definition, output, settled)
                if asked is not None:
                    if asked.stopped:
                        stopped = self._stop_asked(self.store.load(slug))
                        if stopped is not None:
                            return stopped
                    settled.extend(asked.settled)
                    if asked.answers:
                        # Somebody answered, so the design on file must be the
                        # design that was built: the step is run again with what
                        # they said enclosed. Not a refusal and not a part.
                        self.store.answered(slug, asked.note)
                        log.info("%s: %s is run again — %s", slug, definition.name, asked.note)
                        remaining, refusal, seen = list(providers), None, {}
                        continue

                if settled:
                    # Здесь, а не внутри ветки выше: обычный случай — на часть
                    # вопросов ответили, и вторая попытка про остальные молчит.
                    # Тогда спрашивать больше нечего, а записать умолчания надо.
                    output = self._fold(output, settled)
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
            elif remaining and record.from_the_tool:
                self._breathe(run, definition, outcome.attempts)

        last = outcome.attempts[-1]
        if last.busy is not None:
            # The last word was the machine's: it is full, or every account this
            # step could use is limited. Nothing failed and nothing was refused
            # by anybody, so the state is left exactly as it was — the step is
            # still pending and the run is still a run — and the exit code says
            # what happened. A busy machine must never be why a run is over.
            raise ProviderError(last.busy.code, last.busy.detail)

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

    def _ask_the_owner(
        self,
        run: Run,
        workspace: StepWorkspace,
        definition: StepDefinition,
        output: dict[str, Any],
        already: list[Settled],
    ) -> "Asked | None":
        """A step named what only the owner can settle. Send it, wait, and settle.

        One round per step, and that is the rule rather than a limit: a second
        round is a conversation, and every handover in this kit is a file. A
        question the second attempt asks again is taken at its default without
        being sent, because the owner has already answered once.
        """
        questions = questions_of(output, run.slug)
        if not questions:
            return None

        rounds = int(workspace.read_asks().get("rounds") or 0)
        # Улаженное — это всё, чем вопрос уже кончился, а не только отвеченное.
        # Иначе взятое умолчание первого круга во втором улаживается заново, и
        # в свёртку не попадает ни разу.
        done = {one.question.id for one in already}
        fresh = [asked for asked in questions if asked.id not in done]
        if not fresh:
            return Asked(settled=[], answers=False, stopped=False, note="")

        if rounds:
            # У владельца уже был круг. Новый вопрос берётся по умолчанию и
            # записывается — но своим кодом: его никому не отправляли.
            settled = [Settled(question=asked, how=HAD_ROUND) for asked in fresh]
            self._write_asks(workspace, rounds, already + settled)
            return Asked(settled=settled, answers=False, stopped=False, note="")

        where = self._where(run)
        self.store.ask_step(run.slug, f"{definition.name} is asking the owner {_about(len(fresh))}")
        settled = self.owner.ask(
            where, run.slug, definition.name, fresh,
            stop=lambda: self.ledger.stop_pending(where, run.slug) is not None,
        )
        stopped = self.ledger.stop_pending(where, run.slug) is not None
        # Круг, который оборвал человек, — не потраченный круг: он и остановил
        # ночь затем, чтобы ответить. Ответы, успевшие прийти, при этом стоят.
        self._write_asks(workspace, rounds if stopped else rounds + 1, already + settled)

        answers = [one for one in settled if one.how == ANSWERED]
        note = (
            f"{definition.name}: the owner answered {_about(len(answers))}"
            if answers
            else f"{definition.name}: nobody answered, and the defaults were taken"
        )
        return Asked(settled=settled, answers=bool(answers), stopped=stopped, note=note)

    @staticmethod
    def _write_asks(workspace: StepWorkspace, rounds: int, settled: list[Settled]) -> None:
        """Весь вопрос целиком, а не его тень.

        `at` и `block` здесь потому, что из этого файла потом собирается
        допущение для знания владельца, а `when` — потому что заметка обещала
        «что пришло и когда», и «когда» не было.
        """
        workspace.write_asks(
            rounds,
            [
                {
                    "id": one.question.id,
                    "question": one.question.question,
                    "default": one.question.default,
                    "because": one.question.because,
                    "at": one.question.at,
                    "block": one.question.block,
                    "how": one.how,
                    "answer": one.answer,
                    "detail": one.detail,
                    "when": _now(),
                }
                for one in settled
            ],
        )

    @staticmethod
    def _fold(output: dict[str, Any], every: list[Settled]) -> dict[str, Any]:
        """A default nobody answered is an expensive assumption, and nothing more.

        A question the owner *did* answer is neither: it is settled, so it
        leaves the output altogether rather than standing in the pull request
        as something still wanted of them.

        The driver writes into the step's output here, which it does nowhere
        else. What keeps that honest is the file that was already there for
        exactly this: `raw.txt` holds what the model said, unchanged.
        """
        folded = dict(output)
        assumptions = list(folded.get("assumptions") or [])
        # Всё, чем шаг когда-либо кончил спрашивать, а не только последний круг.
        # Ревью: вопрос, взятый по умолчанию в первом круге, во второй не
        # попадал и не записывался никуда — ровно то, ради невозможности чего
        # весь шаг и написан.
        assumptions.extend(as_assumption(one) for one in every if one.how != ANSWERED)
        folded["assumptions"] = assumptions

        answered = {one.question.question for one in every if one.how == ANSWERED}
        folded["asks"] = [
            item
            for item in (folded.get("asks") or [])
            if not (isinstance(item, dict) and str(item.get("question") or "").strip() in answered)
        ]
        return folded

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
            tree=Path(run.tree) if run.tree else None,
            branch=run.branch,
            base=run.base,
            brief=run.brief,
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
                    self._account(provider),
                    failure.until,
                    said_by=f"{run.slug}/{definition.name}",
                )
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
                from_the_tool=True,
            )
        except Exception as crash:
            # An adapter is somebody else's code around somebody else's CLI. A
            # surprise from it is an attempt that did not work, not a run that
            # cannot continue — and the type is written down, so it is fixable.
            return self._refused(
                workspace, attempt, on_provider, provider, f"provider-crashed: {_named(crash)}", {},
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

    def _what_it_needs(self, run: Run) -> list[tuple[str, str]]:
        return _needed_run_enclosures(self.store, run.needs)

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
        enclosed += self._what_it_needs(run)
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


def _needed_run_enclosures(store: RunStore, needs: list[str]) -> list[tuple[str, str]]:
    """What the features this one is built on already designed and built.

    A run that needs another is based on its branch, so that work is in the
    tree — but a session that is not shown it designs it again from the trunk.
    Reading is never an instruction, so it arrives enclosed like everything
    else, and a dependency the store cannot read is left out rather than faked.
    """
    enclosed: list[tuple[str, str]] = []
    for slug in needs:
        try:
            needed = store.load(slug)
        except KitError:
            continue
        for index, step in enumerate(needed.steps):
            # Whatever satisfied a contract: `output.json` is written by
            # `accept` and by nothing else, so its being there is the same fact
            # as the step having passed, read from one place instead of two.
            output = StepWorkspace(store.run_root(slug), index, step.name).read_output()
            if output is not None:
                enclosed.append(
                    (f"{slug}, which this one is built on, {step.name} returned",
                     json.dumps(output, indent=2, ensure_ascii=False))
                )
    return enclosed


def create_run(
    store: RunStore,
    registry: Registry,
    slug: str,
    steps: list[str] | None = None,
    project: str | None = None,
    brief: str | None = None,
    base: str | None = None,
    tree: str | None = None,
    needs: list[str] | None = None,
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
        slug, steps=steps, project=project or str(store.paths.root.resolve()), brief=brief,
        base=base, tree=tree, needs=needs,
    )


def _asked_before(workspace: StepWorkspace) -> list[Settled]:
    """Чем этот шаг уже кончил спрашивать, прочитанное из его собственного файла.

    Драйвер, поднявший шаг заново, обязан знать и ответы, и взятые умолчания:
    без этого ответ владельца, переживший смерть драйвера, выбрасывался, а в
    знание уезжала запись, что ответа не было.
    """
    held = workspace.read_asks()
    read: list[Settled] = []
    for item in held.get("settled") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        read.append(
            Settled(
                question=Question(
                    id=str(item["id"]),
                    question=str(item.get("question") or ""),
                    default=str(item.get("default") or ""),
                    because=str(item.get("because") or ""),
                    at=str(item.get("at") or ""),
                    block=str(item.get("block") or ""),
                ),
                how=str(item.get("how") or ""),
                answer=str(item.get("answer") or ""),
                detail=str(item.get("detail") or ""),
            )
        )
    return read


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _answers_enclosure(settled: list[Settled]) -> list[tuple[str, str]]:
    """What the owner said, enclosed like everything else a step must read.

    A person's words are content and never an instruction: they arrive as a
    quoted enclosure, the same way an earlier step's output does, and nothing
    in them names a file, a command or a step.
    """
    answered = [one for one in settled if one.how == ANSWERED]
    if not answered:
        return []
    body = "\n\n".join(f"{one.question.question}\n{one.answer}" for one in answered)
    return [("the owner answered", body)]


def _about(count: int) -> str:
    return "one thing" if count == 1 else f"{count} things"


def _parts_enclosure(parts: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """What the earlier sessions of this same step produced."""
    return [
        (f"this step already did part {number}", json.dumps(part, indent=2, ensure_ascii=False))
        for number, part in enumerate(parts, start=1)
    ]


def _named(error: BaseException) -> str:
    """A failure anybody can act on names its type as well as its message."""
    return f"{type(error).__name__}: {error}".strip().rstrip(":")
