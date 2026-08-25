"""A worktree per run: its own HEAD, its own index, its own files.

The plan's words — *a worktree per child, in the core* — and the collision S4
wrote down as the reason S8 exists: `deliver` checks the branch out in the
project itself, so a second run moves HEAD under a session still editing files
for a different feature. `git worktree` gives each run a checkout of the same
repository, sharing one object store, so the situation cannot arise.

A tree belongs to a run and is addressed by its slug. It is made where the
project keeps everything else the kit writes, and it is never taken from
somebody who holds it: a branch checked out elsewhere is a refusal by name.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..errors import StateError
from ..logs import get_logger
from ..paths import project_paths
from ..shell import kill_group
from ..state.store import write_whole

#: Where a project's disposable checkouts live. Beside `runs/`, under the kit's
#: own directory: it is the project's, `git worktree list` prints these
#: relative to the repository they belong to, and deleting the project deletes
#: them. The machine's state directory was the alternative and it is the wrong
#: one — a half-built feature is not something that should die with a reboot.
TREES = "trees"

#: git is a local command. One that has said nothing for this long has hung.
TIMEOUT = 120

log = get_logger("driver.tree")


def trees_dir(project: Path | str) -> Path:
    return project_paths(Path(project)).kit_dir / TREES


def tree_for(project: Path | str, slug: str) -> Path:
    return trees_dir(project) / slug


def make_tree(project: Path | str, slug: str, branch: str, base: str) -> Path:
    """This run's own checkout, made or reclaimed, never taken from anybody.

    Four cases, and each of them happens. There is no tree, so it is ours to
    make — from `base`, which for a feature that needs another is that one's
    branch. There is one and git knows it as ours, which is what a driver that
    died leaves behind, and it is carried on rather than deleted: the files in
    it are the only record of how far that session got. The branch is checked
    out somewhere else, and that is where this stops. Or something is sitting at
    the path that git has never heard of, which is nobody's to delete.
    """
    project = Path(project)
    _refuse_unless_a_repository(project)

    where = tree_for(project, slug)
    # Before the first tree and not after it: a checkout inside a directory git
    # is watching is a repository staging itself.
    _keep_trees_out_of_git(trees_dir(project))

    standing = dict((path, held) for _, path, held in _worktrees(project))
    if where in standing:
        log.info("run %s carries on in the tree a driver left at %s", slug, where)
        return where
    if where.exists():
        raise StateError(
            "tree-in-the-way",
            f"{where} is there and git does not know it as a worktree of {project}",
            hint=f"look at it, then remove it: rm -rf {where}",
        )

    held = [path for path, on in standing.items() if on == branch]
    if held:
        raise StateError(
            "tree-held",
            f"{branch} is checked out in {held[0]}, so this run cannot have it too",
        )

    _git(project, "worktree", "add", *_add_args(project, where, branch, base))
    log.info("run %s builds in %s, off %s", slug, where, base)
    return where


def remove_tree(project: Path | str, slug: str) -> bool:
    """Take the checkout away and leave the branch alone.

    The branch is the work; the tree is a copy of it. Removing a tree of a run
    that landed throws away nothing, and it is not done for one that did not:
    those files are the only evidence of what went wrong.
    """
    project = Path(project)
    where = tree_for(project, slug)
    if not any(path == where for _, path, _ in _worktrees(project)) and not where.exists():
        return False

    _git(project, "worktree", "remove", "--force", str(where), allowed_to_fail=True)
    if where.exists():
        # git refuses a worktree whose administrative data is gone; the
        # directory is still ours to clear, and pruning is what tells git.
        shutil.rmtree(where, ignore_errors=True)
    _git(project, "worktree", "prune", allowed_to_fail=True)
    return True


def trees(project: Path | str) -> list[tuple[str, Path, str]]:
    """Every tree of this project the kit made: its run, its path, its branch."""
    project = Path(project)
    mine = trees_dir(project)
    return [
        (path.name, path, branch)
        for _, path, branch in _worktrees(project)
        if path.parent == mine
    ]


# --- git, and nothing else --------------------------------------------------


def _add_args(project: Path, where: Path, branch: str, base: str) -> list[str]:
    """Make the branch, or check out the one an earlier attempt already made."""
    if _branch_exists(project, branch):
        return [str(where), branch]
    return ["-b", branch, str(where), base]


def _branch_exists(project: Path, branch: str) -> bool:
    return bool(
        _git(
            project, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", allowed_to_fail=True
        ).strip()
    )


def _worktrees(project: Path) -> list[tuple[str, Path, str]]:
    """What git holds, read from its own porcelain rather than from the disk."""
    printed = _git(project, "worktree", "list", "--porcelain", allowed_to_fail=True)
    found: list[tuple[str, Path, str]] = []
    where: Path | None = None
    for line in printed.splitlines():
        if line.startswith("worktree "):
            where = Path(line.removeprefix("worktree ").strip())
        elif line.startswith("branch ") and where is not None:
            found.append((where.name, where, line.removeprefix("branch ").strip().removeprefix("refs/heads/")))
            where = None
        elif not line.strip():
            where = None
    return found


def _refuse_unless_a_repository(project: Path) -> None:
    printed = _git(project, "rev-parse", "--is-inside-work-tree", allowed_to_fail=True).strip()
    if printed != "true":
        raise StateError(
            "not-a-repository",
            f"{project} is not a git repository, and a run builds in a worktree of one",
        )


def _keep_trees_out_of_git(where: Path) -> None:
    """The same rule the run state has: what the kit writes is not the project's."""
    ignore = where / ".gitignore"
    if ignore.exists():
        return
    where.mkdir(parents=True, exist_ok=True)
    write_whole(ignore, "# One checkout per run. Not repository content — the branches are.\n*\n")


def _git(project: Path, *argv: str, allowed_to_fail: bool = False) -> str:
    """One command, and everything it started dies with it."""
    try:
        child = subprocess.Popen(
            ["git", *argv], cwd=project, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            start_new_session=True,
        )
    except OSError as error:
        raise StateError("git-failed", f"git cannot be run: {error}") from error

    try:
        stdout, stderr = child.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        kill_group(child)
        raise StateError("git-failed", f"git {' '.join(argv)} said nothing for {TIMEOUT} seconds") from None

    if child.returncode != 0:
        if allowed_to_fail:
            return ""
        raise StateError(
            "git-failed",
            f"git {' '.join(argv)} exited with {child.returncode}: "
            f"{(stderr or stdout).strip()[:400] or 'and said nothing'}",
        )
    return stdout
