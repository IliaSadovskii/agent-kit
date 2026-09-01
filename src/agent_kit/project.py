"""What a project declares about itself: `.agent-kit/v3/project.toml`.

Three facts, each with exactly one reader:

- the commands — `verify` runs these and nothing else, waiting `command_timeout`
  seconds for each;
- the default branch — `deliver` opens the pull request against it;
- the role table — the driver prefers it to the machine's, and only for roles
  this project names;
- where its knowledge lives — the driver encloses an index of it for the step
  that must address it, and `record` writes into it.

Nothing about *how* a provider works reaches here, and nothing this machine
chose about itself does either. This file is the project's, it is committed
beside the code, and `agent-kit init` writes it from what the repository
already says rather than from an interview.
"""

from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RoleConfig, roles_from_table
from .knowledge import DEFAULT_DIR as KNOWLEDGE_DIR
from .errors import ConfigError
from .paths import project_paths
from .verification.answers import Answer, answers_from_table
from .verification.answers import render as verification_lines

PROJECT_FILE = "project.toml"

DEFAULT_BRANCH = "main"

#: A project's own suite is minutes. One that has said nothing for this long is
#: not slow, it is stuck, and a night must not wait on it. A project that knows
#: better says so; this is what the kit assumes when it does not.
DEFAULT_COMMAND_TIMEOUT = 3600

_TOP_KEYS = {"project", "commands", "roles", "verification"}
_PROJECT_KEYS = {"default_branch", "command_timeout", "knowledge"}


@dataclass(frozen=True)
class Command:
    """One declared way of asking the project whether it is well."""

    name: str
    command: str


@dataclass(frozen=True)
class Project:
    root: Path
    default_branch: str = DEFAULT_BRANCH
    #: Seconds `verify` waits for one declared command before killing it and
    #: everything it started.
    command_timeout: int = DEFAULT_COMMAND_TIMEOUT
    #: Where this project keeps its knowledge, relative to its root. The
    #: default is where the second version left it, because the owner's answer
    #: of 22 August is that the format — and the place — do not change.
    #:
    #: **Empty is a state, not a path.** It says, in a file a person wrote and
    #: git carries, that this project is not being described — which is the one
    #: way a project may have no description and not be refused for it. Nothing
    #: is inferred from whether a directory happens to be there: that inference
    #: *was* the silence, and a project the kit knew least about was asked
    #: least. Where it is empty, `knowledge_dir` is None and nothing joins it
    #: to a path.
    knowledge: str = KNOWLEDGE_DIR
    commands: tuple[Command, ...] = ()
    #: What this project checks itself for: one answer per kind of verification
    #: the kit knows, and nothing at all for a kind nobody has been asked about
    #: yet. Its readers are the feature's level — what a design owes and what
    #: `verify` walks — the machine question asked before the first session, and
    #: the door. Empty is the ordinary state of every project written by a kit
    #: older than this one.
    verification: tuple[Answer, ...] = ()
    roles: dict[str, RoleConfig] = field(default_factory=dict)
    source: Path | None = None

    def answer_for(self, kind: str) -> Answer | None:
        """What this project said about that kind, or nothing at all."""
        return next((answer for answer in self.verification if answer.kind == kind), None)

    @property
    def declares_knowledge(self) -> bool:
        """Whether this project says it is described at all.

        The declaration, not the directory. A project that says `knowledge = ""`
        has said out loud that nobody is describing it; one that says nothing
        gets the default and is held to it.
        """
        return bool(self.knowledge.strip())

    def knowledge_in(self, where: Path | str) -> Path | None:
        """Where the knowledge stands in a working copy of this project.

        A run builds in a worktree of its own, and the knowledge is repository
        content like the code beside it: the same relative place, in whichever
        checkout the run holds. None where the project declares none — and never
        `Path(where) / ""`, which is the checkout itself and would make every
        file in the repository part of the owner's knowledge.
        """
        return Path(where) / self.knowledge if self.declares_knowledge else None

    @property
    def knowledge_dir(self) -> Path | None:
        return self.knowledge_in(self.root)

    @property
    def keeps_knowledge(self) -> bool:
        """A project that keeps none owes no block, and is not made to invent one.

        The declaration and nothing else. It used to be whether the directory
        happened to be there, and that inference was the silence: a project that
        declared a description and had not written one was quietly held to the
        looser contract — the kit asking least of the project it knew least
        about. A project that declares one and has written nothing is refused
        before its first session, so no run reaches a step under this.
        """
        return self.declares_knowledge


