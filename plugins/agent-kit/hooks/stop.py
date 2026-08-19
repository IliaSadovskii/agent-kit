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

The same match answers the opposite question. A session whose run is *finished* has nothing left to
do, and one of them has nobody to close it: the session an `epic` hands back to decides what follows
and, when nothing follows, the driver that started it has already exited and no next driver will
ever come. Measured on a live run, it stood for eight hours. So this hook closes it — the one place
that is present at the moment such a session ends a turn.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# What a run is comes from one place, for every program that opens a run file. A hook may not carry
# its own copy: the copies never disagreed on the constant, but they did on the questions asked
# around it, and the one thing worse than four answers is four answers that look like one. The
# module is deliberately tiny — this runs on every Bash call in every session.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    import runfile                                  # noqa: E402 - the path above is what makes it work
except ImportError as exc:                          # a half-installed plugin, and nothing else
    print(json.dumps({"systemMessage":
                      f"agent-kit's stop hook could not load: {exc}. A run may end a turn mid-step "
                      f"without being asked to finish it."}))
    sys.exit(0)

TERMINAL = set(runfile.TERMINAL)
project_root = runfile.project_root


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


def my_runs(root: Path, session: str) -> list:
    """This session's own runs — `(directory, state)`, matched on `session` and never on `window`.

    `window` holds the owner's own session so a batch can be narrated to them; matching it would
    block the one session this design exists to keep free.

    A file nothing can parse is not this session's run — it cannot be shown to be. Failing open is
    this hook's own rule, and it is safe here in a way it is not for the guard: the cost is a turn
    that ends early, not a merge nobody reviewed. That it happened at all is said by `check.py`,
    which names an unreadable run file before every command.

    One pass, because both questions below are asked in every session at the end of every turn and
    a project accumulates run directories for ever — sixty on the project this was measured on.
    """
    return [(directory, state) for directory, state in runfile.runs(root)
            if state is not None and state.get("session") == session]


def unfinished(mine: list) -> tuple[str, str] | None:
    """The run of mine that stopped mid-step, if there is one, as `(slug, step)`."""
    for directory, state in mine:
        # An `epic` is the one run whose session legitimately ends turns while the run is in
        # flight: it decides one batch, hands the building to a driver that outlives it, and says
        # so. Its steps — `gate`, `building`, `auditing`, `proving` — belong to the run, not to the
        # turn, and blocking on them would trap the session in the one place it has no way out of.
        if runfile.kind(state) == "epic":
            continue
        # A handed-over run stops mid-step on purpose: the driver asked for it, the note is written,
        # and the next session carries on from the same file. Refusing here would hold the session
        # open against the one instruction it was given.
        if isinstance(state.get("handoff"), str) and state["handoff"].strip():
            continue
        step = state.get("step")
        if isinstance(step, str) and step not in TERMINAL:
            return directory.name, step
    return None


def finished_epic(mine: list) -> str | None:
    """The slug of this session's own `epic` when it has finished, else None.

    Only an `epic`, because every other session the kit starts already has a closer and they work:
    the driver closes each child it watched, and the driver of the next batch closes the hand-back
    session before it builds anything. This is the one that falls through both — see the comment
    beside `hand_back`.

    **And only a run that is still current.** The name of a hand-back session is derived from the
    run's slug, so it is the same name every time that run is picked up again; without the age
    test, an `epic` finished last month would go on closing any session that ever took its name.
    `STALE_AFTER` is the kit's one answer to *this run file still speaks for the project*.
    """
    for directory, state in mine:
        if runfile.kind(state) != "epic" or state.get("step") not in TERMINAL:
            continue
        try:
            if time.time() - (directory / "run.json").stat().st_mtime >= runfile.STALE_AFTER:
                continue
        except OSError:
            continue
        return directory.name
    return None


def close_myself(session: str) -> str:
    """Close the session this hook is running in. What went wrong, or "" when nothing did.

    `tmux kill-session` alone kills the session and leaves it registered with whatever started it —
    on the machine this was measured on, a watchdog restored the session a minute later and typed
    "Continue from where you left off" into it. So where a helper that knows about the registration
    exists, **it is the whole answer and tmux is not a second opinion**: with no argument it means
    *the session I am in*, and it unregisters and then kills on its own clock. Where there is no
    helper, tmux is the whole answer instead. The two never both run.

    What a zero from the helper proves is exactly this much: it accepted the job. It is not proof
    that the registration is gone — `claude-close` on this machine writes `claude-registry del …
    || true` — and nothing here can check that from outside. Where the helper's own reporting is
    thin, this is thin with it, and that is worth knowing rather than papering over.
    """
    closer = shutil.which("claude-close")
    if closer:
        try:
            done = subprocess.run([closer], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError) as exc:
            return f"{closer} did not finish: {exc}"
        # **The helper's refusal is the answer.** It exits non-zero either because it guards that
        # session — the machine's own control sessions are refused by name — or because it stopped
        # somewhere in the middle, and there is no way from out here to tell which. Killing anyway
        # would override a guard, or kill a session whose registration may still stand, and the
        # second one is the defect this exists to remove.
        if done.returncode != 0:
            said = (done.stderr.strip() or done.stdout.strip()
                    or f"{closer} exited {done.returncode} and said nothing")
            return said
        return ""                                  # it unregisters, then kills, on its own clock
    try:
        done = subprocess.run(["tmux", "kill-session", "-t", session],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"tmux kill-session did not finish: {exc}"
    if done.returncode != 0:
        return done.stderr.strip() or "tmux kill-session refused, and said nothing"
    return ""


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

        mine = my_runs(root, session)
        found = unfinished(mine)
        if not found:
            slug = finished_epic(mine)
            if slug:
                failed = close_myself(session)
                if failed:
                    print(json.dumps({"systemMessage":
                                      f"agent-kit could not close this session after {slug} "
                                      f"finished: {failed}. Close it by hand."}))
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
