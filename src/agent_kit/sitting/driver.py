"""The hour in which somebody says what their product is.

Who owns the loop was the question S8a had to answer, and the answer is the
kit — see `room.py`, which now holds that shape for both sittings. What is here
is only what makes this one the knowledge's: it reads the telling against the
parts written down, prints the reading, asks the contradictions, and writes the
description and the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..errors import ConfigError
from ..knowledge import Knowledge
from ..project import require_project
from ..logs import get_logger
from .read import Reading, read, settle
from .room import ANSWERS, SITTINGS, TELLING, Opened, Sitting as Held
from .steps import READING, SETTLING, UNCHANGED
from .telling import Telling
from .write import Written, write

log = get_logger("sitting")

__all__ = ["ANSWERS", "Outcome", "SITTINGS", "Sitting", "TELLING", "workspace_output"]


@dataclass
class Outcome:
    """What the sitting came to, for the person who is standing here."""

    name: str
    reading: Reading | None = None
    written: Written | None = None
    asked: list[tuple[str, str]] = field(default_factory=list)
    #: Every addressable record of the knowledge that is not a part. The
    #: denominator: "so many parts were read against so many records that were
    #: not." A count said without its denominator is a count that cannot be wrong.
    records: int = 0


class Sitting(Held):
    """One telling about a product, from the terminal to the owner's own files."""

    held_for = "knowledge tell"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._standing: list = []
        self._knowledge: Knowledge | None = None

    def _sit(self, telling: Telling) -> Outcome:
        # Before the room is made, and that is the whole of why it is here and
        # not below `_open`: a sitting that leaves an hour of paperwork in a
        # project it had nowhere to write to has already dirtied a working copy
        # the owner is about to read a diff of.
        if require_project(self.root).knowledge_dir is None:
            raise ConfigError(
                "no-knowledge-declared",
                "объявление проекта говорит, что знания он не держит, значит описанию "
                "некуда деться",
                hint='уберите `knowledge = ""` из .agent-kit/v3/project.toml',
            )

        opened = self._open(telling)
        knowledge = opened.knowledge
        standing = knowledge.parts()
        self._standing, self._knowledge = standing, knowledge
        outcome = Outcome(name=opened.name, records=len(knowledge.anchors()))

        reading = self._turn(
            opened, READING, 0,
            [
                ("what the owner said, with a number on every line", telling.numbered()),
                ("the project's knowledge, as an index", knowledge.index()),
            ],
            judge=lambda output: read(output, telling, standing),
        )
        first = read(reading, telling, standing)
        self._print(first, outcome)

        asked = self.ask(
            [(row.key, row.question) for row in first.contradictions], opened.room
        )
        outcome.asked = asked
        if asked:
            only = {key for key, _ in asked}
            settled = self._turn(
                opened, SETTLING, 1,
                [
                    ("what the owner said, with a number on every line", telling.numbered()),
                    ("the project's knowledge, as an index", knowledge.index()),
                    ("the reading you returned", _as_json(workspace_output(opened.room, 0))),
                    (
                        "what the owner answered, and nothing else was asked",
                        "\n".join(f"{key}: {answer}" for key, answer in asked),
                    ),
                ],
                judge=lambda output: read(output, telling, standing, only=only),
            )
            first = settle(first, read(settled, telling, standing, only=only))

        outcome.reading = first
        outcome.written = write(knowledge, first, self.today)
        self._told(outcome)
        return outcome

    # --- what the person standing here is shown ---------------------------

    def _print(self, reading: Reading, outcome: Outcome) -> None:
        self.say("")
        for row in reading.rows:
            said = f"  {row.name}" if row.name else ""
            # What already stands where this line is about to be rewritten. A
            # part four runs have written down what they assumed under is a
            # different thing to rewrite from one nothing has touched, and it is
            # worth knowing before, not after.
            beside = "" if row.verdict == UNCHANGED else self._beside(row.key)
            self.say(f"  {row.verdict:<12} {row.key:<8}{said}{beside}")
        for entry in reading.ledger:
            self.say(f"  {'ledger':<12} {entry.kind:<8}  {entry.what}")
        self.say("")
        self.say(f"  {reading.counts()}")
        # The denominator, because a count with none cannot be wrong. The parts
        # were read against every part there is; the records that are not parts
        # were not read at all, and saying so is cheaper than being asked.
        # A part is a list item and a record is a heading, so the two sets do
        # not overlap: every addressable record of this knowledge is a record
        # this sitting did not read.
        self.say(
            f"  сверено частей: {len(reading.rows)}; записей вне частей не читалось: {outcome.records}"
        )
        self.say("")

    def _beside(self, key: str) -> str:
        standing = [part for part in self._standing if part.key == key]
        if not standing:
            return ""
        blocks = self._knowledge.blocks_beside(standing[0]) if self._knowledge else 0
        return f"   (рядом стоит блоков, написанных до правки: {blocks})" if blocks else ""

    def _told(self, outcome: Outcome) -> None:
        written = outcome.written
        if written is None:
            return
        self.say(f"  частей записано: {len(written.parts)}; строк в реестр: {len(written.ledger)}")
        for path in written.files:
            self.say(f"  {path}")
        self.say("")
        self.say("  Кит не коммитит: прочитайте diff и закоммитьте сами.")


def workspace_output(room: Path, index: int) -> dict:
    from ..driver.workspace import StepWorkspace

    return StepWorkspace(room, index, READING.name).read_output() or {}


def _as_json(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)
