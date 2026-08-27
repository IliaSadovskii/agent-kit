"""What a reading has to be before it is an answer, and what it comes to.

The contract says the shape. This says the two things a shape cannot: that
every part standing in the project got a line — including the ones that did not
move — and that every line points at something the owner actually said.

The first is the whole reason the reading is a field and not a summary. The
cheap way to look thorough is to read a third of what is written down and
report three differences confidently, and a line per part is exactly what a
third of the reading cannot produce. It is checked by counting, not by asking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..knowledge import Part, part_key
from .steps import BADLY, BROKEN, CONTRADICTS, NEW, REFINES, UNCHANGED
from .telling import SittingRefusal, Telling


@dataclass(frozen=True)
class Row:
    """One part, as the reading left it.

    No `said`. The range is what makes the row traceable and it is read exactly
    once, here, where it is resolved against the telling — a row that survives
    this has already been shown to point at something the owner typed. Carrying
    it further would be a field whose only reader is the check that already ran.
    """

    key: str
    verdict: str
    name: str = ""
    says: str = ""
    question: str = ""


@dataclass(frozen=True)
class Entry:
    """One line for the ledger: work that exists and is wrong."""

    what: str
    kind: str


@dataclass
class Reading:
    rows: list[Row] = field(default_factory=list)
    ledger: list[Entry] = field(default_factory=list)

    def counted(self, verdict: str) -> int:
        return sum(1 for row in self.rows if row.verdict == verdict)

    @property
    def contradictions(self) -> list[Row]:
        return [row for row in self.rows if row.verdict == CONTRADICTS]

    def counts(self) -> str:
        """The four numbers, said back. The second is the one nobody can see anywhere else."""
        return " · ".join(
            f"{verdict} {self.counted(verdict)}" for verdict in (NEW, REFINES, CONTRADICTS, UNCHANGED)
        ) + (
            f"   ledger: {BADLY} {sum(1 for one in self.ledger if one.kind == BADLY)}"
            f" · {BROKEN} {sum(1 for one in self.ledger if one.kind == BROKEN)}"
        )


def read(
    output: dict[str, Any],
    telling: Telling,
    standing: list[Part],
    *,
    only: set[str] | None = None,
) -> Reading:
    """The reading, judged and turned into rows — or a refusal that names its part.

    `only` is the settling's set: a second turn answers for the parts the owner
    was asked about and says nothing about the rest, because the program already
    holds the rest and merging is its job rather than a session's.
    """
    held = {part.key: part for part in standing}
    wanted = set(held) if only is None else set(only)

    rows: list[Row] = []
    seen: set[str] = set()
    for index, one in enumerate(output.get("parts") or []):
        row = _row(one, index, telling, held)
        if row.key in seen:
            raise SittingRefusal(
                "part-named-twice",
                f"{row.key} is answered for twice, and one part cannot have two readings",
            )
        seen.add(row.key)
        rows.append(row)

    missing = sorted(wanted - seen)
    if missing:
        raise SittingRefusal(
            "reading-misses-a-part",
            "every part written down needs a line of its own, including the ones this telling "
            f"did not move, and these have none: {', '.join(missing)}",
        )
    if only is not None:
        extra = sorted(seen - wanted)
        if extra:
            raise SittingRefusal(
                "part-nobody-asked-about",
                f"this turn settles what the owner was asked about, and these were not: {', '.join(extra)}",
            )

    return Reading(rows=rows, ledger=[_entry(one, index, telling) for index, one in enumerate(output.get("ledger") or [])])


def _row(one: dict[str, Any], index: int, telling: Telling, held: dict[str, Part]) -> Row:
    verdict = str(one.get("verdict") or "")
    said_key = str(one.get("key") or "").strip()
    name = " ".join(str(one.get("name") or "").split())
    about = f"parts[{index}]"

    if verdict == UNCHANGED:
        # A part that did not move needs its key and nothing else: what it says
        # is already on file, and asking a session to retype it is asking for a
        # rewrite nobody wanted.
        key = _standing(said_key, held, about)
        return Row(key=key, verdict=verdict)

    for what in ("name", "says", "said"):
        if not str(one.get(what) or "").strip():
            raise SittingRefusal(
                "nothing-was-said",
                f"{about} is {verdict} and has no {what}; a part that changes has to say what it now says",
            )

    said = str(one["said"]).strip()
    telling.said(said, about)  # the range resolves, or this is not a record of anything

    if verdict == NEW:
        if said_key and said_key in held:
            raise SittingRefusal(
                "part-already-there",
                f"{about} calls {said_key} new and this product already has it; a part that is "
                "there is refined or contradicted, never added again",
            )
        key = said_key or part_key(name)
        if key in held:
            raise SittingRefusal(
                "part-already-there",
                f"{about} adds a part whose key {key} is already taken by {held[key].name!r}",
            )
        return Row(key=key, verdict=verdict, name=name, says=str(one["says"]).strip())

    key = _standing(said_key, held, about)
    question = " ".join(str(one.get("question") or "").split())
    if verdict == CONTRADICTS and not question:
        raise SittingRefusal(
            "no-question-for-a-contradiction",
            f"{about} contradicts {key} and asks nothing; a contradiction is the one thing this "
            "sitting puts to the owner, and it cannot be put without a question",
        )
    return Row(key=key, verdict=verdict, name=name, says=str(one["says"]).strip(), question=question)


def _standing(key: str, held: dict[str, Part], about: str) -> str:
    if not key:
        raise SittingRefusal("no-such-part", f"{about} names no key, and only a new part may have none")
    if key not in held:
        raise SittingRefusal(
            "no-such-part",
            f"{about} names {key}, which is not a part this product has written down: "
            f"{', '.join(sorted(held)) or 'it has none'}",
        )
    return key


def _entry(one: dict[str, Any], index: int, telling: Telling) -> Entry:
    what = " ".join(str(one.get("what") or "").split())
    telling.said(str(one.get("said") or "").strip(), f"ledger[{index}]")
    return Entry(what=what, kind=str(one.get("kind") or ""))


def settle(first: Reading, second: Reading) -> Reading:
    """The reading the owner's answers left, merged by the program and not by a session.

    A row the settling answered for replaces the row that asked; everything else
    stands exactly as the first turn left it. The order is the first turn's, so
    the file the owner reads afterwards is not reshuffled by a second session.
    """
    answered = {row.key: row for row in second.rows}
    return Reading(
        rows=[answered.get(row.key, row) for row in first.rows],
        ledger=first.ledger,
    )
