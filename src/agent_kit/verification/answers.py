"""What a project answered about a kind, and the three ways it did not.

The answer is a command, or a refusal carrying a date and a reason. Never a
bare word:

- **a command**, because it is the only answer a program can test. It is held
  to *starting* — the same question `verify`'s commands are held to — and to
  proving something, which is a second question and the reason this module
  exists rather than one more call to `starts_nothing`.
- **a reason**, because twelve lines of `no` would clear every check here while
  recording that nobody thought about anything.
- **a date**, because *there is no front end* stops being true the week there
  is one.

**Nothing reads `since` except the refusal to accept an answer without it, and
the line the door prints.** No horizon expires anything; `answer-out-of-date`
was designed and then dropped, because a horizon the kit invented would put a
rung on the door that nothing could ever take away. So this is a field whose
only other reader is a printer — the very thing that got `design.verification`
deleted in this same step, and the contradiction is deliberate rather than an
oversight. The difference: that field was the *whole* answer to what would
prove a feature, and this one is a required part of an answer the kit refuses
without. When staleness gets a writer — an answer going stale on evidence, a
manifest whose hash has moved — this is what it reads. Until then the honest
statement is that the date is recorded and nobody acts on it.

The shape of an answer is checked where the file is parsed — `project.py`, the
one TOML reader the rest of the kit already uses. What a *machine* makes of it
is checked here, before the first session of a run that carries `verify`: the
same place and the same moment as `no-such-command`, because it is the same
question asked of a longer list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..errors import ConfigError
from .kinds import CATALOGUE, Kind, kind_named

if TYPE_CHECKING:  # pragma: no cover - for the type checker, not for a run
    from ..project import Project

#: The whole of what a project may say about one kind.
ANSWER_KEYS = {"command", "why", "since"}

#: A date, and only the shape of one. What the kit needs is that a person wrote
#: down *when* they decided; whether that day existed is the calendar's business
#: and `date.fromisoformat` answers it.
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: First words that exit zero whatever the project is in. For `[commands]` these
#: are legitimate — a project whose lint command is `:` declares a real thing,
#: and `SHELL_WORDS` lets them through on purpose since S4. Here they are not:
#: a command against a kind means *this is what proves it*, and a command that
#: cannot fail proves nothing. The plan names this one directly — the second
#: version's own gate was once opened by `yes`.
PROVES_NOTHING = frozenset({"true", ":", "yes", "echo", "printf"})


@dataclass(frozen=True)
class Answer:
    """One kind, and what this project says it does about it."""

    kind: str
    command: str = ""
    why: str = ""
    #: The day the refusal was decided. Empty for a command: a command is
    #: re-answered every time it runs.
    since: str = ""

    @property
    def is_a_command(self) -> bool:
        return bool(self.command)


def answers_from_table(table: dict) -> tuple[Answer, ...]:
    """The `[verification]` table, read and refused where it is not a decision.

    Called by the project's own reader, so every command that reads a project
    refuses the same file for the same reason. A caller that wanted to be
    lenient here would be a second parser.
    """
    from datetime import date

    answers: list[Answer] = []
    for name in table:
        kind = kind_named(name)
        if kind is None:
            raise ConfigError(
                "unknown-kind",
                f"verification.{name} — не тот вид проверки, который знает этот кит: "
                f"{', '.join(one.name for one in CATALOGUE)}",
                hint="agent-kit verification",
            )
        block = table[name]
        if not isinstance(block, dict):
            raise ConfigError("bad-value", f"verification.{name} должен быть таблицей")
        for key in block:
            if key not in ANSWER_KEYS:
                raise ConfigError(
                    "unknown-key", f"verification.{name}.{key} — не то, что кит читает об ответе"
                )

        command = _said(block.get("command"), f"verification.{name}.command")
        why = _said(block.get("why"), f"verification.{name}.why")
        since = _said(block.get("since"), f"verification.{name}.since")

        if bool(command) == bool(why):
            raise ConfigError(
                f"bad-verification-answer: {name}",
                f"verification.{name} must answer with a command or with a reason it cannot apply here, "
                + ("and it names both" if command else "and it names neither"),
                hint="agent-kit verification",
            )
        if why and not since:
            raise ConfigError(
                f"bad-verification-answer: {name}",
                f"verification.{name} отказывается от вида и не говорит, когда это решили; "
                "отказ без даты не отличить от того, на который с тех пор никто не смотрел",
                hint="agent-kit verification",
            )
        if since:
            if not DATE.match(since):
                raise ConfigError(
                    f"bad-verification-answer: {name}",
                    f"verification.{name}.since must be a date as 2026-08-28, not {since!r}",
                )
            try:
                date.fromisoformat(since)
            except ValueError as bad:
                raise ConfigError(
                    f"bad-verification-answer: {name}", f"verification.{name}.since: {bad}"
                ) from bad
        answers.append(Answer(kind=name, command=command, why=why, since=since))

    return tuple(sorted(answers, key=lambda answer: _order(answer.kind)))


def _order(name: str) -> int:
    return next((at for at, kind in enumerate(CATALOGUE) if kind.name == name), len(CATALOGUE))


def _said(value: object, where: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ConfigError("bad-value", f"{where} должен быть строкой")
    return value.strip()


def render(answers: tuple[Answer, ...]) -> list[str]:
    """The table, written back out. What `init` wrote, the kit reads again."""
    if not answers:
        return []
    lines = [
        "",
        "# What this project checks itself for. The kinds are the kit's — see",
        "# `agent-kit verification` — and every one of them is answered with a command",
        "# or with a reason it cannot apply here, carrying the day that was decided.",
    ]
    for answer in answers:
        lines.append(f"\n[verification.{answer.kind}]")
        if answer.is_a_command:
            lines.append(f'command = "{answer.command}"')
        else:
            lines.append(f'why = "{answer.why}"')
            lines.append(f'since = "{answer.since}"')
    return lines


# --- what this project owes, and what it has not said anything about --------


def owed_by_a_feature(project: "Project | None") -> tuple[Kind, ...]:
    """The kinds every feature of this project must decide about.

    A kind answered with a command: the project does this, so a feature says
    which command proves *it*, or why the kind cannot apply to this change.

    A kind the project refused is refused for every feature of it — the whole
    point of the dated refusal is that nobody is asked again — and a kind
    nobody has answered is owed by nobody. A project that has never been asked
    therefore owes nothing, which is what every project written by an older kit
    is, and is why nothing about it changes on the day this ships.
    """
    if project is None:
        return ()
    commanded = {answer.kind for answer in project.verification if answer.is_a_command}
    return tuple(kind for kind in CATALOGUE if kind.name in commanded)


def unanswered(project: "Project | None") -> tuple[Kind, ...]:
    """Every kind this project has said nothing about, in the catalogue's order.

    Reported, never refused. A kind added to the catalogue starts being asked of
    every project here, and a refusal would fail every project in the world on
    the day it is added — including a frozen baseline nobody may move. The door
    prints it; nothing is stopped by it.
    """
    said = {answer.kind for answer in project.verification} if project is not None else set()
    return tuple(kind for kind in CATALOGUE if kind.name not in said)


# --- a command is held to proving something ---------------------------------


def proves_nothing(command: str) -> str:
    """The first word of an answer, when nothing it does could ever fail."""
    words = command.strip().split()
    first = words[0] if words else ""
    return first if first in PROVES_NOTHING else ""


def commands_that_prove_nothing(project: "Project | None") -> list[Answer]:
    if project is None:
        return []
    return [
        answer
        for answer in project.verification
        if answer.is_a_command and proves_nothing(answer.command)
    ]


def refuse_commands_that_prove_nothing(project: "Project | None") -> None:
    """Asked before a session is paid for, like every other question about a command."""
    empty = commands_that_prove_nothing(project)
    if not empty:
        return
    named = "; ".join(
        f"{answer.kind} — {proves_nothing(answer.command)!r} exits zero whatever is wrong"
        for answer in empty
    )
    where = getattr(project, "source", None) or getattr(project, "root", "this project")
    raise ConfigError(
        "command-that-proves-nothing",
        f"{where} отвечает на вид проверки командой, которая не может провалиться: {named}",
        hint="agent-kit verification",
    )
