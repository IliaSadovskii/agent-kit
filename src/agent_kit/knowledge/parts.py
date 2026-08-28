"""A part of the product, and the mark that says who said it.

The second version wrote the parts as list items, and this is the measurement
of them rather than a memory:

    - задание — описание, ответ, проверка моделью — `walked: 2026-08-13`
    - вход — Google, Apple, учётная запись — `derived`

So a part stays a list item. What the third version adds is a key, in a segment
of exactly the kind the same line already carries — the argument S6 made for
`id:` on a block, applied to a line that already ends in one backticked
segment. No line anybody wrote is rewritten, and there is nothing to migrate.

**A part is a list item that carries a mark, and the mark is what finds it.**
Not "a list item under `## Части`": a section name is a word in one project's
language, and a reader that turns on it is a reader that goes blind the day
somebody renames a heading. The mark is the kit's own and cannot drift.

**A key is derived where the line carries none** — from the part's own name,
over the alphabet `identifier()` already uses. Derived rather than drawn, for
the reason S6 gives: a bench case can say what it must be before the run. Where
the kit writes a part it writes the key into the line, because a rename is
exactly what a second telling does, and a key derived from the name every time
would read a renamed part as a new one and lay a second line beside the first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .format import KnowledgeError, identifier, prose

#: What a part carries when nobody has confirmed it: worked out from the code
#: and never walked. The kit reads it; S8a does not write it, because the step
#: that works things out from code is the audit and it is not built yet.
DERIVED = "derived"

#: Where the kit puts the parts when a project has none at all. The project's
#: own language, because the file is the owner's to read — and it is written
#: only into a file the kit is creating from nothing.
PARTS_HEADING = "## Части"

PRODUCT = "product.md"

_ITEM = re.compile(r"^\s*[-*]\s+(?P<body>.*\S)\s*$")
#: The last backticked segment of a line, and only the last: a part's marks
#: come off its end one at a time, and `search` on an unanchored pattern
#: finds the leftmost instead — which read a description holding a `word`
#: as though it were the mark.
_SEGMENT = re.compile(r"`(?P<inside>[^`]+)`\s*$")
_WALKED = re.compile(r"^walked:\s*(?P<date>\d{4}-\d{2}-\d{2})$")
_KEY = re.compile(r"^key:\s*(?P<key>[^·]+?)$")
#: Whatever the second version put between a part's name and its description.
#: An em dash with spaces around it, which is what every line of it uses.
SEPARATOR = " — "


@dataclass(frozen=True)
class Part:
    """One part of the product, and where its line stands."""

    key: str
    name: str
    says: str
    #: A date the owner walked it, or `derived`.
    mark: str
    file: str
    line: int

    @property
    def walked(self) -> bool:
        return self.mark != DERIVED


def part_key(name: str) -> str:
    """The key of a line that carries none, from the part's own first words.

    The same idiom as a block's identifier and for the same reason: a case on
    the bench can name it in advance, so a judge asks the kit what the key must
    be instead of accepting whatever came out.
    """
    return identifier("part", " ".join(name.split()).casefold())


def read_parts(file: str, lines: list[str]) -> list[Part]:
    """Every part in one file, in the order they stand."""
    found: list[Part] = []
    written = prose(file, lines)
    for index, line in enumerate(lines):
        item = _ITEM.match(line) if written[index] else None
        if item is None:
            continue
        part = _read_item(item.group("body"), file, index)
        if part is not None:
            found.append(part)
    return found


def _read_item(body: str, file: str, index: int) -> Part | None:
    """A list item, if it carries a mark. Its marks come off the end first."""
    mark = ""
    key = ""
    rest = body
    while True:
        trimmed = rest.rstrip()
        segment = _SEGMENT.search(trimmed)
        if segment is None:
            break
        inside = segment.group("inside").strip()
        walked = _WALKED.match(inside)
        named = _KEY.match(inside)
        if walked is not None:
            mark = mark or walked.group("date")
        elif inside == DERIVED:
            mark = mark or DERIVED
        elif named is not None:
            key = key or named.group("key").strip()
        else:
            break
        rest = trimmed[: segment.start()].rstrip().rstrip("·—-").rstrip()

    if not mark:
        return None
    name, _, says = rest.partition(SEPARATOR)
    name = name.strip()
    if not name:
        return None
    return Part(
        key=key or part_key(name),
        name=name,
        says=says.strip(),
        mark=mark,
        file=file,
        line=index,
    )


def render_part(key: str, name: str, says: str, mark: str) -> str:
    """One line, and one line only.

    A part that wrapped would need a parser that knows where a list item ends,
    and every line of the real knowledge is one line. What is long here is a
    part that wants to be two parts.
    """
    said = f"{SEPARATOR}{' '.join(says.split())}" if says.strip() else ""
    return f"- {' '.join(name.split())}{said}{SEPARATOR}`key: {key}` · `{_mark(mark)}`"


def _mark(mark: str) -> str:
    if mark == DERIVED:
        return DERIVED
    if not _WALKED.match(f"walked: {mark}"):
        raise KnowledgeError(
            "bad-mark", f"{mark!r} is neither a date the owner walked this part nor {DERIVED!r}"
        )
    return f"walked: {mark}"
