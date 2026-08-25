"""Will these branches merge, asked before the owner finds out in the morning.

The plan says *several branches merged in an order the program decides*. The
order is decided when a tree is made — a feature that needs another is based on
its branch — and the merging itself is the owner's: an integration branch the
kit pushes is a fourth thing to review and the first place the kit would be
writing code nobody wrote.

What is left is the question only something awake at 03:00 can ask: two
independent features that touched one file conflict on GitHub in the morning,
and nothing would have said so. This merges them in a throwaway tree, in the
order the graph gives, and throws the tree away. It pushes nothing, opens
nothing, and changes no branch.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..logs import get_logger
from ..shell import kill_group

#: git in a scratch tree. One that has said nothing for this long has hung.
TIMEOUT = 300

log = get_logger("batch.merge")


@dataclass(frozen=True)
class Conflict:
    slug: str
    branch: str
    files: list[str] = field(default_factory=list)

    def said(self) -> str:
        where = ", ".join(self.files) if self.files else "no file it would name"
        return f"{self.slug} ({self.branch}) — {where}"


def check_merges(project: Path | str, base: str, landed: list[tuple[str, str]]) -> list[Conflict]:
    """Merge each branch into a scratch copy of the base, in order, and report.

    Nothing is pushed and no branch of the project is touched: the merges happen
    on a detached HEAD in a worktree that is deleted before this returns. A
    branch git does not have is left out rather than reported as a conflict — a
    feature that never delivered has nothing to merge.
    """
    project = Path(project)
    here = [(slug, branch) for slug, branch in landed if _has(project, branch)]
    if len(here) < 2 or not _has(project, base):
        # One branch always merges into its own base, and that is what
        # delivering it already did.
        return []

    where = project / ".agent-kit/v3/trees/.merge-check"
    _git(project, "worktree", "remove", "--force", str(where), allowed_to_fail=True)
    shutil.rmtree(where, ignore_errors=True)
    _git(project, "worktree", "add", "--detach", str(where), base, allowed_to_fail=True)
    if not where.is_dir():
        log.info("the merge check could not make a tree; nothing is claimed about these branches")
        return []

    found: list[Conflict] = []
    try:
        for slug, branch in here:
            merged = _git(where, "merge", "--no-edit", branch, allowed_to_fail=True, want_status=True)
            if merged.returncode == 0:
                continue
            found.append(Conflict(slug=slug, branch=branch, files=_unmerged(where)))
            _git(where, "merge", "--abort", allowed_to_fail=True)
    finally:
        _git(project, "worktree", "remove", "--force", str(where), allowed_to_fail=True)
        shutil.rmtree(where, ignore_errors=True)
        _git(project, "worktree", "prune", allowed_to_fail=True)
    return found


def _unmerged(where: Path) -> list[str]:
    printed = _git(where, "diff", "--name-only", "--diff-filter=U", allowed_to_fail=True)
    return [line.strip() for line in printed.splitlines() if line.strip()]


def _has(project: Path, branch: str) -> bool:
    return bool(
        _git(project, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", allowed_to_fail=True).strip()
    )


def _git(cwd: Path, *argv: str, allowed_to_fail: bool = False, want_status: bool = False):
    """One command, and everything it started dies with it."""
    try:
        child = subprocess.Popen(
            ["git", *argv], cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", start_new_session=True,
        )
    except OSError as error:
        log.info("the merge check could not run git: %s", error)
        return subprocess.CompletedProcess(argv, 1, "", str(error)) if want_status else ""

    try:
        stdout, stderr = child.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        kill_group(child)
        log.info("git %s said nothing for %s seconds", " ".join(argv), TIMEOUT)
        return subprocess.CompletedProcess(argv, 1, "", "timed out") if want_status else ""

    done = subprocess.CompletedProcess(argv, child.returncode, stdout, stderr)
    if want_status:
        return done
    if child.returncode != 0 and not allowed_to_fail:
        log.info("git %s exited with %s", " ".join(argv), child.returncode)
    return stdout
