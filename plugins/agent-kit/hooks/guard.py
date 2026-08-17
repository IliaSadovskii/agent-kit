#!/usr/bin/env python3
"""Refuse the irreversible three — and the one expensive habit — while a run of this kit is in flight.

    PreToolUse (Bash) — registered in hooks.json

Every command of the kit is told never to merge a pull request, never to force-push and never to
push to the default branch. That held by instruction alone until 0.48.0, and instruction is exactly
what a long autonomous run loses: two merge accidents happened before this file existed — a feature
merged into its parent branch instead of the default one, so nothing reached it at all.

A hook is the only mechanism an agent cannot talk itself out of, and it costs nothing in context
because it runs outside the model. The design's two conditions for one (docs/design/kit-v1.md) are
met here:

**It is a no-op unless a kit run is actually in progress.** The signal is the kit's own state — a
run file at a step that is not terminal. Not the branch name: the hook that keyed on branch names
treated every conversation held on a feature branch as that feature's pipeline and blocked a live
analysis session (defect P4). With no run in flight this exits without an opinion, so the owner's
own sessions, `blueprint` and `next` are untouched.

**What a prompt can enforce reliably stays a prompt.** These three cannot be: they are one Bash call
away at any moment of a five-hour run, and undoing them means rewriting somebody's history.

The fourth is not irreversible and is here for the other half of the same test: `ship` is told not
to walk the whole product and did it 144 times across 80 feature sessions of two measured runs.
An instruction that competes with a cheap path loses, and this one costs hours rather than tokens.
It binds only inside a session the driver registered as a `ship`, so every place that *should* walk
the product — the scenarios lens, the closing session, an `epic`'s proving phase, the owner's own
terminal — never meets it.

The fifth guards the tree rather than the history: **a session that is not part of the run may not
move the branch of the checkout the run is building in.** The driver starts every child in the
project's own directory, so that one tree is shared with whoever else opens a session there — and
on a measured night a second session took it forty seconds after a feature's session had. Nothing
was lost, and the feature spent twelve minutes rebuilding itself in a worktree it had to invent.
The refusal names the cheap way out, `git worktree add`, which is what makes it a redirection
rather than a wall.

It fails open. A guard that breaks must not stop the work — but it says so rather than going quiet,
because silence would be indistinguishable from consent.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# What a run is comes from one place, for every program that opens a run file — the copies never
# disagreed on the constant, but the questions asked around it did. The module is deliberately tiny
# and imports only the standard library: this hook runs on every Bash call in every session.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    import runfile                                  # noqa: E402 - the path above is what makes it work
except ImportError as exc:                          # a half-installed plugin, and nothing else
    # **Loudly.** This hook is the one mechanism an agent cannot talk its way past, so it may fail
    # open — a broken guard must never stop the work — but it may not fail *quietly*: silence here
    # is indistinguishable from permission. Before the shared module existed this file could not
    # fail to load at all, and the first version of that import made the guard disappear without a
    # word, which is the exact trade this hook is written against.
    print(json.dumps({"systemMessage":
                      f"agent-kit's guard could not load and is not protecting this session: {exc}. "
                      f"Merging, force-pushing and pushing the default branch are unguarded until "
                      f"the plugin is reinstalled."}))
    sys.exit(0)

TERMINAL = set(runfile.TERMINAL)

MERGE = re.compile(r"\bgh\s+pr\s+merge\b")
FORCE = re.compile(r"\bgit\s+push\b[^&|;]*?(?:--force\b|--force-with-lease\b|\s-f\b|\s\+\w)")
PUSH = re.compile(r"\bgit\s+push\b")
# Switching the tree, and only that. `git checkout -- <path>` and `git checkout <ref> -- <path>`
# restore files and move no branch, so the `--` form is let past; `git worktree add`, which is what
# this refusal offers instead, matches neither pattern.
SWITCH = re.compile(r"\bgit\s+(?:checkout|switch)\b(?![^&|;]*?\s--\s)")


def runs_in_flight(root: Path) -> bool:
    """A run of the kit is happening here — the one condition under which this hook has an opinion.

    What counts as in flight is `runfile.in_flight`, which every reader of a run file now asks:
    never terminal, and written to inside a day. The staleness half is what gives the signal an
    end — without it one abandoned run disables merging in this project for good, and the fix is a
    hand editing a file, which is exactly the kind of thing this hook exists to make unnecessary.
    """
    return bool(runfile.in_flight(root))


project_root = runfile.project_root


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=5)
    return done.stdout.strip() if done.returncode == 0 else ""


def default_branch(root: Path) -> str:
    head = git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head:
        return head.rsplit("/", 1)[-1]
    for name in ("main", "master"):
        if git(root, "rev-parse", "--verify", "--quiet", name):
            return name
    return "main"


def my_session() -> str | None:
    """The tmux session this hook is running inside, or None when there is none.

    The same signal the stop hook matches on, and for the same reason: the driver writes a child's
    session name into its run file, so a session nobody registered owns no run of the kit and gets
    no opinion. Here it is what tells a feature's session apart from the audit lens, the closing
    session and the owner's own window — all of which may walk the product and must not be refused.
    """
    if not os.environ.get("TMUX"):
        return None
    try:
        done = subprocess.run(["tmux", "display-message", "-p", "#S"],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() or None


def building_a_feature(root: Path) -> bool:
    """This session is a `ship` mid-flight — the one place walking the whole product is refused."""
    session = my_session()
    if not session:
        return False
    for _directory, state in runfile.runs(root):
        if state is None or state.get("session") != session:
            continue
        return runfile.kind(state) == "feature" and state.get("step") not in TERMINAL
    return False


def declared_e2e(root: Path) -> str:
    """`commands.e2e` from the project's own manifest, read without importing the whole check."""
    try:
        text = (root / ".agent-kit" / "project.yml").read_text(encoding="utf-8")
    except OSError:
        return ""
    inside = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            inside = line.strip().rstrip(":") == "commands"
            continue
        if inside and line.strip().startswith("e2e:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return ""


def holds_tree(root: Path) -> bool:
    """This session is standing in the tree a run of somebody else's is building in.

    The driver starts every child in the project's own directory, so one checkout is shared by the
    run and by whoever else opens a session there. Measured on a live night: a `blueprint` session
    switched that tree to another branch forty seconds after a feature's session had switched it to
    its own, and the child spent the next twelve minutes rebuilding itself in a worktree it invented
    on the spot — a rebase, an amend, a reset and a commit removing a symlink that only appeared
    because the tree had moved under it.

    Three conditions, and all three are facts rather than judgements: a run is in flight, this
    session is not one of the sessions the driver registered, and this checkout is the one the runs
    live in. A session already in a worktree of its own answers False and is never refused.

    **A session with no tmux name is not judged.** The registration this matches on is a tmux
    session name, so without one there is nothing to compare and refusing would be a guess. That
    leaves a session started outside tmux unguarded here; what covers it is the line `check.py`
    prints before every command, which is prose and can be argued with, which is the trade.
    """
    session = my_session()
    if not session:
        return False
    flight = runfile.in_flight(root)
    if not flight:
        return False
    if any(state and state.get("session") == session for _directory, state in flight):
        return False
    return Path(root).resolve() == runfile.main_worktree(Path(root)).resolve()


def verdict(command: str, branch: str, default: str,
            e2e: str = "", building: bool = False, held: bool = False) -> str | None:
    """Why this command may not run, or None. Pure, so the tests can reach it."""
    if held and SWITCH.search(command):
        return ("A run of this kit is building in this checkout, and moving its branch pulls the "
                "working tree out from under it. Take a tree of your own instead — "
                "`git worktree add ../<name> <branch>` — and work there. Restoring a file is "
                "untouched: `git checkout -- <path>` moves no branch.")
    # A feature proves itself; the product is proved by whatever integrates a batch. That has been
    # written in `ship`'s Verify step since it existed, and measured over two live runs it lost:
    # `ship` started the end-to-end command 144 times across 80 feature sessions. Cheap in tokens
    # and expensive in hours — which is exactly the shape of rule this kit moves out of prose,
    # because an instruction competing with a cheap path loses every time.
    #
    # Narrow on purpose. It binds only inside a registered `ship`, so the audit's scenarios lens,
    # the closing session, an `epic`'s proving phase and the owner's own terminal are untouched —
    # each of those is where walking the product is the work.
    if e2e and building and e2e.strip() and e2e.strip() in command:
        return (f"`{e2e.strip()}` walks the whole product, and a feature proves only itself — the "
                f"scenarios belong to whatever integrates the batch, which runs them once over the "
                f"chain. Run the project's `commands.test` instead, and say in `suite` what you "
                f"could not exercise from here.")
    if MERGE.search(command):
        return ("Merging is the owner's, on every command of this kit — a run that merges its own "
                "pull request has reviewed nothing and asked nobody. Leave it open and say so in "
                "the run file and the report.")
    if FORCE.search(command):
        return ("A force push rewrites history somebody else may already have. Land another commit "
                "instead; if the branch truly has to be rebuilt, that is the owner's call.")
    if PUSH.search(command):
        pushes_default = re.search(rf"\b{re.escape(default)}\b", command) or (
            branch == default and not re.search(r"\bgit\s+push\b[^&|;]*\s\S+\s+\S+", command))
        if pushes_default:
            return (f"`{default}` is the branch every run forks from, and a run pushes to its own "
                    f"branch and opens a pull request instead. If this is bookkeeping that belongs "
                    f"on {default}, it is `blueprint` or `next` that does it, not a build run.")
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0                                   # nothing to judge; say nothing

    try:
        if event.get("tool_name") != "Bash":
            return 0
        command = (event.get("tool_input") or {}).get("command") or ""
        if not command:
            return 0

        root = project_root(Path(event.get("cwd") or os.getcwd()))
        if root is None or not runs_in_flight(root):
            return 0

        building = building_a_feature(root)
        why = verdict(command, git(root, "rev-parse", "--abbrev-ref", "HEAD"), default_branch(root),
                      declared_e2e(root) if building else "", building, holds_tree(root))
        if not why:
            return 0

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": why,
            },
            "systemMessage": f"agent-kit refused this: {why}",
        }))
    except Exception as exc:                        # noqa: BLE001 - a broken guard must not stop work
        print(json.dumps({"systemMessage":
                          f"agent-kit's guard could not judge this command and allowed it: {exc}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
