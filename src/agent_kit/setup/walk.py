"""`agent-kit setup` — the walk a person takes on a machine with nothing on it.

It prints commands and runs none. Installing is the owner's act on the owner's
machine, and so is a login; an installer that reports *done* is the assertion
instead of a trace this whole plan is written against, while a printed command
followed by a re-measurement is a trace.

And it says *where* to run what it prints. The walk holds this terminal until
somebody tells it they went and did it, so the command belongs in another
window — which the screen did not say, and the owner typed it into the window
that was waiting.

It spends nothing. The two free rungs are climbed again after the person says
they have run what was printed, and the rungs above them — the ones that cost a
real session — are `agent-kit provider check <name>`, which the walk names and
does not climb. That is the line between the two commands: **setup does not
spend, check does.**

**The screen is a numbered list, and the number is derived.** The owner ran this
on a real machine and got the inventory of every shipped provider, four
paragraphs of somebody else's `notes`, and then a bare `press enter` with no way
to tell whether it was the last thing or the first of five. So: one heading that
says how many steps there are, one numbered step at a time, one short line of
what matters *now*, and the command set off on its own line so it can be copied.

The count comes from `_plan`, which is the same list the walk then takes. A
number written down beside it would be a second thing that had to agree — and a
machine whose tool is already standing has two steps, not three. The plan is
settled before the first line is printed, because every question it depends on
is answered by the reading: whether the tool is here, whether the declaration
carries a login, whether this machine would end up with two pools of quota.

**How many lines it reads from the stream, exactly.** One after the install
command, and only where the provider was not already standing. One after the
login command, and only where the provider declares one. One for the account,
and only where this machine would end up with two providers or more — with one
provider there is one pool, and a question with one answer is not a question.
So a fresh machine reaching Claude Code types two lines. A stream that closes
while a question is standing is `nobody-to-ask`, and nothing is written.

**It speaks Russian, and the refusals keep their codes.** What a person reads at
the terminal is the owner's language, the way `knowledge tell` and `batch
compose` already are; what a judge reads is `provider-not-ready`, which is not
a phrase in any language. Rewriting the prose here is safe for exactly that
reason, and a case that goes red over it was measuring a sentence.
"""

from __future__ import annotations

from textwrap import wrap
from typing import Callable

from ..config import ProviderConfig, write_block
from ..errors import ChannelError, ExitCode, ProviderError
from ..logs import get_logger
from ..paths import Paths
from ..providers import registry
from .reading import Reading, Standing, read

log = get_logger("setup")

PROGRAM = "agent-kit"
CHECK = "agent-kit provider check"

#: What each step of the walk is called, where it is on the screen, and nothing
#: else. The order of this table is the order of the walk.
STEPS = {
    "install": "Установить",
    "login": "Войти",
    "pool": "Выбрать пул квоты",
    "write": "Записать выбор",
}

#: Where prose sits, and where a command sits. Two indents and no third: a
#: command has to be selectable by eye as the thing to copy.
BODY = " " * 7
COMMAND = " " * 11
WIDTH = 66

#: Where the command goes, said at every step that prints one.
#:
#: The walk blocks on the line after the command: it is holding this terminal,
#: waiting to be told the person went and did it. The owner read `run this` on
#: a real server, typed it into the window that was holding the prompt, and
#: nothing happened — "у меня ничего не произошло на этом шаге". Where to run
#: it is part of the instruction and not a nicety.
#:
#: Repeated at both steps rather than said once at the top, because the steps
#: are not always both there: on a machine where the tool is already standing
#: the login is step one, and a sentence that leaned on the install step would
#: be missing on exactly the machine the owner was standing at.
ELSEWHERE = "Откройте второй терминал — это окно ждёт вашего Enter — и выполните там:"


