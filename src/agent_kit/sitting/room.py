"""What is the same about every hour spent with the owner.

Two of them exist: the one where somebody says what their product is, and the
one where somebody says what tonight builds. They read different things and
they write different things, and everything in between is one shape — the kit
holds the loop, the owner's words are written down before anything is asked,
two headless turns go through the same providers every step of a run uses, and
only what genuinely needs a person is put to the person who is standing here.

So the shape is here and the two drivers on top of it are small. A second copy
of this would be a second copy of the mechanism a dozen traps already watch,
and it would inherit none of them — the same argument S8a made about the chain
of attempts, applied one layer up.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path
from typing import Any, Callable, Iterator

from ..driver.session import Sessions, Standing
from ..driver.workspace import StepWorkspace
from ..errors import ChannelError, StateError, UsageError
from ..knowledge import Knowledge
from ..machine import Ledger
from ..project import require_project
from ..state.store import keep_sittings_out_of_git
from .telling import Telling

SITTINGS = "sittings"
TELLING = "telling.txt"
ANSWERS = "answers.txt"


@dataclass(frozen=True)
class Opened:
    """The paperwork of one sitting: where it lives and what it is about."""

    name: str
    room: Path
    subject: Standing
    knowledge: Knowledge


class Sitting:
    """One telling, from the terminal to the files. Subclasses say which files."""

    #: What the lease over the working copy says it is being held for. The
    #: machine's page prints this, and a page that says `knowledge tell` while
    #: a batch is being composed is a page telling somebody the wrong thing.
    held_for = "a sitting"

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

    def hold(self, telling: Telling) -> Any:
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
                "the telling is empty, and a sitting is what somebody says out loud",
            )
        held = self.ledger.hold_checkout(str(self.root), self.held_for)
        if not held.granted:
            raise StateError(held.code, held.detail)
        try:
            return self._sit(telling)
        finally:
            self.ledger.release(held)

    def _sit(self, telling: Telling) -> Any:
        raise NotImplementedError

    def _open(self, telling: Telling) -> Opened:
        """The room, the words in it, and what this project has written down.

        The telling goes to disk before anything is asked of anybody: it is the
        thing every row is checked against, and it must survive a session dying,
        a machine that is full, and the owner closing the terminal.
        """
        project = require_project(self.root)
        name = self.name_for()
        room = self.room(name)
        room.mkdir(parents=True, exist_ok=True)
        # Before the first word of it is written down. The room holds an hour of
        # the owner's own speech, and the kit ends by asking them to commit a
        # diff — so nothing here may be waiting in it when they do.
        keep_sittings_out_of_git(room.parent)
        (room / TELLING).write_text(telling.text, encoding="utf-8")
        return Opened(
            name=name,
            room=room,
            subject=Standing(slug=name, project=str(self.root)),
            knowledge=Knowledge(project.knowledge_dir),
        )

    # --- one headless turn ------------------------------------------------

    def _turn(
        self,
        opened: Opened,
        definition,
        index: int,
        enclosures: list[tuple[str, str]],
        judge: Callable[[dict], Any],
    ) -> dict:
        workspace = StepWorkspace(opened.room, index, definition.name)
        attempts = {"n": 0}

        def on_start(provider: str):
            attempts["n"] += 1
            return opened.subject, attempts["n"]

        walked = self.sessions.turn(
            opened.subject, definition, workspace, definition.contract, enclosures, {},
            on_start=on_start, judge=judge,
        )
        if not walked.passed:
            last = walked.last
            where = opened.room / TELLING
            if last is not None and last.busy is not None:
                # The machine said no before a session started. Nothing was
                # spent and nothing was written, and the telling is on disk.
                raise StateError(last.busy.code, f"{last.busy.detail}; what you said is kept at {where}")
            raise StateError(
                "sitting-refused",
                f"{definition.name} was refused {len(walked.attempts)} times, last: "
                f"{last.refusal if last else 'and said nothing'}; what you said is kept at {where}",
            )
        return workspace.read_output() or {}

    # --- what is put to the person standing here ---------------------------

    def ask(self, questions: list[tuple[str, str]], room: Path) -> list[tuple[str, str]]:
        """Only what needs a person, and only from the person who is here.

        There is no default and no twenty minutes. That machinery exists because
        a night has nobody to ask; a sitting is the hour when somebody is
        standing right here, and taking a default from them would be answering
        for a person who is in the room.
        """
        asked: list[tuple[str, str]] = []
        for key, question in questions:
            self.say(f"? {question}")
            answer = self._answer()
            if answer is None:
                raise ChannelError(
                    "nobody-to-ask",
                    f"{key}: there is something to settle and nothing is answering. "
                    "Nothing has been written",
                    hint="pass the telling with --from <файл>, and answer at the terminal",
                )
            asked.append((key, answer))
            # Written the moment it is typed. Kept until the end and then
            # dropped because a later question had nobody, it would be somebody
            # else's work thrown away for a reason that was not theirs.
            (room / ANSWERS).write_text(
                "\n".join(f"{one}: {said}" for one, said in asked) + "\n", encoding="utf-8"
            )
        return asked

    def _answer(self) -> str | None:
        if self.answers is None:
            return None
        try:
            return next(self.answers).strip()
        except StopIteration:
            return None
