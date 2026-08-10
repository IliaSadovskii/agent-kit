#!/usr/bin/env python3
"""Refuse to end a turn while this session's own run is mid-step.

    Stop — registered in hooks.json

Ending a turn and finishing a run are separate events, and nothing in the harness ties them
together: a child pushed its branch, took its review, and stopped with `step: "deliver"` still in
its run file — the field the driver judges it by. Thirty minutes later the stall timer noticed and
restarted a session whose context was intact and correct.

The design is in docs/design/stop-hook.md. Its one hard part is whose run this is: blocking on any
run in flight would trap the owner's own session for most of a night, so the driver writes the
child's session name into its run file and this matches on that field alone. A session nobody
registered has no run here and no opinion is offered — which is what leaves `blueprint`, `next` and
every side conversation untouched by construction rather than by a list of exceptions.

It refuses once per turn, it never blocks on a step it could not read, and it fails open out loud.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TERMINAL = {"done", "blocked", "skipped"}


def project_root(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ".agent-kit").is_dir():
            return candidate
    return None


def my_session() -> str | None:
    """The name of the session this hook is running inside, or None when there is none.

    None is the honest answer for a session started by hand: it owns no run of the kit, so the
    hook has nothing to say about it.
    """
    if not os.environ.get("TMUX"):
        return None
    try:
        done = subprocess.run(["tmux", "display-message", "-p", "#S"],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    name = done.stdout.strip()
    return name or None


def my_run(root: Path, session: str) -> tuple[str, str] | None:
    """This session's run and the step it is on — matched on `session`, never on `window`.

    `window` holds the owner's own session so a batch can be narrated to them; matching it would
    block the one session this design exists to keep free.
    """
    for path in sorted((root / ".agent-kit" / "runs").glob("*/run.json")):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(state, dict) or state.get("session") != session:
            continue
        step = state.get("step")
        if isinstance(step, str) and step not in TERMINAL:
            return path.parent.name, step
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0                                   # nothing to judge; say nothing

    try:
        if event.get("stop_hook_active"):
            return 0                               # told once already; the driver owns it from here

        root = project_root(Path(event.get("cwd") or os.getcwd()))
        session = my_session()
        if root is None or session is None:
            return 0

        found = my_run(root, session)
        if not found:
            return 0

        slug, step = found
        print(json.dumps({
            "decision": "block",
            "reason": (f"Your run {slug} is still at step \"{step}\" — a turn that ends is not a run "
                       f"that finished, and the driver judges this run by that field. Finish the "
                       f"step and close the run file, or record a blocker and set step \"blocked\". "
                       f"Then stop."),
        }))
    except Exception as exc:                        # noqa: BLE001 - a broken hook must not stop work
        print(json.dumps({"systemMessage":
                          f"agent-kit's stop hook could not judge this session and allowed it: {exc}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
