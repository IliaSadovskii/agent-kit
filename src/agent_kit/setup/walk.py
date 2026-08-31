"""`agent-kit setup` — the walk a person takes on a machine with nothing on it.

It prints commands and runs none. Installing is the owner's act on the owner's
machine, and a login opens a browser; an installer that reports *done* is the
assertion instead of a trace this whole plan is written against, while a printed
command followed by a re-measurement is a trace.

It spends nothing. The two free rungs are climbed again after the person says
they have run what was printed, and the rungs above them — the ones that cost a
real session — are `agent-kit provider check <name>`, which the walk names and
does not climb. That is the line between the two commands: **setup does not
spend, check does.**

**How many lines it reads from the stream, exactly.** One after the install
command, and only where the provider was not already standing. One after the
login command, and only where the provider declares one. One for the account,
and only where this machine would end up with two providers or more — with one
provider there is one pool, and a question with one answer is not a question.
So a fresh machine reaching Claude Code types two lines. A stream that closes
while a question is standing is `nobody-to-ask`, and nothing is written.
"""

from __future__ import annotations

from typing import Callable

from ..config import ProviderConfig, write_block
from ..errors import ChannelError, ExitCode, ProviderError
from ..logs import get_logger
from ..paths import Paths
from ..providers import registry
from .reading import Reading, Standing, read, render

log = get_logger("setup")

PROGRAM = "agent-kit"
CHECK = "agent-kit provider check"


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

    say("what this machine has")
    for line in render(reading):
        say(line)
    say("")

    one = _which(reading, name)
    say(f"walking {one.name} — {one.title}")
    if one.notes:
        for line in one.notes.splitlines():
            say(f"  {line}")
    say("")

    if not one.ready:
        one = _install(one, ask, say, paths)
    if not one.ready:
        say("")
        say(f"{one.name} is still not here: {one.stopped_on} — {one.detail}")
        raise ProviderError(
            "provider-not-ready",
            f"{one.name} did not reach the rung `{one.stopped_on}` after the walk, "
            "so nothing about it was written down",
        )

    _login(one, ask, say)
    account = _account(reading, one, ask, say)
    _write(paths, reading, one, account, say)
    return int(ExitCode.OK)


# --- who is walked ----------------------------------------------------------


def _which(reading: Reading, name: str | None) -> Standing:
    """The one named, or the one that already works, or the first shipped."""
    if name is not None:
        registry.facts(name)  # `unknown-provider`, and it names what is shipped
        found = reading.named(name)
        if found is None:  # pragma: no cover - both come from the same folder
            raise ProviderError("unknown-provider", f"{name!r} is not in this machine's reading")
        return found
    real = [one for one in reading.providers if one.real]
    if not real:
        # Not `no-provider`: that is the driver's, it means a role has nobody
        # and there is no default, and the answer to it is to configure one.
        # This is the kit carrying no agent at all, and configuring is not an
        # answer to it. A code means one thing.
        raise ProviderError(
            "ships-no-provider", "this kit ships no provider that is an agent"
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


def _install(one: Standing, ask, say, paths: Paths) -> Standing:
    say(f"{one.name} is not standing here: {one.stopped_on} — {one.detail}")
    if not one.install:
        say(f"and {one.name} declares no command that installs it, so this is yours to do.")
        return one

    say("")
    say("run this, in this terminal or another:")
    say(f"    {' '.join(one.install)}")
    if one.installer_missing:
        # Measured, not guessed: the first word of the argv, asked of PATH. It
        # is the whole of what holds a declaration the kit will never run.
        say(f"    ({one.installer_missing!r} is not on this machine either — that comes first)")
    _line(ask, say, "press enter when it has finished: ")

    say("")
    say("looking again…")
    return _again(one.name, paths)


def _login(one: Standing, ask, say) -> None:
    if not one.login:
        return
    say("")
    say("and log it in — it opens a browser, and the kit never sees a key:")
    say(f"    {' '.join(one.login)}")
    _line(ask, say, "press enter when it has finished: ")


def _again(name: str, paths: Paths) -> Standing:
    """The same two rungs, climbed again.

    This is the whole of *nothing is reported installed that was not measured
    afterwards*: an install that ran, exited zero and put nothing on this
    machine leaves the rung exactly where it was, and the walk writes nothing.
    """
    found = read(paths).named(name)
    if found is None:  # pragma: no cover - the name came from the same folder
        raise ProviderError("unknown-provider", f"{name!r} stopped being a provider mid-walk")
    return found


# --- the one thing that cannot be measured ----------------------------------


def _account(reading: Reading, one: Standing, ask, say) -> str | None:
    """Which pool of quota this provider draws on. One subscription is one pool.

    Asked only where there is something to answer. With one provider configured
    there is one pool and its name is the provider's own, which is what the
    ledger already assumes; asking would be a question with one answer.
    """
    others = {name for name in reading.config.providers if name != one.name}
    if not others:
        return None
    say("")
    say("one subscription is one pool of slots, even where two tools reach it.")
    say(f"which pool does {one.name} draw on? {', '.join(sorted(others | {one.name}))}")
    said = _line(ask, say, f"pool [{one.name}]: ").strip()
    return said or None


# --- what is written --------------------------------------------------------


def _write(paths: Paths, reading: Reading, one: Standing, account: str | None, say) -> None:
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

    say("")
    say(f"written → {where}")
    say(f"  [providers.{one.name}] enabled")
    if said_default:
        say(f"  [machine] provider = {said_default!r} — what a role the table does not name falls back to")
    say("")
    # The block is written on the strength of the free rungs alone: the tool is
    # here and it answers. Whether the *account* answers costs a session, so it
    # is named rather than claimed — and without this line the machine where a
    # person is most lost, tool standing and account silent, hears nothing.
    say(f"the account behind it has not been measured. one session says whether it answers:")
    say(f"    {CHECK} {one.name}")
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


def _line(ask: Callable[[str], str], say, prompt: str) -> str:
    """A line from the person standing here, and an empty stream is not a line.

    The same shape S8a settled for a sitting: an answer comes from the terminal
    and from nowhere else, and a closed stream while a question stands means
    nothing is written rather than something invented.
    """
    said = ask(prompt)
    if said == "":
        raise ChannelError(
            "nobody-to-ask",
            "the walk asked something and the stream had closed; nothing has been written",
            hint=f"{PROGRAM} setup, and answer at the terminal",
        )
    return said
