#!/usr/bin/env python3
"""Refuse the irreversible three, while a run of this kit is in flight.

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

TERMINAL = {"done", "blocked", "skipped"}

MERGE = re.compile(r"\bgh\s+pr\s+merge\b")
FORCE = re.compile(r"\bgit\s+push\b[^&|;]*?(?:--force\b|--force-with-lease\b|\s-f\b|\s\+\w)")
PUSH = re.compile(r"\bgit\s+push\b")


def runs_in_flight(root: Path) -> bool:
    """A run of the kit is happening here — the one condition under which this hook has an opinion."""
    for path in (root / ".agent-kit" / "runs").glob("*/run.json"):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(state, dict) and state.get("step") not in TERMINAL:
            return True
    return False


def project_root(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ".agent-kit").is_dir():
            return candidate
    return None


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


def verdict(command: str, branch: str, default: str) -> str | None:
    """Why this command may not run, or None. Pure, so the tests can reach it."""
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

        why = verdict(command, git(root, "rev-parse", "--abbrev-ref", "HEAD"), default_branch(root))
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
