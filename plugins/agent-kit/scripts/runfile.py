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
from pathlib import Path

RUNS = ".agent-kit/runs"
MANIFEST = ".agent-kit/project.yml"

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


def runs(root: Path):
    """Every run directory in this project, with its state — `(directory, state | None)`.

    The unreadable ones come back too, with `None`, because every caller has something to say about
    them and none of them could say it while the loop dropped them on the floor.
    """
    for path in sorted((Path(root) / RUNS).glob("*/run.json")):
        yield path.parent, read(path)


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


def branch_shape(name: str) -> bool:
    """Whether a name is one this kit makes. A slug written where a branch belongs has no `/`."""
    return bool(re.match(r"^[^/]+/.+", name or ""))
