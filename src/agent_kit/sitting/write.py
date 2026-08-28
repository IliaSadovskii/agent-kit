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

from ..knowledge import Knowledge
from ..knowledge.debt import LEDGER
from .read import Reading
from .steps import UNCHANGED


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
        # The owner's own line, and the kit's only other writer of this file is
        # the night of a batch. A lone run writes none: its findings reach the
        # owner in the pull request, which is the channel it has.
        path = knowledge.write_debt(entry.what, entry.kind)
        said.append(entry.what)
        if path not in files:
            files.append(path)

    return Written(parts=written, ledger=said, files=files)
