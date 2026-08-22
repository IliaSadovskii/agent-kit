"""What a project declares about itself: `.agent-kit/v3/project.toml`.

Three facts, each with exactly one reader:

- the commands — `verify` runs these and nothing else, waiting `command_timeout`
  seconds for each;
- the default branch — `deliver` opens the pull request against it;
- the role table — the driver prefers it to the machine's, and only for roles
  this project names.

Nothing about *how* a provider works reaches here, and nothing this machine
chose about itself does either. This file is the project's, it is committed
beside the code, and `agent-kit init` writes it from what the repository
already says rather than from an interview.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RoleConfig, roles_from_table
from .errors import ConfigError
from .paths import project_paths

PROJECT_FILE = "project.toml"

DEFAULT_BRANCH = "main"

#: A project's own suite is minutes. One that has said nothing for this long is
#: not slow, it is stuck, and a night must not wait on it. A project that knows
#: better says so; this is what the kit assumes when it does not.
DEFAULT_COMMAND_TIMEOUT = 3600

_TOP_KEYS = {"project", "commands", "roles"}
_PROJECT_KEYS = {"default_branch", "command_timeout"}


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
    commands: tuple[Command, ...] = ()
    roles: dict[str, RoleConfig] = field(default_factory=dict)
    source: Path | None = None


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
        raise ConfigError("unreadable-project", f"{path} is not valid TOML: {error}") from error
    except OSError as error:
        raise ConfigError("unreadable-project", f"{path} could not be read: {error}") from error

    _refuse_unknown(document, _TOP_KEYS, "")
    block = _table(document.get("project", {}), "project")
    _refuse_unknown(block, _PROJECT_KEYS, "project.")

    return Project(
        root=Path(root),
        default_branch=_text(block.get("default_branch", DEFAULT_BRANCH), "project.default_branch"),
        command_timeout=_seconds(block.get("command_timeout", DEFAULT_COMMAND_TIMEOUT), "project.command_timeout"),
        commands=_commands(_table(document.get("commands", {}), "commands")),
        roles=roles_from_table(_table(document.get("roles", {}), "roles")),
        source=path,
    )


def require_project(root: Path | str) -> Project:
    """For the steps that are programs: they cannot run on a guess."""
    project = read_project(root)
    if project is None:
        raise ConfigError(
            "no-project",
            f"{project_file(root)} is not there, so this project has declared no commands and no branch",
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
            commands=tuple(commands),
            roles=dict(standing.roles) if standing else {},
        ),
        missing,
    )


def render(project: Project) -> str:
    lines = [
        "# What this project is, as the kit reads it. Written by `agent-kit init`",
        "# from what the repository already said; edit it where that was wrong.",
        "",
        "[project]",
        f'default_branch = "{project.default_branch}"',
        "# How long `verify` waits for one command before killing it and its children.",
        f"command_timeout = {project.command_timeout}",
        "",
        "[commands]",
        "# What `verify` runs, in this order. One fact, one home.",
    ]
    lines += [f'{command.name} = "{command.command}"' for command in project.commands]
    if not project.commands:
        lines.append("# nothing was found; `verify` refuses a project that cannot say how it is tested")

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
            f"{path} exists already and may have been edited by hand",
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
            raise ConfigError("unknown-key", f"{prefix}{key} is not something the kit reads about a project")


def _table(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError("bad-value", f"{where} must be a table")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("bad-value", f"{where} must be a non-empty string")
    return value.strip()


def _seconds(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError("bad-value", f"{where} must be a whole number of seconds above zero")
    return value


def _commands(table: dict[str, Any]) -> tuple[Command, ...]:
    return tuple(Command(name, _text(value, f"commands.{name}")) for name, value in table.items())
