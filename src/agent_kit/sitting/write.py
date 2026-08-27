"""Writing what the sitting came to — by the program, and never by the session.

The same sentence S6 wrote for `record`, for the same reason: an agent that
writes the file itself can always claim it did. The session returns rows; this
turns them into lines.

Everything resolves before anything is written. A sitting that half-wrote the
owner's description and then refused would leave a file nobody will read again,
and that is worse than a sitting that wrote nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..knowledge import Knowledge, identifier
from ..knowledge.parts import LEDGER, SEPARATOR
from ..state.store import write_whole
from .read import Reading
from .steps import BADLY, BROKEN, UNCHANGED

#: Where each kind of ledger line goes. The kind decides the section and does
#: nothing else; if that stopped being true the field would be deleted rather
#: than documented.
SECTIONS = {
    BADLY: "Работает плохо",
    BROKEN: "Не работает",
}

#: The heading a ledger is made with, and the two sentences under it. Nothing
#: here promises a check: no program reads this prose, and a template that
#: states a rule nobody runs is the defect this whole layer exists against.
LEDGER_HEAD = [
    "# Технический долг",
    "",
    "Что уже построено и работает не так. Строки пишет `agent-kit knowledge tell`;",
    "закрывает их тот, кто сделал работу.",
]


@dataclass(frozen=True)
class Written:
    """What reached the disk, so the person standing here is told and not asked to look."""

    parts: list[str]
    ledger: list[str]
    files: list[Path]


def write(knowledge: Knowledge, reading: Reading, today: str) -> Written:
    """The parts, then the ledger. Both by key, so a second telling rewrites its own."""
    files: list[Path] = []
    written: list[str] = []
    for row in reading.rows:
        if row.verdict == UNCHANGED:
            # Not even the mark moves. A part the telling did not touch keeps
            # the line somebody wrote by hand, down to its spacing.
            continue
        path = knowledge.write_part(row.key, row.name, row.says, today)
        written.append(row.key)
        if path not in files:
            files.append(path)

    said: list[str] = []
    for entry in reading.ledger:
        path = _ledger_line(knowledge, entry.what, entry.kind)
        said.append(entry.what)
        if path not in files:
            files.append(path)

    return Written(parts=written, ledger=said, files=files)


def _ledger_line(knowledge: Knowledge, what: str, kind: str) -> Path:
    """One line of the ledger, replaced where it stands and appended where it does not.

    A ledger line carries a key and no mark, and that is deliberate: a mark is
    what makes a list item a *part of the product*, and a line about work that
    is wrong is not one. The file itself is left out of `described` for the same
    reason — its headings are records like any other, and a telling of nothing
    but bugs must not leave a project the gate calls described.
    """
    if knowledge.root is None:
        raise ValueError("a sitting that writes has a knowledge directory")
    knowledge.root.mkdir(parents=True, exist_ok=True)
    path = knowledge.root / LEDGER
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else list(LEDGER_HEAD)

    key = identifier("debt", " ".join(what.split()).casefold())
    line = f"- {' '.join(what.split())}{SEPARATOR}`key: {key}`"
    for index, held in enumerate(lines):
        if f"`key: {key}`" in held:
            lines[index] = line
            write_whole(path, "\n".join(lines) + "\n")
            return path

    heading = f"## {SECTIONS[kind]}"
    if heading not in lines:
        lines += ["", heading, "", line]
    else:
        at = lines.index(heading) + 1
        while at < len(lines) and not lines[at].startswith("## "):
            at += 1
        while at > 0 and not lines[at - 1].strip():
            at -= 1
        lines = lines[:at] + [line] + lines[at:]
    write_whole(path, "\n".join(lines) + "\n")
    return path