#: Words a declared command can begin with that are not a program to be found:
#: the shell's own, and the ones that open a compound command. `which` finds
#: none of them, and a project whose lint command is `:` declares a real thing.
SHELL_WORDS = frozenset(
    """
    : . source alias bg break builtin cd command continue echo eval exec exit export false fg
    getopts hash jobs kill let local printf pwd read readonly return set shift test time times
    trap true type typeset ulimit umask unalias unset wait
    if then else elif fi for while until do done case esac function select
    """.split()
)

#: A first word the kit cannot read as the name of a program: the shell will
#: expand or interpret it before it looks for one. `MODE=ci make test` is a
#: declaration somebody wrote on purpose, and guessing at it would refuse a
#: project that is perfectly well.
UNREADABLE = tuple("$`(){}[]<>|&;*?\"'=!~\\")


def starts_nothing(command: str) -> str:
    """The first word of a declared command, when nothing here answers to it.

    Empty when it does, and empty when the kit cannot tell — which is the honest
    answer for a line the shell will do something to first. What this does not
    catch is a program that is there and cannot do the job: `make` on a machine
    with no makefile is on PATH, and it is `verify` that finds that out.
    """
    words = command.strip().split()
    first = words[0] if words else ""
    if not first or first in SHELL_WORDS or any(character in first for character in UNREADABLE):
        return ""
    if "/" in first:
        # A path is looked for where it says, not on PATH: that is what writing
        # one means.
        found = Path(first)
        return "" if found.is_file() and os.access(found, os.X_OK) else first
    return "" if shutil.which(first) else first


def commands_that_start_nothing(project: "Project") -> list[Command]:
    """Every command this project declares whose first word this machine cannot start.

    Both lists: what `verify` runs over the project, and what a kind of
    verification is answered with. One question, one code, one moment.
    """
    return [
        command
        for command in (*project.commands, *answered_commands(project))
        if starts_nothing(command.command)
    ]


def answered_commands(project: "Project") -> list[Command]:
    """A kind answered with a command is a command this machine will run.

    It is held to starting for exactly the reason `[commands]` is, and by the
    same code: `verify` runs both, and a run refused at the end for a binary
    that was never there costs the same night either way.
    """
    return [
        Command(f"verification.{answer.kind}", answer.command)
        for answer in project.verification
        if answer.is_a_command
    ]


def refuse_commands_that_start_nothing(project: "Project") -> None:
    """Asked before a session is paid for, and never by running anything.

    The second version refused before spending and this one did not: a project
    declaring `make test` where there is no make passed `init`, passed `design`,
    passed `build`, and failed at `verify` — two sessions gone, and the same
    again the next night.
    """
    lost = commands_that_start_nothing(project)
    if not lost:
        return
    named = "; ".join(f"{command.name} — {starts_nothing(command.command)!r} is not here" for command in lost)
    raise ConfigError(
        "no-such-command",
        f"{project.source or project.root} объявляет команды, которые эта машина не запустит, и "
        f"а `verify` их запускал бы: {named}",
        hint="agent-kit init --force — или поправьте объявление руками",
    )


def project_file(root: Path | str) -> Path:
    return project_paths(Path(root)).kit_dir / PROJECT_FILE


def read_project(root: Path | str) -> Project | None:
    """What the project declared, or nothing at all if it never did."""
    path = project_file(root)
    if not path.is_file():
        return None

    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise ConfigError("unreadable-project", f"{path} — не TOML: {error}") from error
    except OSError as error:
        raise ConfigError("unreadable-project", f"{path} не прочитался: {error}") from error

    _refuse_unknown(document, _TOP_KEYS, "")
    block = _table(document.get("project", {}), "project")
    _refuse_unknown(block, _PROJECT_KEYS, "project.")

    return Project(
        root=Path(root),
        default_branch=_text(block.get("default_branch", DEFAULT_BRANCH), "project.default_branch"),
        command_timeout=_seconds(block.get("command_timeout", DEFAULT_COMMAND_TIMEOUT), "project.command_timeout"),
        knowledge=_inside(block.get("knowledge", KNOWLEDGE_DIR), "project.knowledge"),
        commands=_commands(_table(document.get("commands", {}), "commands")),
        verification=answers_from_table(_table(document.get("verification", {}), "verification")),
        roles=roles_from_table(_table(document.get("roles", {}), "roles")),
        source=path,
    )


