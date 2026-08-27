"""The commit an audit measures, unpacked where nothing can be written back.

An audit is read-only, and the cheap way to say that is a rule in prose: *the
lens changes nothing*. The kit's own measure is the other one — a change that
removes a possibility beats a change that adds a check — so the session never
stands in the working copy at all. It stands in `git archive HEAD`, unpacked
into a directory the kit deletes afterwards.

There is no `.git` in it. So the session cannot commit, cannot open a branch,
cannot push, and cannot touch a file anybody will read again. A worktree was
the obvious alternative and it is the weaker one: a worktree can commit, and
the pre-push hook lets a *new* branch through — which is exactly the branch
nobody can account for later that the plan measured 51 of.

What this costs, and it is said out loud rather than discovered: the audit
measures the last commit. Work that is only in the working copy is not in the
archive, and `export-ignore` in `.gitattributes` takes whole directories out of
it. Both are printed.
"""

from __future__ import annotations

import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..errors import ConfigError
from ..logs import get_logger

#: git is a local command. One that has said nothing for this long has hung.
TIMEOUT = 120

log = get_logger("audit.tree")


@dataclass(frozen=True)
class Unpacked:
    """The commit, where it was put, and what the person should know about it."""

    where: Path
    commit: str
    #: What this repository calls the commit's branch. `HEAD` where it is
    #: detached, which is a true answer and not a missing one.
    branch: str
    #: True when the working copy holds changes the archive does not. Printed,
    #: never refused: the audit says which commit it measured, and a person
    #: mid-work is entitled to audit what is committed.
    dirty: bool
    files: int

    @property
    def short(self) -> str:
        return self.commit[:7]


def unpack_head(root: Path | str, into: Path) -> Unpacked:
    """The last commit of `root`, as files, with no repository around them."""
    root = Path(root)
    commit = _asked(root, "rev-parse", "HEAD")
    if commit is None:
        if _asked(root, "rev-parse", "--is-inside-work-tree") != "true":
            raise ConfigError(
                "not-a-repository",
                f"{root} is not a git repository, and an audit measures a commit",
            )
        raise ConfigError(
            "no-commit",
            f"{root} has no commit yet, so there is nothing to unpack and nothing to measure",
        )

    into.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar", dir=into.parent) as archive:
        done = subprocess.run(
            ["git", "-C", str(root), "archive", "--format=tar", "-o", archive.name, commit],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        if done.returncode != 0:
            raise ConfigError(
                "no-commit",
                f"{root}: git archive would not write {commit[:7]}: "
                f"{(done.stderr or done.stdout).strip()[:400] or 'and said nothing'}",
            )
        with tarfile.open(archive.name) as held:
            members = [one for one in held.getmembers() if one.isfile()]
            _extract(held, into)

    branch = _asked(root, "rev-parse", "--abbrev-ref", "HEAD") or "HEAD"
    dirty = bool(_asked(root, "status", "--porcelain"))
    log.info("%s unpacked at %s: %s files", commit[:7], into, len(members))
    return Unpacked(where=into, commit=commit, branch=branch, dirty=dirty, files=len(members))


def _extract(held: tarfile.TarFile, into: Path) -> None:
    """`data` where the interpreter has it: an archive is somebody else's bytes."""
    try:
        held.extractall(into, filter="data")
    except TypeError:  # pragma: no cover - Python below 3.12
        held.extractall(into)


def _asked(root: Path, *argv: str) -> str | None:
    """What git says, or None where it would not say it."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *argv], capture_output=True, text=True, timeout=TIMEOUT
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None