def walk(
    name: str | None,
    ask: Callable[[str], str],
    say: Callable[[str], None],
    paths: Paths | None = None,
) -> int:
    """One provider, from nothing to a line in `config.toml`. Returns an exit code."""
    paths = paths or Paths.from_env()
    reading = read(paths)
    if reading.unreadable_config is not None:
        # Before anything is printed at somebody and long before anything is
        # written: the kit does not overwrite a file it could not read. The
        # original failure and not a new one — it names the key, and one thing
        # is named one way.
        raise reading.unreadable_config

    one = _which(reading, name)
    plan = _plan(reading, one)

    say("")
    say(f"  {one.title} — настройка, {_how_many(len(plan))}")
    say("")
    say("")

    if "install" in plan:
        one = _install(one, ask, say, _mark(plan, "install"), paths)
    if not one.ready:
        _gave_up(one, say)
        raise ProviderError(
            "provider-not-ready",
            f"{one.name} не дошёл до ступени `{one.stopped_on}` за весь ход, "
            "so nothing about it was written down",
        )

    if "login" in plan:
        _login(one, ask, say, _mark(plan, "login"))
    account = _pool(reading, one, ask, say, _mark(plan, "pool")) if "pool" in plan else None
    _write(paths, reading, one, account, say, _mark(plan, "write"))
    return int(ExitCode.OK)


# --- how many steps there are -----------------------------------------------


def _plan(reading: Reading, one: Standing) -> list[str]:
    """Every step this walk will take, in the order it will take them.

    Derived, and derived here alone: the heading counts this list and each step
    finds its own place in it, so a walk that skips a step cannot go on saying
    there are three. Everything it asks is already answered by the reading, so
    the whole plan is settled before the first line reaches anybody.
    """
    takes = {
        "install": not one.ready,
        "login": bool(one.login),
        "pool": bool(_pool_mates(reading, one)),
        "write": True,
    }
    return [step for step in STEPS if takes[step]]


def _mark(plan: list[str], step: str) -> str:
    return f"{plan.index(step) + 1}/{len(plan)}"


def _how_many(count: int) -> str:
    """`3 шага`. The kit counts in the owner's language, so it declines the noun."""
    last, hundred = count % 10, count % 100
    if last == 1 and hundred != 11:
        return f"{count} шаг"
    if last in (2, 3, 4) and hundred not in (12, 13, 14):
        return f"{count} шага"
    return f"{count} шагов"


def _pool_mates(reading: Reading, one: Standing) -> set[str]:
    """Every other provider this machine has already configured.

    With none of them there is one pool of quota and its name is this
    provider's own, which is what the ledger already assumes; a question with
    one answer is not a question, and it is not a step either.
    """
    return {name for name in reading.config.providers if name != one.name}


# --- who is walked ----------------------------------------------------------


def _which(reading: Reading, name: str | None) -> Standing:
    """The one named, or the one that already works, or the first shipped."""
    if name is not None:
        registry.facts(name)  # `unknown-provider`, and it names what is shipped
        found = reading.named(name)
        if found is None:  # pragma: no cover - both come from the same folder
            raise ProviderError("unknown-provider", f"{name!r} нет в том, что кит намерил на этой машине")
        return found
    real = [one for one in reading.providers if one.real]
    if not real:
        # Not `no-provider`: that is the driver's, it means a role has nobody
        # and there is no default, and the answer to it is to configure one.
        # This is the kit carrying no agent at all, and configuring is not an
        # answer to it. A code means one thing.
        raise ProviderError(
            "ships-no-provider", "этот кит не везёт ни одного провайдера, который был бы агентом"
        )
    # The one that already works, before the one that needs putting there.
    #
    # It read the other way round until S9, and could not go wrong: with one
    # real provider shipped, *the first that needs the walk* and *the first
    # that works* were the same folder. With four shipped and three of them
    # not installed on any given machine, the old order walked somebody whose
    # agent was standing and configured off to install a tool they never named,
    # picked in alphabetical order. Naming one is still `agent-kit setup <name>`.
    return next((one for one in real if one.ready), None) or real[0]


# --- the two commands -------------------------------------------------------


def _install(one: Standing, ask, say, mark: str, paths: Paths) -> Standing:
    _heading(say, mark, "install")
    if not one.install:
        _prose(say, f"Кит не знает команды, которая ставит {one.title}, — это придётся сделать самому.")
        return one

    _prose(say, _why_it_is_not_here(one))
    _requirements(one, say)
    _prose(say, ELSEWHERE)
    _command(say, one.install)
    _done(ask, say)

    _prose(say, "Смотрим ещё раз…")
    return _again(one.name, paths)


