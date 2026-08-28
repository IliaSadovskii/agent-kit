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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..config import DEFAULT_WAIT, RoleConfig
from ..errors import ConfigError, KitError, ProviderError, StateError
from ..hook import write_pre_push
from ..knowledge import DEFAULT_DIR as KNOWLEDGE_DIR, Knowledge
from ..logs import get_logger
from ..machine import Busy, Ceilings, Ledger, ledger_path
from ..owner import ANSWERED, HAD_ROUND, NOBODY, Owner, Question, Settled, as_assumption, questions_of
from ..paths import Paths
from ..project import DEFAULT_BRANCH, read_project, refuse_commands_that_start_nothing
from ..verification import owed_by_a_feature, refuse_commands_that_prove_nothing
from ..verification.owed import recount_for
from ..verification.said import what_a_feature_owes
from ..state import DEFAULT_STEPS, Run, RunStore, StepStatus
from ..steps import Registry, StepDefinition
from ..steps.contract import CheckedAgainst
from .executor import Executor
from .session import (
    ATTEMPTS_PER_PROVIDER,
    BACKOFF,
    CONTINUATIONS_ALLOWED,
    AttemptRecord,
    Sessions,
)
from .workspace import StepWorkspace

log = get_logger("driver")


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
        # There is no driver without a ledger. A ceiling that can be left out is
        # a ceiling that is off wherever somebody forgot it, which is the shape
        # of every defect the plan's measurement found.
        # The chain, the slot and the pause are not the driver's own: they are
        # held once, in `session.py`, and a sitting with the owner uses the same
        # ones. What is left here is what only a run has — its state.
        self.sessions = Sessions(
            executors=executors,
            root=store.paths.root,
            ledger=ledger or Ledger(ledger_path(Paths.from_env())),
            roles=roles,
            default_provider=default_provider,
            attempts_per_provider=attempts_per_provider,
            backoff=backoff,
            continuations_allowed=continuations_allowed,
            ceilings=ceilings,
            accounts=accounts,
            wait=wait,
            pause=pause,
            say=say,
        )
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
            # The second question about the same commands: one that starts is
            # not one that can fail, and a kind answered with `true` is a kind
            # nothing checks. `[commands]` is deliberately not held to this.
            refuse_commands_that_prove_nothing(project)

    def _is_described_at_all(self, run: Run) -> None:
        """Missing is not the same as fine, and only one of them can be said out loud.

        Asked once, before the first session, and only of a run that carries the
        step which reads a description — `design`, whose input encloses the
        index of it. The same shape as the question about the project's own
        commands, and for the same reason: a night spent designing against
        nothing is a night nobody gets back.

        Three states, not two. Described: the declared directory holds at least
        one addressable record. Not described, said out loud: `knowledge = ""`,
        which a person typed into a file git carries. And silence — a project
        that never declared anything and never wrote anything — which is what is
        refused here, because it is the one the second version answered zero to.
        """
        if run.next_pending() != 0 or not any(step.name == "design" for step in run.steps):
            return
        where = self._where(run)
        try:
            project = read_project(where)
        except ConfigError as unreadable:
            # The step that needs the declaration refuses it and names the
            # field, exactly as it does for the commands. Refusing here would
            # name the wrong place.
            log.info("%s could not be read: %s", where, unreadable)
            return
        if project is not None and (
            not project.declares_knowledge or Knowledge(project.knowledge_dir).described
        ):
            return
        # One code and three doors. A project that declared nothing at all and a
        # project that declared a description it never wrote are the same state
        # to a run about to be designed — nothing to design against — and giving
        # them two codes would make a caller tell them apart to do the same
        # thing about both.
        said = "declares no description" if project is None else f"{project.knowledge}/ holds no record"
        raise ConfigError(
            "no-description",
            f"this project {said} of what the product is, so there is nothing for a design to be "
            "designed against",
            hint=(
                "write the declaration — `agent-kit init` — then sit down with it — "
                '`agent-kit knowledge tell` — or say out loud that nobody is describing this '
                'project: `knowledge = ""` in .agent-kit/v3/project.toml'
            ),
        )

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

    def _where(self, run: Run) -> str:
        return str(Path(run.project) if run.project else self.store.paths.root.resolve())

    def _advance(self, slug: str) -> StepOutcome:
        run = self.store.load(slug)
        if run.finished:
            raise StateError("run-finished", f"{slug} is {run.status.value}; there is no next step")

        self._can_be_verified_at_all(run)
        self._is_described_at_all(run)
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
        project = self._project_of(run)
        contract = definition.contract_in(
            self.keeps_knowledge(run), bool(owed_by_a_feature(project))
        )
        providers = self.sessions.providers_for(definition)
        workspace = StepWorkspace(self.store.run_root(slug), index, definition.name)
        enclosures, prior = self.enclosures(run, index, definition)
        # What this step's answer is held to beyond its own fields: what the
        # project owes, and what an earlier step measured. Neither fits in a
        # contract the kit ships, so it is bound here, where both are in hand.
        recount = recount_for(definition.name, prior, project)
        if recount is not None:
            contract = CheckedAgainst(fields=contract.fields, recount=recount)

        outcome = StepOutcome(slug=slug, step=definition.name, passed=False)
        # Из файла шага, а не с нуля: драйвер мог умереть после того, как
        # владелец ответил, и тогда ответ лежит здесь и обязан быть вложен.
        settled: list[Settled] = _asked_before(workspace)
        parts = workspace.read_parts() if definition.splittable else []
        stopped_by: StepOutcome | None = None

        # What a start, a refusal and a busy machine mean for a *run*. The chain
        # around them is `session.py`'s and is shared with the sitting; only
        # these four know there is a `run.json` at all.
        def on_start(provider: str):
            nonlocal run
            run = self.store.start_step(slug, provider=provider)
            return run, run.steps[index].attempts

        def on_broke(provider: str, escaped: BaseException) -> None:
            # Whatever broke, the state must not be left holding a step nobody
            # can move. The reason is written down before it is raised.
            self.store.refuse_step(slug, f"{definition.name} on {provider}: {_named(escaped)}")

        def on_refusal(provider: str, reason: str) -> None:
            self.store.refuse_step(slug, f"{definition.name} on {provider}: {reason}")
            log.info("%s: %s refused on %s — %s", slug, definition.name, provider, reason)

        def on_busy(provider: str, got: Busy) -> bool:
            nonlocal stopped_by
            if got.code != "stopped-by-request":
                return False
            stopped_by = self._stop_asked(run)
            return stopped_by is not None

        while True:
            # A part of a split step and an answer from the owner both start the
            # chain over: neither is a refused attempt, so no refusal is carried
            # forward and every provider is in play again.
            walked = self.sessions.turn(
                run,
                definition,
                workspace,
                contract,
                enclosures + _parts_enclosure(parts) + _answers_enclosure(settled),
                prior,
                on_start=on_start,
                on_refusal=on_refusal,
                on_broke=on_broke,
                on_busy=on_busy,
                stop_pending=self.ledger.stop_pending,
                attempt_now=lambda: run.steps[index].attempts,
                parts_done=len(parts),
                providers=providers,
            )
            outcome.attempts.extend(walked.attempts)
            if walked.abandoned:
                return stopped_by if stopped_by is not None else outcome

            record = walked.record
            if record is None:
                break

            output = workspace.read_output() or {}
            if definition.splittable:
                workspace.add_part(output)
                parts.append(output)
            if definition.splittable and output.get("complete") is False:
                room = self._carry_on(slug, definition, parts, outcome)
                if room is None:
                    return outcome
                continue

            if definition.splittable and len(parts) > 1:
                # Several sessions did this step, each answering only for its
                # own part. What the next step reads must be all of it.
                output = contract.merge(parts)
                workspace.accept(record.attempt, output, record.meta)

            # The step named something only the owner can settle. The slot is
            # already given back — a run waiting for a person holds no session —
            # and the run is still held, so a stop can reach it.
            asked = self._ask_the_owner(run, workspace, definition, output, settled)
            if asked is not None:
                if asked.stopped:
                    stopped = self._stop_asked(self.store.load(slug))
                    if stopped is not None:
                        return stopped
                settled.extend(asked.settled)
                if asked.answers:
                    # Somebody answered, so the design on file must be the design
                    # that was built: the step is run again with what they said
                    # enclosed. Not a refusal and not a part.
                    self.store.answered(slug, asked.note)
                    log.info("%s: %s is run again — %s", slug, definition.name, asked.note)
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
            log.info(
                "%s: %s passed on %s (attempt %s)", slug, definition.name, record.provider, record.attempt
            )

            if definition.gate and output.get(definition.gate) is False:
                # The step did its work and what it recorded is that the run must
                # not go on. Nothing was refused and nothing broke, so the run
                # stops rather than fails: `failed` is for a kit that could not do
                # its work, and this one did.
                outcome.reason = (
                    f"gate-closed: {definition.name} passed and recorded {definition.gate} as "
                    "false; the run does not go past that"
                )
                self.store.halt(slug, outcome.reason)
                log.info("%s: %s stopped the run: %s is false", slug, definition.name, definition.gate)
            return outcome

        refusal = outcome.attempts[-1].refusal if outcome.attempts else None
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

    # --- what it is given -------------------------------------------------

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

    def keeps_knowledge(self, run: Run) -> bool:
        project = self._project_of(run)
        return bool(project and project.keeps_knowledge)

    def _knowledge_of(self, run: Run) -> Knowledge:
        project = self._project_of(run)
        root = Path(run.project) if run.project else self.store.paths.root
        # A project that says it is not described has nothing to enclose, and
        # says so — rather than having the kit read a directory it never
        # declared. A run with no declaration at all falls back to the default,
        # which is what a probe against a bare repository is.
        return Knowledge(project.knowledge_dir if project else root / KNOWLEDGE_DIR)

    def _what_it_needs(self, run: Run) -> list[tuple[str, str]]:
        return _needed_run_enclosures(self.store, run.needs)

    def enclosures(
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
        if definition is not None and definition.needs_kinds:
            # Reading is never an instruction, so what the kit knows about a
            # kind arrives here rather than being looked up: a session judging
            # its own excuse against its memory of what `types` means is a
            # session judging nothing.
            said = what_a_feature_owes(
                self._project_of(run), definition.name, prior.get("design"), prior.get("verify")
            )
            if said:
                enclosed.append(("what a feature of this project owes", said))
        return enclosed, prior


#: What the driver used to hold itself and now shares. The names stay where
#: every caller and every test already reaches for them; the values live once,
#: in `Sessions`, so a driver and a sitting cannot drift apart on a ceiling.
SHARED = (
    "executors", "roles", "default_provider", "attempts", "backoff",
    "continuations", "ceilings", "accounts", "wait", "pause", "say", "ledger",
)


def _shared(name: str) -> property:
    return property(
        lambda self: getattr(self.sessions, name),
        lambda self, value: setattr(self.sessions, name, value),
    )


for _name in SHARED:
    setattr(StepRunner, _name, _shared(_name))


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
    frame: list[str] | None = None,
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
        base=base, tree=tree, needs=needs, frame=frame,
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
