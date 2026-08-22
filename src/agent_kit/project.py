"""What a project declares about itself: `.agent-kit/v3/project.toml`.

Three facts, each with exactly one reader:

- the commands — `verify` runs these and nothing else;
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

_TOP_KEYS = {"project", "commands", "roles"}
_PROJECT_KEYS = {"default_branch"}


@dataclass(frozen=True)
class Command:
    """One declared way of asking the project whether it is well."""

    name: str
    command: str


@dataclass(frozen=True)
class Project:
    root: Path
    default_branch: str = DEFAULT_BRANCH
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
    """Read the repository. What cannot be found is named, never invented."""
    missing: list[str] = []
    commands = _from_makefile(root) or _from_pyproject(root)
    if not any(command.name == "test" for command in commands):
        missing.append("test — no `test` target in a Makefile and no pytest in pyproject.toml")
    return (
        Project(root=root, default_branch=_default_branch(root), commands=tuple(commands)),
        missing,
    )


def render(project: Project) -> str:
    lines = [
        "# What this project is, as the kit reads it. Written by `agent-kit init`",
        "# from what the repository already said; edit it where that was wrong.",
        "",
        "[project]",
        f'default_branch = "{project.default_branch}"',
        "",
        "[commands]",
        "# What `verify` runs, in this order. One fact, one home.",
    ]
    lines += [f'{command.name} = "{command.command}"' for command in project.commands]
    if not project.commands:
        lines.append("# nothing was found; `verify` refuses a project that cannot say how it is tested")
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

    write_whole(path, render(project))
    return path


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


def _commands(table: dict[str, Any]) -> tuple[Command, ...]:
    return tuple(Command(name, _text(value, f"commands.{name}")) for name, value in table.items())