def _requirements(one: Standing, say) -> None:
    """What has to be standing here already — printed **above** the command.

    Above it, and that is the whole of this block. Every requirement the owner
    hit on a real machine arrived as a refusal after the install had run, or,
    worse, as a tool that installed cleanly and then failed at the hour a night
    needed it: `bubblewrap` was learned from a conversation rather than from
    the kit. A line under the command is a line read after it.

    Each carries what was measured about it rather than a blanket *you will
    need these*, because a list nobody checked is a list the person has to go
    and check. The marks are the ones two other screens already use — `ok` and
    `no` — and a case that reads them is reading the kit's own vocabulary
    rather than a sentence somebody may reword.
    """
    if not one.requires:
        return
    _prose(say, "Что должно стоять на этой машине до установки:")
    column = max(len(want.binary) for want in one.requires)
    for want in one.requires:
        say(f"{COMMAND}{'ok' if want.here else 'no'}  {want.binary:{column}}  {want.why}")
    say("")
    if one.missing:
        _prose(
            say,
            "Чего нет — поставьте сначала: без этого команда ниже либо не выполнится, "
            "либо поставит инструмент, который потом не заработает.",
        )


def _why_it_is_not_here(one: Standing) -> str:
    """Not found, or found and silent. Two different mornings for whoever reads it."""
    if one.stopped_on == "binary":
        return "Не найден на этой машине."
    return "Он здесь, но не отвечает — поставьте заново."


def _login(one: Standing, ask, say, mark: str) -> None:
    """The command, where to run it, and what the tool will do — in that order.

    Nothing here says a browser will open. The kit does not know where the
    person is sitting: it was written for a server reached over a private
    network, which has no screen for one to open on, and it installs onto a
    laptop just as well. What the tool actually does belongs to the tool, so
    it is the declaration that says it — and the declaration has to have been
    measured on a machine rather than read out of a reference. `gemini` was
    declared as opening a browser and prints a link into the terminal instead;
    the first live walk is what found that out.
    """
    _heading(say, mark, "login")
    _prose(say, "Ключа кит не видит: вход остаётся делом самого инструмента.")
    _prose(say, ELSEWHERE)
    _command(say, one.login)
    if one.login_note:
        _prose(say, one.login_note)
    _done(ask, say)


def _again(name: str, paths: Paths) -> Standing:
    """The same two rungs, climbed again.

    This is the whole of *nothing is reported installed that was not measured
    afterwards*: an install that ran, exited zero and put nothing on this
    machine leaves the rung exactly where it was, and the walk writes nothing.
    """
    found = read(paths).named(name)
    if found is None:  # pragma: no cover - the name came from the same folder
        raise ProviderError("unknown-provider", f"{name!r} перестал быть провайдером посреди хода")
    return found


def _gave_up(one: Standing, say) -> None:
    """What the person is left with, before the refusal names its code.

    The measured detail is on the screen and not only the rung's name: the
    walk got here because something unexpected happened, and *what was
    measured* is the whole of what the person has to go on.
    """
    say("")
    _prose(say, f"Не вышло: {one.title} так и не прошёл ступень «{one.stopped_on}».")
    if one.detail:
        _prose(say, one.detail)
    _prose(say, "Ничего не записано.")


# --- the one thing that cannot be measured ----------------------------------


def _pool(reading: Reading, one: Standing, ask, say, mark: str) -> str | None:
    """Which pool of quota this provider draws on. One subscription is one pool."""
    _heading(say, mark, "pool")
    _prose(say, "Одна подписка — один пул слотов, даже если к ней ходят два инструмента.")
    _prose(say, "Пулы: " + ", ".join(sorted(_pool_mates(reading, one) | {one.name})))
    # The raw line decides whether anybody is there; what they typed is read
    # after. A bare Enter is an answer — it takes the default — and stripping
    # before the check would read it as a stream that had closed.
    said = _answer(ask, f"{BODY}Чей пул у {one.name}? [{one.name}] ")
    say("")
    return said.strip() or None


# --- what is written --------------------------------------------------------


