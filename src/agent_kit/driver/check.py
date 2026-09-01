"""Measuring what a provider can actually do.

A level nobody measured is the same class of claim as a rule nobody tested. So
the kit climbs a ladder and says which rung failed:

    binary     the thing is there and can be run
    answers    it answers when asked what it is
    login      the account behind it answers, not just the binary
    one_shot   given a step's input, it returns something
    contract   what it returned satisfies the step's contract
    writes     the session could create a file where it landed
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

from ..errors import ConfigError, KitError
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
RUNGS = ("binary", "answers", "login", "one_shot", "contract", "writes", "observed", "limits")

#: Level A is these; level B is every rung that applies.
#:
#: `writes` is among them and `contract` is not, which looks the wrong way round
#: until the two questions are read apart. A provider that answers in prose has
#: started a session and returned something — that is what level A is, and the
#: step contract is the method's problem rather than the tool's. A provider that
#: cannot create a file cannot do the one thing every step above `probe` exists
#: to do, whatever it says while failing to.
LEVEL_A = ("binary", "answers", "login", "one_shot", "writes")

#: The two that cost nothing: no session, no quota, no account. They are climbed
#: for every shipped provider every time the machine's standing is read, which is
#: why the line is drawn exactly here — a screen that cost quota is a screen
#: nobody can afford to look at. Derived from the ladder rather than listed
#: beside it, so a second list cannot disagree with the first.
FREE = RUNGS[:2]

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
    #: The whole of what a failing session printed. A rung's `detail` carries
    #: the end of it, which is all a night's log has room for; this screen was
    #: typed by somebody who wants to know what went wrong, so it gets more.
    said: str = ""

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
    except ConfigError:
        # Not a rung. A rung is a question about the provider; this is this
        # machine choosing a model or an effort the tool has no flag for, the
        # file to edit is `config.toml`, and exit code 2 says so. Landing it in
        # the `binary` rung said the binary was missing when it was standing
        # there — and exit 4 would have said an agent cannot be run right now.
        raise
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
        rungs["login"].detail = "аккаунт ответил"
        rungs["one_shot"].passed = True
        rungs["one_shot"].detail = f"вернулось знаков: {len(result.raw)}"
    except ExecutorFailed as failure:
        # One session measures both rungs, so a failed session has to be sorted
        # into which of them it failed — and there are three answers, not two.
        #
        # It used to be two. The reason was matched against a list of English
        # words held in this file, and when nothing matched the ladder wrote
        # *the account answered* and moved the failure up to `one_shot`. On the
        # first live climb against a real provider that default reported `ok
        # login` for an account that had returned 401 Unauthorized — the one
        # thing on the screen that was green was the one thing that was broken.
        #
        # The kit's own rule is that a judge reads a code and never a phrase,
        # and a list of somebody else's stderr wordings in the kit's own source
        # is that rule broken by the kit itself. So the words live in the
        # provider's declaration now, the executor turns them into
        # `provider-signed-out`, and what is read here is a code.
        #
        # And the third answer is the point: where nothing says the account is
        # the trouble, the rung is **not asked**. Not passed. A rung that
        # reports `ok` on a guess is worse than no rung, because it is the line
        # somebody stops reading at.
        report.said = failure.said
        reason = f"{failure.code}: {_one_line(failure.detail)}"
        if failure.code == "provider-signed-out":
            rungs["login"].detail = reason
            _fill(rungs["one_shot"], False, "аккаунт не ответил, поэтому работу не давали", False)
        else:
            _fill(
                rungs["login"], False,
                "не спрашивали: сессия не удалась, а из отказа не видно, дело ли в аккаунте",
                False,
            )
            rungs["one_shot"].detail = reason
        return done()

    report.raw = result.raw
    report.facts = result.facts

    probe = builtin_registry().get("probe")
    try:
        answered = parse_output(result.raw)
        probe.contract.check(answered)
        rungs["contract"].passed = True
        rungs["contract"].detail = "ответ удовлетворил контракт шага probe"
        _fill(rungs["writes"], *_writes(answered))
    except ContractRefusal as refused:
        rungs["contract"].detail = f"{refused.code}: {refused.detail}"
        # Not a failure of `writes`: nothing was asked of it. The contract is
        # what guarantees `can_write` is there and is a boolean, so without it
        # there is no answer to read — and a rung nobody climbed is not a rung
        # anybody failed.
        _fill(rungs["writes"], False, "ответ не прочитался, поэтому вопрос не задавали", False)

    if result.facts.observed:
        rungs["observed"].passed = True
        rungs["observed"].detail = (
            f"{result.facts.context_used:,} из {result.facts.context_window:,} токенов"
        )
    else:
        rungs["observed"].detail = "он не говорит, сколько контекста держит сессия"

    _fill(rungs["limits"], *_limits(executor))
    return done()


def free_rungs(name: str, options: dict[str, list[str]] | None = None) -> list[Rung]:
    """Just the two that cost nothing: it is here, and it says what it is.

    The same two functions `check_provider` climbs them with — one
    implementation of each rung, so what `doctor` prints and what `provider
    check` measures cannot drift apart.
    """
    rungs = [Rung(rung) for rung in FREE]
    declared = declared_facts(name)
    if not declared.binary:
        # Not a process, so neither question can be put to it. `fake` is the
        # one shipped today, and a rung nobody can climb is not a rung anybody
        # failed — printing it as failed would say the fixture is broken.
        for rung in rungs:
            _fill(rung, False, "этот провайдер не процесс — искать нечего", False)
        return rungs

    try:
        executor = build_executor(name, options or {})
    except KitError as failure:
        # Broad on purpose, and unlike `check_provider` above: this is what two
        # screens print for every shipped provider, and a screen that raises is
        # a machine that cannot be looked at. Its callers pass no options, so
        # the choice a `ConfigError` would be about cannot be made here.
        rungs[0].detail = f"{failure.code}: {failure.detail}"
        rungs[1].detail = "до неё не дошли"
        return rungs

    _fill(rungs[0], *_binary(executor))
    if not rungs[0].held:
        rungs[1].detail = "до неё не дошли"
        return rungs
    _fill(rungs[1], *_answers(executor))
    return rungs


# --- what to type next ------------------------------------------------------

#: How the walk is named on a screen. The kit prints commands and runs none:
#: installing is the owner's act on the owner's machine, and so is a login.
PROGRAM = "agent-kit"


@dataclass
class Cure:
    """What closes the rung that failed — one line, and the commands to type.

    A diagnosis with no next step is where the owner was left: *споткнулся на
    ступени `one_shot`*, and nothing about what to do with that. The whole
    point of the kit installing providers is that it walks somebody through.

    Nothing here is invented. Every command comes out of the provider's own
    `[provider.setup]`, which is the same table `agent-kit setup` prints from —
    one declaration, two readers, and no second list of commands to disagree
    with the first. A rung that no command closes says so in words rather than
    leaving a dead end, and a provider that declares no install says *that*
    rather than having one guessed for it.
    """

    #: One line of prose at the person reading. Russian, like every other screen.
    said: str = ""
    #: What to type, in the order to type it: a lead line and the argv under it.
    steps: list[tuple[str, list[str]]] = field(default_factory=list)
    #: What this machine has not got, word and reason, measured against PATH —
    #: and only what is missing. The ladder is the other place somebody arrives
    #: at with a tool that does not work, and until this it was the place that
    #: said nothing about requirements at all: `agent-kit setup` printed them
    #: above the install command and `provider check` sent people to the same
    #: command with no idea that it would not help.
    missing: list[tuple[str, str]] = field(default_factory=list)


def cure(report: CheckReport) -> Cure | None:
    """The failed rung, turned into the command that closes it. None if none failed."""
    failed = report.failed
    if failed is None:
        return None

    declared = declared_facts(report.provider)
    walk = ("Или пройдите ход целиком:", [PROGRAM, "setup", report.provider])

    if failed in ("binary", "answers"):
        said = (
            "Инструмент не найден на этой машине."
            if failed == "binary"
            else "Он здесь, но не отвечает — поставьте заново."
        )
        if not declared.install:
            return Cure(f"{said} Команды, которая ставит {declared.title}, кит не знает — "
                        "это придётся сделать самому.", missing=_missing(declared))
        return Cure(said, [("Поставьте его:", declared.install), walk], _missing(declared))

    if failed == "login":
        if not declared.login:
            return Cure(f"Аккаунт не ответил, а команды входа {declared.title} не объявляет: "
                        "вход остаётся делом самого инструмента.")
        return Cure("Аккаунт не ответил: инструмент не залогинен.",
                    [("Войдите:", declared.login), walk])

    if failed == "one_shot":
        # The honest half-answer, and it is deliberately not a diagnosis. The
        # ladder could not tell whether the account is the trouble — that is
        # what the `login` rung above says — so the command is named as the one
        # to run *if it is*, rather than as the cure. A dead end here is what
        # the owner hit; a confident wrong command would be worse.
        said = "Сессия не удалась, а из отказа не видно, дело ли в аккаунте — смотрите выше, что она сказала."
        if not declared.login:
            return Cure(said)
        return Cure(said, [("Если дело в аккаунте, вход у этого инструмента такой:", declared.login), walk])

    if failed == "contract":
        return Cure("Это чинится не командой: инструмент ответил, но не тем, "
                    "чего требует контракт шага `probe`.")
    if failed == "writes":
        return Cure("Это чинится не командой: сессия не смогла создать файл там, где стояла. "
                    "Смотрите флаг, который открывает песочницу, в объявлении этого провайдера.")
    return Cure("Это чинится не командой: инструмент работает, но об этом рассказать не умеет.")


def _missing(declared: Any) -> list[tuple[str, str]]:
    """What the tool needs and this machine has not got, asked once, in one place.

    The same function `agent-kit setup` measures with, imported where it is
    used rather than at the top of the file: the reading imports this module
    for its two free rungs, and one home for a question is worth a lazy import.
    """
    from ..setup.reading import wanted

    return [(want.binary, want.why) for want in wanted(declared) if not want.here]


def _writes(answered: Any) -> tuple[bool, str, bool]:
    """What the probe already went and found out, finally read by somebody.

    The probe's own words: *find out whether you can write to it — create a
    file, delete it again*. The contract has required the answer since S2 and no
    reader ever asked for it, which made `can_write` the one field in this kit
    written for nobody. The rung is that reader.
    """
    if not isinstance(answered, dict):  # pragma: no cover - the contract refused first
        return False, "ответ не прочитался, поэтому вопрос не задавали", False
    if answered.get("can_write") is True:
        return True, "сессия создала файл там, где стояла, и убрала его", True
    return (
        False,
        "сессия не смогла создать файл там, где стояла: песочница или объявление "
        "без флага, который её открывает",
        True,
    )


def _one_line(reason: str) -> str:
    """A rung is one row of a table, so its detail is one line.

    Somebody else's failure arrives with the newlines it was printed with, and
    a rung that pastes a session's banner into the middle of the ladder is a
    ladder nobody can read down. The whole of it is printed under the table, so
    what is kept here is the end — where a CLI puts its reason.

    Trimmed apart from the code, never with it: the code is the one thing on
    this row a judge reads, and a `…vider-signed-out` is a code nothing can
    match. Which is the same rule under a different hat — a judge reads a code,
    so the code has to survive being made to fit.
    """
    from ..providers.process import short

    return short(" ".join(reason.split()), 160)


def _fill(rung: Rung, passed: bool, detail: str, applies: bool = True) -> None:
    rung.passed, rung.detail, rung.applies = passed, detail, applies


def _limits(executor: Any) -> tuple[bool, str, bool]:
    """Can this provider tell a limited account from a working one?

    Measured, not assumed: the declared phrases are run through the adapter's own
    detection, and it has to come back with an hour attached.
    """
    declared = getattr(executor, "declared", None)
    refuse = getattr(executor, "_refuse_if_limited", None)
    if declared is None or refuse is None:
        return False, "про лимиты его не спросить", False
    if not getattr(declared, "reads_limits", False):
        return False, "он не объявляет, по чему узнать исчерпанный аккаунт", True

    sample = f"{declared.limit_says[0]}. Your limit will reset at 5pm (UTC)."
    try:
        refuse(sample)
    except ExecutorFailed as refused:
        if refused.code == "provider-limited" and refused.until:
            return True, f"исчерпанный аккаунт читается, и час сброса тоже ({refused.until})", True
        return False, f"лимит замечен, а час не прочитан: {refused.detail}", True
    return False, "его собственные объявленные фразы не узнаются", True


def _binary(executor: Any) -> tuple[bool, str, bool]:
    binary = getattr(executor, "binary", None)
    if binary is None:
        return False, "этот провайдер не процесс — искать нечего", False
    path = Path(binary)
    if path.is_absolute() or "/" in binary:
        return (True, str(path), True) if path.is_file() else (False, f"{path} — такого файла нет", True)
    from shutil import which

    found = which(binary)
    return (bool(found), found or f"{binary} не найден на PATH", True)


def _answers(executor: Any) -> tuple[bool, str, bool]:
    """Whether it can be asked is the declaration's answer, not the object's.

    Every process executor carries `version()` since S9a, so having the method
    no longer says the question can be put. A provider that declares no flag
    for it is *not asked* — failing the rung would drop a working level-A
    provider below level A over a flag it never claimed.
    """
    version = getattr(executor, "version", None)
    if version is None:
        return False, "его не спросить, что он такое", False
    declared = getattr(executor, "declared", None)
    if declared is not None and not declared.flags.get("version"):
        return False, "он не объявляет флага, которым спрашивают, что он такое", False
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
