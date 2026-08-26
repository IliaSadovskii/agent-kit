"""The `pre-push` hook the plan promised, written into the project's repository.

Section 4 of the plan replaces the second version's `PreToolUse` hook with a git
one: *refuse merge, force-push, push to the default branch — catches the agent
and the human, works with no agent at all*. Until now the promise was the only
trace of it: sessions run with permissions bypassed, and nothing between a
session and the trunk.

Two of the three are pushes and this file holds them. The third — `gh pr merge`
— is an API call and no push hook will ever see it; what holds that one is
`method/rules/repository.md`, which every role carries in its input.

**Where it goes.** git is asked, rather than guessed at: `--git-path hooks`
answers with the common directory, which every worktree of the repository
shares, and honours `core.hooksPath` where a project has set one. So one file
written in the project covers every run's tree.

**What it is not.** It is not a wall. `git push --no-verify` walks past it, and
so does anybody who deletes the file. It makes the ordinary command do the safe
thing, and the method says the rest in words.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .logs import get_logger

#: The line that says this file is the kit's. A hook without it belongs to the
#: project and is never touched: overwriting somebody's hook silently is a
#: worse defect than the one this file is here to fix.
MARK = "# written by agent-kit — three refusals, and nothing else"

NAME = "pre-push"

#: git is a local command. One that has said nothing for this long has hung.
TIMEOUT = 30

#: What `write_pre_push` did.
WRITTEN = "written"
LEFT_ALONE = "left-alone"
NO_REPOSITORY = "no-repository"

log = get_logger("hook")

_BODY = """#!/bin/sh
{mark}
#
# Two refusals, both about pushes: nothing goes to this project's trunk, and
# nothing goes anywhere that would drop commits already on the remote. The
# third refusal the plan names — `gh pr merge` — is not a push, and no push
# hook can see it; the kit's method says that one in words to every role.
#
# Each refusal names a code — `push-to-the-trunk`, `force-push` — because that
# is what the kit's own rule asks of a refusal, and it is what a bench judge
# reads instead of a sentence somebody may rewrite.
#
# This file is not a wall: `--no-verify` walks past it. It is here so that the
# ordinary command does the safe thing. `agent-kit init` writes it, and so does
# every run; delete it and both put it back.

trunk='{trunk}'
zero='0000000000000000000000000000000000000000'

while read -r _local_ref local_sha remote_ref remote_sha
do
	if [ "$remote_ref" = "refs/heads/$trunk" ]; then
		echo "agent-kit: refused: push-to-the-trunk — $trunk is this project's trunk; the kit pushes to a branch and opens a pull request" >&2
		exit 1
	fi
	if [ "$remote_sha" = "$zero" ]; then
		continue
	fi
	if ! git merge-base --is-ancestor "$remote_sha" "$local_sha" 2>/dev/null; then
		echo "agent-kit: refused: force-push — $remote_ref holds commits this push would drop" >&2
		exit 1
	fi
done

exit 0
"""


@dataclass(frozen=True)
class Hook:
    """Where the hook is, and what happened to it."""

    what: str
    path: Path | None = None

    def said(self) -> str:
        """What a person needs told. A hook that went in quietly needs nothing."""
        if self.what != LEFT_ALONE:
            return ""
        return (
            f"{self.path} is the project's own {NAME} hook, so it was left alone: "
            "nothing here refuses a push to the trunk or a force push"
        )


def hooks_dir(where: Path | str) -> Path | None:
    """Where git looks for this repository's hooks, asked of git.

    A worktree answers with the same directory as the repository it belongs to,
    which is what makes one file enough for every run.
    """
    printed = _git(Path(where), "rev-parse", "--path-format=absolute", "--git-path", "hooks")
    return Path(printed.strip()) if printed.strip() else None


def write_pre_push(where: Path | str, trunk: str) -> Hook:
    """Put the hook in, unless the project already has one of its own."""
    hooks = hooks_dir(where)
    if hooks is None:
        return Hook(NO_REPOSITORY)

    path = hooks / NAME
    if path.exists() and MARK not in _read(path):
        return Hook(LEFT_ALONE, path)

    hooks.mkdir(parents=True, exist_ok=True)
    # Written again every time, so that a project which renamed its trunk is
    # held on the new name rather than on the one it had at `init`.
    path.write_text(_BODY.format(mark=MARK, trunk=_quoted(trunk)), encoding="utf-8")
    path.chmod(0o755)
    return Hook(WRITTEN, path)


def _quoted(trunk: str) -> str:
    """A branch name inside single quotes in a shell script. git allows `'` in one."""
    return trunk.replace("'", "'\\''")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _git(where: Path, *argv: str) -> str:
    try:
        done = subprocess.run(
            ["git", *argv], cwd=where, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        log.info("git could not say where %s hooks live: %s", where, error)
        return ""
    return done.stdout if done.returncode == 0 else ""
