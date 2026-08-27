"""The hour with the owner: the kit holds the loop, and the model never does.

Who owns the loop was the question this step had to answer, and the answer is
the kit. The alternative — a provider's CLI attached to a terminal — puts the
owner's words in a channel the kit cannot see: no `raw.txt`, no contract, no
range that points back at what was said, and the session holding the pen over
the owner's own files. It also cannot be driven by anything, which means it
cannot be trapped, which means it cannot be shipped.

So: the owner's words are read once and written down; a headless turn reads
them against what is written down; the program prints the reading and puts only
the contradictions to the person who is standing right here; a second headless
turn settles those; and the program writes the files. Two sessions, one round
of questions, and every handover a file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date
from pathlib import Path
from typing import Any, Callable, Iterator

from ..driver.session import Sessions, Standing
from ..driver.workspace import StepWorkspace
from ..errors import ChannelError, ConfigError, KitError, StateError, UsageError
from ..knowledge import Knowledge
from ..logs import get_logger
from ..machine import Ledger, ledger_path
from ..paths import Paths
from ..project import require_project
from ..state.store import keep_sittings_out_of_git
from .read import Reading, read, settle
from .steps import READING, SETTLING, UNCHANGED
from .telling import SittingRefusal, Telling
from .write import Written, write

log = get_logger("sitting")

SITTINGS = "sittings"
TELLING = "telling.txt"
ANSWERS = "answers.txt"


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


class Sitting:
    """One telling, from the terminal to the files."""

    def __init__(
        self,
        root: Path | str,
        sessions: Sessions,
        today: str = "",
        say: Callable[[str], Any] | None = None,
        answers: Iterator[str] | None = None,
        ledger: Ledger | None = None,
    ) -> None:
        self.root = Path(root)
        self.sessions = sessions
        # The same one the driver writes to: a ceiling or a lease that a sitting
        # can slip past is a ceiling that is off for whoever forgot it.
        self.ledger = ledger or sessions.ledger
        self.today = today or _date.today().isoformat()
        self.say = say or print
        #: Where an answer comes from. Always the terminal — the telling may be
        #: a file, an answer never is: a sitting is with somebody.
        self.answers = answers
        self._standing: list = []
        self._knowledge: Knowledge | None = None

    # --- where its paperwork lives ----------------------------------------

    def room(self, name: str) -> Path:
        return self.root / ".agent-kit/v3" / SITTINGS / name

    def name_for(self) -> str:
        """Today, and an ordinal where today already had one."""
        held = self.root / ".agent-kit/v3" / SITTINGS
        name = self.today
        ordinal = 1
        while (held / name).is_dir():
            ordinal += 1
            name = f"{self.today}-{ordinal}"
        return name

    # --- the sitting ------------------------------------------------------

    def hold(self, telling: Telling) -> Outcome:
        """One sitting, and one writer in the working copy while it lasts.

        The lease is taken before a session is asked anything and given back in
        a `finally`, exactly as a slot is. It is the lease a run started by hand
        takes for the same reason: a sitting writes into the project's own
        checkout, and two writers in one working copy is two things editing one
        file. It is not a slot — a working copy is not quota.
        """
        if telling.empty:
            raise UsageError(
                "nothing-was-told",
                "the telling is empty, and a sitting is what somebody says about their product",
            )

        project = require_project(self.root)
        where = project.knowledge_dir
        if where is None:
            raise ConfigError(
                "no-knowledge-declared",
                "this project's declaration says it keeps no knowledge, so there is nowhere for a "
                "description to go",
                hint='take `knowledge = ""` out of .agent-kit/v3/project.toml',
            )
        knowledge = Knowledge(where)

        held = self.ledger.hold_checkout(str(self.root), "knowledge tell")
        if not held.granted:
            raise StateError(held.code, held.detail)
        try:
            return self._sit(telling, knowledge)
        finally:
            self.ledger.release(held)

    def _sit(self, telling: Telling, knowledge: Knowledge) -> Outcome:
        name = self.name_for()
        room = self.room(name)
        room.mkdir(parents=True, exist_ok=True)
        # Before the first word of it is written down. The room holds an hour of
        # the owner's own speech, and the kit ends by asking them to commit a
        # diff — so nothing here may be waiting in it when they do.
        keep_sittings_out_of_git(room.parent)
        # First, before anything is asked of anybody: the telling is the thing
        # every row is checked against, and it must survive a session dying, a
        # machine that is full, and the owner closing the terminal.
        (room / TELLING).write_text(telling.text, encoding="utf-8")

        subject = Standing(slug=name, project=str(self.root))
        standing = knowledge.parts()
        self._standing, self._knowledge = standing, knowledge
        outcome = Outcome(name=name, records=len(knowledge.anchors()))

        reading = self._turn(
            subject, READING, room, 0, telling, knowledge,
            judge=lambda output: read(output, telling, standing),
        )
        first = read(reading, telling, standing)
        self._print(first, outcome)

        asked = self._ask(first, room)
        outcome.asked = asked
        if asked:
            only = {key for key, _ in asked}
            settled = self._turn(
                subject, SETTLING, room, 1, telling, knowledge,
                judge=lambda output: read(output, telling, standing, only=only),
                answered=asked,
                reading=first,
            )
            first = settle(first, read(settled, telling, standing, only=only))

        outcome.reading = first
        outcome.written = write(knowledge, first, self.today)
        self._told(outcome)
        return outcome

    # --- one headless turn ------------------------------------------------

    def _turn(
        self,
        subject: Standing,
        definition,
        room: Path,
        index: int,
        telling: Telling,
        knowledge: Knowledge,
        judge: Callable[[dict], Any],
        answered: list[tuple[str, str]] | None = None,
        reading: Reading | None = None,
    ) -> dict:
        workspace = StepWorkspace(room, index, definition.name)
        attempts = {"n": 0}

        def on_start(provider: str):
            attempts["n"] += 1
            return subject, attempts["n"]

        enclosures = [
            ("what the owner said, with a number on every line", telling.numbered()),
            ("the project's knowledge, as an index", knowledge.index()),
        ]
        if reading is not None and answered is not None:
            enclosures += [
                ("the reading you returned", _as_json(workspace_output(room, 0))),
                (
                    "what the owner answered, and nothing else was asked",
                    "\n".join(f"{key}: {answer}" for key, answer in answered),
                ),
            ]

        walked = self.sessions.turn(
            subject, definition, workspace, definition.contract, enclosures, {},
            on_start=on_start, judge=judge,
        )
        if not walked.passed:
            last = walked.last
            if last is not None and last.busy is not None:
                # The machine said no before a session started. Nothing was
                # spent and nothing was written, and the telling is on disk.
                raise StateError(
                    last.busy.code,
                    f"{last.busy.detail}; what you said is kept at {room / TELLING}",
                )
            raise StateError(
                "sitting-refused",
                f"{definition.name} was refused {len(walked.attempts)} times, last: "
                f"{last.refusal if last else 'and said nothing'}; what you said is kept at "
                f"{room / TELLING}",
            )
        return workspace.read_output() or {}

    # --- what is put to the person standing here ---------------------------

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

    def _ask(self, reading: Reading, room: Path) -> list[tuple[str, str]]:
        """Only the contradictions, and only from the person who is here.

        There is no default and no twenty minutes. That machinery exists because
        a night has nobody to ask; this sitting is the hour when somebody is
        standing right here, and taking a default from them would be answering
        for a person who is in the room.
        """
        asked: list[tuple[str, str]] = []
        for row in reading.contradictions:
            self.say(f"? {row.question}")
            answer = self._answer()
            if answer is None:
                raise ChannelError(
                    "nobody-to-ask",
                    f"{row.key}: there is a contradiction to settle and nothing is answering. "
                    "Nothing has been written",
                    hint="agent-kit knowledge tell --from <файл>, and answer at the terminal",
                )
            asked.append((row.key, answer))
            # Written the moment it is typed. Kept until the end and then
            # dropped because a later question had nobody, it would be somebody
            # else's work thrown away for a reason that was not theirs.
            (room / ANSWERS).write_text(
                "\n".join(f"{key}: {said}" for key, said in asked) + "\n", encoding="utf-8"
            )
        return asked

    def _answer(self) -> str | None:
        if self.answers is None:
            return None
        try:
            return next(self.answers).strip()
        except StopIteration:
            return None

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
    return StepWorkspace(room, index, READING.name).read_output() or {}


def _as_json(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)
