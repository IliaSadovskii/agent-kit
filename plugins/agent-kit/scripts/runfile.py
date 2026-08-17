#!/usr/bin/env python3
"""What a run is, in one place — for every program of this kit that opens a run file.

`.agent-kit/runs/<slug>/run.json` is the memory of one run, and four programs read it: `check.py`
judges it, `orchestrate.py` drives it, and both hooks decide whether a run is in flight at all.
Each of them used to carry its own copy of what a run is: the terminal steps were declared four
times over, the read-a-file loop was written out five times, and two of those copies answered
differently on the same input.

This module holds only what all four need and nothing else. It imports `json`, `re` and `pathlib`,
because one of its readers is a hook that runs on **every** Bash call in every session, and what a
hook may not do is get slow or fail to load.

**A read that fails returns `None`, never `{}`.** An empty run file and one nothing can parse are
different facts and the caller has to tell them apart — a run whose memory is unreadable is a run
that lost it, and reading that as "no run here" is how the merge guard used to disarm itself in
silence.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

RUNS = ".agent-kit/runs"
MANIFEST = ".agent-kit/project.yml"

# How long a run file may sit untouched and still count as a run in flight. A run that was
# abandoned — the server restarted, the driver was killed, nobody ran `--resume` — never reaches a
# terminal step, and without a limit it speaks for the project for ever: every session would go on
# being told to keep out of a tree nothing is building in. A day is far longer than any gap inside a
# live run, where the driver writes on every event.
STALE_AFTER = 24 * 3600

# The steps after which nothing about a run can be fixed. A driver watches for one of these to know
# a child is finished; a hook reads them to know a run is no longer in flight.
TERMINAL = ("done", "blocked", "skipped")
STEPS = ("queued", "design", "build", "verify", "deliver", "done", "blocked", "skipped",
         # the steps a driver writes on a batch's own file, and an epic's phases on its own
         "building", "closing", "gate", "auditing", "proving")

BRANCH_PREFIXES = ("claude/", "sprint/", "epic/")

# The four things a run file can be. They are not variants of one thing: a feature is built and must
# prove itself, an errand is a command doing a job with no suite of its own, a batch is a queue of
# children, and an epic is a queue of batches. Eight places used to work this out for themselves,
# each from a different signal.
KINDS = ("feature", "errand", "batch", "epic")
COMMAND_PREFIX = "/agent-kit:"
FEATURE_COMMANDS = (f"{COMMAND_PREFIX}ship", f"{COMMAND_PREFIX}fix")
BY_COMMAND = {"ship": "feature", "fix": "feature", "sprint": "batch", "epic": "epic", "mvp": "epic",
              "audit": "errand", "advise": "errand", "blueprint": "errand", "accept": "errand",
              "next": "errand"}


def read(path: Path):
    """A run file as a record, or `None` when nothing here can read it as one."""
    try:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def main_worktree(root: Path) -> Path:
    """The checkout a linked `git worktree` was cut from — or `root`, when it is not one.

    Run files are working state and live in `.agent-kit/runs/`, which every project of this kit
    gitignores. So a session standing in a linked worktree sees the tracked `.agent-kit/` — and no
    runs at all: the guard read that as *nothing is in flight here* and let a night's run merge,
    force-push and push the default branch unguarded, and the stop hook could not find the run it
    was supposed to hold open. Both hooks are armed from the tree the runs are actually in.

    Read from files rather than asked of `git`: this is on the path of a hook that runs on every
    Bash call in every session, and a subprocess there is a cost paid thousands of times a night.
    A linked worktree's `.git` is a *file* naming its administrative directory, and `commondir`
    beside it points back at the main repository.
    """
    root = Path(root)
    marker = root / ".git"
    if not marker.is_file():
        return root
    try:
        text = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return root
    if not text.startswith("gitdir:"):
        return root
    admin = Path(text.split(":", 1)[1].strip())
    if not admin.is_absolute():
        admin = (root / admin).resolve()
    try:
        common = (admin / "commondir").read_text(encoding="utf-8").strip()
    except OSError:
        return root
    git_dir = Path(common) if Path(common).is_absolute() else (admin / common)
    try:
        main = git_dir.resolve().parent
    except OSError:
        return root
    return main if (main / RUNS).is_dir() or (main / ".agent-kit").is_dir() else root


def runs(root: Path):
    """Every run directory in this project, with its state — `(directory, state | None)`.

    The unreadable ones come back too, with `None`, because every caller has something to say about
    them and none of them could say it while the loop dropped them on the floor.
    """
    for path in sorted((main_worktree(Path(root)) / RUNS).glob("*/run.json")):
        yield path.parent, read(path)


def in_flight(root: Path) -> list:
    """The runs happening here now — `(directory, state | None)`, newest write last.

    Two things make a run count, and the second is what gives the signal an end: it never reached a
    terminal step, and something wrote to its file inside `STALE_AFTER`. This is the one fact the
    kit has about *another session is working in this tree*, and four readers ask for it — the two
    hooks, the check that prints it before every command, and the commands that refuse to start
    beside it. It was written out twice before, in the guard and in nothing else.

    **A run file nothing can parse counts as a run in flight.** Unreadable and fresh is not "no run
    here": that reading is what once disarmed the merge guard in silence, and the cost of being
    wrong the other way is a refused command the owner can override by saying so.
    """
    now = time.time()
    out = []
    for directory, state in runs(root):
        try:
            age = now - (directory / "run.json").stat().st_mtime
        except OSError:
            continue
        if age >= STALE_AFTER:
            continue
        if state is None or state.get("step") not in TERMINAL:
            out.append((directory, state))
    return out


def kind(state: dict) -> str:
    """Which of the four this run is, or `"unknown"` when nothing here can tell.

    **`kind` in the file wins**, and it is the only signal that cannot be wrong by accident. The
    rest is inference for files written before the field existed, in the order of how much each
    signal knows:

    - the child's own `prompt`, when it starts with a command of this kit. That is what the driver
      will type, so it decides what the session becomes;
    - otherwise `command`, which the run wrote about itself.

    A prompt that is *prose* rather than a command answers `"unknown"`, because it genuinely is:
    a frame child written before this field existed and a feature whose prompt somebody typed out
    read exactly alike, and `command` says `ship` for both. Sixteen real run files across three live
    projects are in that state.

    That ambiguity was decided silently until now — `errand = bool(prompt)`, so **any** prompt made
    a run an errand, and a feature carrying the very line `templates/run.json` offers as its default
    stopped being asked for its suite, for the tree it was proved on, and for its mutation result.
    Now the file says it cannot tell, and one field settles it for every reader.
    """
    declared = str(state.get("kind") or "").strip()
    if declared:
        return declared if declared in KINDS else "unknown"
    prompt = str(state.get("prompt") or "").strip()
    if prompt:
        first = prompt.split()[0]
        if not first.startswith(COMMAND_PREFIX):
            return "unknown"
        return "feature" if first in FEATURE_COMMANDS else "errand"
    return BY_COMMAND.get(str(state.get("command") or "").strip(), "unknown")


def project_root(start: Path):
    """The project a path is in — the nearest directory above it holding `.agent-kit/`."""
    start = Path(start).resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".agent-kit").is_dir():
            return candidate
    return None


def resume_command(state: dict, directory) -> str:
    """The command that picks this run up where it stopped, or `""` when nothing here can say.

    Asked because the one place that answered it — the ladder in `next` — named two of the three:
    `sprint --resume` for a batch and `ship --run` for a feature, and nothing at all for an epic. A
    run at `auditing` or `proving` is an epic mid-flight, and the recommendation it got was the
    command for a batch. Derived rather than remembered, so the answer cannot go out of date the
    next time a command gains a phase.

    **The run's own `prompt` wins**, because it is literally what the driver types to start this
    session — an audit lens carries its own name in it, which nothing else here knows. Otherwise the
    kind decides. `unknown` answers `""`: a run whose kind cannot be worked out cannot be handed to a
    command on a guess.
    """
    prompt = str(state.get("prompt") or "").strip()
    if prompt.startswith(COMMAND_PREFIX) and len(prompt) <= 200:
        return prompt
    by_kind = {"epic": f"{COMMAND_PREFIX}epic --resume {directory}",
               "batch": f"{COMMAND_PREFIX}sprint --resume {directory}",
               "feature": f"{COMMAND_PREFIX}ship --run {directory}"}
    return by_kind.get(kind(state), "")


def branch_shape(name: str) -> bool:
    """Whether a name is one this kit makes. A slug written where a branch belongs has no `/`."""
    return bool(re.match(r"^[^/]+/.+", name or ""))