def require_project(root: Path | str) -> Project:
    """For the steps that are programs: they cannot run on a guess."""
    project = read_project(root)
    if project is None:
        raise ConfigError(
            "no-project",
            f"{project_file(root)} нет, значит проект не объявил ни команд, ни ветки",
            hint="agent-kit init",
        )
    return project


# --- writing it, from what the repository already says ----------------------


def discover(root: Path) -> tuple[Project, list[str]]:
    """Read the repository, and keep whatever the project already said.

    What is already declared wins: somebody wrote it on purpose, and the point
    of reading the repository is to fill gaps, not to overrule a person. This
    matters because `init --force` is the very fix the kit suggests when a
    project declares no commands, and it used to answer by deleting the rest.
    """
    found = _from_makefile(root) or _from_pyproject(root)
    standing = read_project(root)

    declared = {command.name: command for command in (standing.commands if standing else ())}
    commands = list(declared.values())
    commands += [command for command in found if command.name not in declared]

    missing: list[str] = []
    if not any(command.name == "test" for command in commands):
        missing.append("test — no `test` target in a Makefile and no pytest in pyproject.toml")

    return (
        Project(
            root=root,
            default_branch=standing.default_branch if standing else _default_branch(root),
            command_timeout=standing.command_timeout if standing else DEFAULT_COMMAND_TIMEOUT,
            knowledge=standing.knowledge if standing else KNOWLEDGE_DIR,
            commands=tuple(commands),
            verification=_answered(standing, found),
            roles=dict(standing.roles) if standing else {},
        ),
        missing,
    )


def _answered(standing: "Project | None", found: list[Command]) -> tuple[Answer, ...]:
    """What the project already answered, and the one answer reading it proposes.

    From the *finding*, never from what was already declared: a project whose
    `test` command a person typed by hand has not thereby said that the suite is
    what proves a feature of it. What the repository itself says — a `test`
    target, a pytest section — is a proposal the kit may make, and it is the
    cheapest of the answers the plan measured: an instrument already installed
    and never declared.

    Everything else is left unanswered, and the door names it. A commented hole
    would be prose, and a `why` the kit invented would be the project refusing a
    kind nobody asked a person about.
    """
    already = standing.verification if standing else ()
    if any(answer.kind == "suite" for answer in already):
        return already
    suite = next((command for command in found if command.name == "test"), None)
    if suite is None:
        return already
    return answers_from_table(
        {answer.kind: _as_table(answer) for answer in already} | {"suite": {"command": suite.command}}
    )


def _as_table(answer: Answer) -> dict[str, str]:
    said = {"command": answer.command} if answer.is_a_command else {"why": answer.why, "since": answer.since}
    return {key: value for key, value in said.items() if value}


def render(project: Project) -> str:
    lines = [
        "# What this project is, as the kit reads it. Written by `agent-kit init`",
        "# from what the repository already said; edit it where that was wrong.",
        "",
        "[project]",
        f'default_branch = "{project.default_branch}"',
        "# How long `verify` waits for one command before killing it and its children.",
        f"command_timeout = {project.command_timeout}",
        "# Where this project keeps its knowledge. Empty says out loud that nobody is",
        "# describing this project — and is the only way a run of it is not refused for",
        "# having no description. `agent-kit knowledge tell` is the other way.",
        f'knowledge = "{project.knowledge}"',
        "",
        "[commands]",
        "# What `verify` runs, in this order. One fact, one home.",
    ]
    lines += [f'{command.name} = "{command.command}"' for command in project.commands]
    if not project.commands:
        lines.append("# nothing was found; `verify` refuses a project that cannot say how it is tested")

    lines += verification_lines(project.verification)

    for name, role in sorted(project.roles.items()):
        # Read back by the driver, so it has to survive being written out. It
        # was not, and `init --force` deleted the table every time.
        lines += ["", f"[roles.{name}]", f'provider = "{role.provider}"']
        if role.fallback:
            lines.append("fallback = [" + ", ".join(f'"{spare}"' for spare in role.fallback) + "]")
        for key in ("model", "effort"):
            value = getattr(role, key)
            if value is not None:
                lines.append(f'{key} = "{value}"')
    return "\n".join(lines) + "\n"