def _write(
    paths: Paths, reading: Reading, one: Standing, account: str | None, say, mark: str
) -> None:
    """Two blocks at most, and every other byte of the file is left alone.

    The block being written is rebuilt rather than edited line by line: a value
    in this file may be a multi-line string and a comment has no key, so a
    line-wise merge would promise more than it keeps. What that costs is said
    out loud — a comment *inside* the one block being written does not survive.
    Every other block, and everything around them, does.
    """
    chosen = ProviderConfig(
        name=one.name,
        enabled=True,
        model=one.chosen.model if one.chosen else None,
        effort=one.chosen.effort if one.chosen else None,
        # What was asked wins; what stood there before it survives being unasked.
        account=account or (one.chosen.account if one.chosen else None),
        max_sessions=one.chosen.max_sessions if one.chosen else None,
    )
    lines = ["enabled = true"]
    for key in ("model", "effort", "account"):
        value = getattr(chosen, key)
        if value is not None:
            lines.append(f'{key} = "{value}"')
    if chosen.max_sessions is not None:
        lines.append(f"max_sessions = {chosen.max_sessions}")
    where = write_block(paths.config_file, f"[providers.{one.name}]", lines)

    said_default = ""
    if not reading.default:
        write_block(paths.config_file, "[machine]", _machine_block(paths, one.name))
        said_default = one.name

    _heading(say, mark, "write")
    say(f"{BODY}✓ {where}")
    say(f"{COMMAND}[providers.{one.name}]  включён")
    if said_default:
        say(f"{COMMAND}[machine] provider      {said_default}")
        say("")
        _prose(say, "На этот провайдер падает роль, которую таблица не назвала.")
    say("")
    # The block is written on the strength of the free rungs alone: the tool is
    # here and it answers. Whether the *account* answers costs a session, so it
    # is named rather than claimed — and without this line the machine where a
    # person is most lost, tool standing and account silent, hears nothing.
    say("  Готово. Осталось одно — измерить аккаунт, это одна живая сессия:")
    say("")
    # Four spaces under a line that starts at two: this one is not inside a
    # numbered step, so it keeps its own indent rather than borrowing theirs.
    say(f"      {CHECK} {one.name}")
    log.info("%s written into the machine's configuration", one.name)


def _machine_block(paths: Paths, provider: str) -> list[str]:
    """`provider`, beside every key that was already typed there, and nothing else.

    Rebuilding the block from the effective configuration would write `wait` and
    `backoff` as literal numbers on a machine that never chose either — and from
    that day a changed default in the kit could not reach this machine. What was
    typed here stays typed here; what was never typed stays the kit's to decide.

    The file parses: the walk refused before this if it did not.
    """
    import tomllib

    had: dict = {}
    if paths.config_file.exists():
        had = tomllib.loads(paths.config_file.read_text(encoding="utf-8")).get("machine") or {}
    kept = [f"{key} = {_scalar(value)}" for key, value in had.items() if key != "provider"]
    return kept + [f'provider = "{provider}"']


def _scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


# --- the shape of one step --------------------------------------------------


def _heading(say, mark: str, step: str) -> None:
    say(f"  {mark}  {STEPS[step]}")
    say("")


def _prose(say, text: str) -> None:
    for line in wrap(text, width=WIDTH):
        say(BODY + line)
    say("")


def _command(say, argv: list[str]) -> None:
    say(COMMAND + " ".join(argv))
    say("")


def _done(ask, say) -> None:
    """*Сделали? Enter* — the line that says the person went and did it."""
    _answer(ask, f"{BODY}Сделали? Enter ⏎ ")
    say("")


def _answer(ask, prompt: str) -> str:
    """A line from the person standing here, and an empty stream is not a line.

    The same shape S8a settled for a sitting: an answer comes from the terminal
    and from nowhere else, and a closed stream while a question stands means
    nothing is written rather than something invented.
    """
    said = ask(prompt)
    if said == "":
        raise ChannelError(
            "nobody-to-ask",
            "ход о чём-то спросил, а поток был закрыт; ничего не записано",
            hint=f"{PROGRAM} setup — и отвечайте у терминала",
        )
    return said
