"""Taking a case's trap away, and asking it to stop firing.

The bench says which mechanisms fired. It cannot say whether a case is reading
its own trap or the ordinary night the trap was planted in — and a case that
reads the night is green against a broken kit. That has happened three times:
one case in S8 and two in S7a were green until somebody broke the mechanism by
hand. For every other case the claim that it is armed lives in prose in a note.

This is the same question asked mechanically. A case brings exactly three
things on top of the baseline world:

    plant.sh    what it puts in place before the kit runs
    repo/       what it lays over the baseline project
    replies/    what it makes the sessions say

Take all three away and what is left is the baseline world, where nothing is
wrong: the project is the tiny one every case starts from, the sessions answer
that the work is done and the commands are green. A case that still reports
`fired` there is measuring something the world reaches anyway.

`case.toml` is not touched, and that is the line. What a case declares — the
run it asks for, the batch it drives, what it expects — is the question, not
the trap. A case whose trap really is its declaration (a needs graph that
loops; three features to prove three sessions run at once) has nothing that
can be taken away without turning it into a different case, and it says so in
words: `no_disarm` in its own block. That escape hatch is printed on every run
and counted at the end, so it cannot be a quiet place to put a case nobody
wants measured.

Four answers, because the check must never claim more than it measured:

- **armed** — with the trap gone the case stopped firing;
- **still fires** — it did not, so it is not reading what it plants;
- **not disarmable** — the case says in words why nothing can be taken away;
- **could not be checked** — the disarmed run broke, and that is never armed.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..errors import KitError
from .cases import CASE_FILE, Case, read_case
from .runner import run_case

#: What the four answers are called, in the one place they are spelled.
ARMED = "armed"
STILL_FIRES = "still fires"
NOT_DISARMABLE = "not disarmable"
UNCHECKABLE = "could not be checked"

#: What the sessions say when nothing is wrong: a design that names how it will
#: be proved, a build that finishes and writes what it names, and a review that
#: found nothing. The same trio a case that plants nothing in its replies
#: already ships — held here rather than in a directory of its own, because a
#: bench file `.gitignore` can swallow is a bench that is green only here.
NOTHING_WRONG: dict[str, str] = {
    "01-reply.json": json.dumps(
        {
            "title": "Money learns a VAT rate",
            "summary": "Money learns a VAT rate, so a price can be quoted with the tax on it.",
            "changes": ["money.py — a RATE beside the amount"],
            "seams": ["AMOUNT keeps its meaning: the price before tax"],
            "verification": ["the declared command comes back green with RATE in place"],
            "asks": [],
            "closes": [],
            "assumptions": [],
        },
        indent=2,
    )
    + "\n",
    "02-reply.json": json.dumps(
        {
            "complete": True,
            "summary": "The rate, and the check that was decided before it.",
            "files": ["money.py"],
            "tests": ["the declared command"],
            "deviations": [],
            "remaining": None,
        },
        indent=2,
    )
    + "\n",
    "02-reply.sh": "#!/bin/sh\nprintf 'RATE = 20\\n' >> money.py\n",
    "03-reply.json": json.dumps({"verdict": "pass", "findings": []}, indent=2) + "\n",
}


#: What a sitting says when nothing is wrong: the baseline world's one part is
#: accounted for and unchanged, and one part is added from the first line of
#: whatever the case's telling is. It points at a real range, because `said` is
#: required and there is no `derived` for a session to hide behind — and L1 is a
#: range every telling has.
NOTHING_TOLD: dict[str, str] = {
    "01-reply.json": json.dumps(
        {
            "parts": [
                {"key": "money", "verdict": "unchanged"},
                {
                    "verdict": "new",
                    "name": "то, что рассказали",
                    "says": "первая строка рассказа",
                    "said": "L1",
                },
            ],
            "ledger": [],
        },
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
}


@dataclass(frozen=True)
class Armed:
    """What the check found out about one case."""

    name: str
    state: str
    why: str = ""

    @property
    def said(self) -> str:
        return self.state if self.state == ARMED and not self.why else f"{self.state} — {self.why}"


def disarm(case: Case, into: Path) -> Case:
    """The same case with everything it plants taken away.

    A directory, and not a `Case` with fields overridden, because the world is
    made from a directory: a disarmed case has to be laid out exactly as the
    armed one is, or the check measures the difference between two layouts.
    """
    room = into / case.name
    if room.exists():
        shutil.rmtree(room)
    room.mkdir(parents=True)

    shutil.copy2(case.root / CASE_FILE, room / CASE_FILE)
    if case.judge is not None:
        shutil.copy2(case.judge, room / "judge.sh")

    if case.sitting is not None:
        _laid_out(room / "replies", NOTHING_TOLD)
    elif case.batch is None:
        _nothing_wrong(room / "replies")
    else:
        for feature in case.batch.features:
            _nothing_wrong(room / "replies" / feature.slug)

    return read_case(into, case.name)


def _nothing_wrong(folder: Path) -> None:
    _laid_out(folder, NOTHING_WRONG)


def _laid_out(folder: Path, files: dict[str, str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = folder / name
        path.write_text(text, encoding="utf-8")
        if path.suffix == ".sh":
            path.chmod(0o755)


def check_named(root: Path, name: str, into: Path) -> Armed:
    """One case: is it reading its own trap, or the night the trap sits in?"""
    try:
        case = read_case(root, name)
    except KitError as unreadable:
        return Armed(name, UNCHECKABLE, f"{unreadable.code}: {unreadable.detail}")
    return check_case(case, into)


def check_case(case: Case, into: Path) -> Armed:
    if case.no_disarm:
        # Nothing is made and nothing is run: a case that says there is no
        # honest disarm is taken at its word, and the word is printed.
        return Armed(case.name, NOT_DISARMABLE, case.no_disarm)

    try:
        without = disarm(case, into / "disarmed")
    except (KitError, OSError) as broken:
        return Armed(case.name, UNCHECKABLE, f"the trap could not be taken away: {broken}")

    result = run_case(without, into / "worlds")
    if not result.verdict.judged:
        return Armed(case.name, UNCHECKABLE, result.verdict.why)
    if result.verdict.fired:
        return Armed(case.name, STILL_FIRES, "it fires against a world with nothing planted in it")
    return Armed(case.name, ARMED, result.verdict.why)