def write_project(project: Project, force: bool = False) -> Path:
    path = project_file(project.root)
    if path.exists() and not force:
        raise ConfigError(
            "project-exists",
            f"{path} уже есть, и его могли править руками",
            hint="agent-kit init --force",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    from .state.store import write_whole

    _unhide(path.parent)
    write_whole(path, render(project))
    return path


def _unhide(kit_dir: Path) -> None:
    """S0-S3 wrote the ignore here, where it covers this file too.

    A project set up by an older kit would commit no declaration and nobody
    would see why. The ignore belongs one level down, over `runs/`, and the
    store writes it there; this only clears the older one out of the way.
    """
    stale = kit_dir / ".gitignore"
    if stale.is_file() and stale.read_text(encoding="utf-8", errors="replace").strip().endswith("*"):
        stale.unlink()


#: Targets worth declaring, in the order `verify` should run them.
_TARGETS = ("lint", "test")


def _from_makefile(root: Path) -> list[Command]:
    makefile = next((root / name for name in ("Makefile", "makefile", "GNUmakefile") if (root / name).is_file()), None)
    if makefile is None:
        return []
    try:
        text = makefile.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    targets = {line.split(":", 1)[0].strip() for line in text.splitlines() if ":" in line and not line.startswith(("\t", " ", "#"))}
    return [Command(name, f"make {name}") for name in _TARGETS if name in targets]


def _from_pyproject(root: Path) -> list[Command]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return []
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError):
        return []
    tools = document.get("tool")
    if isinstance(tools, dict) and "pytest" in tools:
        return [Command("test", "pytest")]
    return []


def _default_branch(root: Path) -> str:
    """What this repository calls its trunk, asked of git rather than assumed."""
    import subprocess

    for argv in (
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        ["git", "symbolic-ref", "--short", "HEAD"],
    ):
        found = subprocess.run(argv, cwd=root, capture_output=True, text=True)
        name = found.stdout.strip().removeprefix("origin/")
        if found.returncode == 0 and name:
            return name
    return DEFAULT_BRANCH


def is_repository(root: Path) -> bool:
    import subprocess

    found = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], cwd=root, capture_output=True, text=True
    )
    return found.returncode == 0 and found.stdout.strip() == "true"


# --- field checks, each naming what it refused ------------------------------


def _refuse_unknown(table: dict[str, Any], known: set[str], prefix: str) -> None:
    for key in table:
        if key not in known:
            raise ConfigError("unknown-key", f"{prefix}{key} — не то, что кит читает о проекте")


def _table(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError("bad-value", f"{where} должен быть таблицей")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("bad-value", f"{where} — непустая строка")
    return value.strip()


def _inside(value: Any, where: str) -> str:
    """A directory of this project, and not a way out of it.

    It is a path the kit writes into. An absolute one, or one that climbs, puts
    a block somewhere no run can find again and takes the kit out with an
    unnamed crash on the way.
    """
    if isinstance(value, str) and not value.strip():
        # Said out loud: this project is not being described. The one value that
        # is a state rather than a path, and a person has to type it.
        return ""
    text = _text(value, where)
    if Path(text).is_absolute() or ".." in Path(text).parts:
        raise ConfigError("bad-field: project.knowledge", f"{where} must be a path inside the project, not {text!r}")
    return text


def _seconds(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError("bad-value", f"{where} — целое число секунд больше нуля")
    return value


def _commands(table: dict[str, Any]) -> tuple[Command, ...]:
    return tuple(Command(name, _text(value, f"commands.{name}")) for name, value in table.items())
