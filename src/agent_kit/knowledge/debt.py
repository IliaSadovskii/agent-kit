"""The ledger: what is built and works badly, one line at a time.

Measured before it was designed. The second version's ledger is a real file and
a busy one — 110 open lines in `beeplish` against a single `found` block in the
whole of its knowledge — and its own header says what it is for: *«Пишут
прогоны, читают перед каждой командой, закрывает тот, кто её сделает.
Закрывается удалением строки в том же коммите, что делает работу, — не
галочкой.»* That is the loop this file rebuilds, and the second version's own
measurement of where it broke is the reason it is rebuilt whole: a ledger line
whose named closer never removed lines survived the work that answered it, for
ever.

**A line is a list item that carries a key and no mark.** The mark is what makes
a list item a *part of the product*, and work that is wrong is not one. So the
two readers cannot see each other's lines, and neither reads the heading above
them: a section name is one project's word, and a reader that turns on it goes
blind the day somebody renames it. Only `debt.md` is read this way, and naming
that file is allowed because it is the kit's own name rather than a word the
project chose.

**The `run:` segment says a night found it; its absence says the owner did.**
One more `·` segment of a kind the line already carries — the same move that
gave a block `id:` and a part `key:`. The second version marked the owner's own
lines `владелец` for the same reason: the two read differently, and a reader who
cannot tell them apart cannot weigh either.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .format import identifier, prose

#: The file. The kit's own name, which is what lets `described` leave it out
#: and what lets this reader be sure it is not reading somebody's shopping list.
LEDGER = "debt.md"

#: What a line says about itself. `badly` — it does what it should and does it
#: badly; `broken` — it does not work at all. The kind chooses the section and
#: does nothing else, which is why it is not a segment on the line: a field
#: nobody reads back is a field that is not written.
BADLY = "badly"
BROKEN = "broken"

#: Where each kind goes. In the project's own language, because the file is the
#: owner's to read.
SECTIONS = {BADLY: "Работает плохо", BROKEN: "Не работает"}

#: The heading a ledger is made with, and the sentences under it. Nothing here
#: promises a check: no program reads this prose, and a template that states a
#: rule nobody runs is the defect this whole layer exists against. It is written
#: once, when the file is created; a ledger that already stands keeps the header
#: it has, because no line anybody wrote is rewritten.
LEDGER_HEAD = [
    "# Технический долг",
    "",
    "Что уже построено и работает не так. Пишут двое: час с владельцем",
    "(`agent-kit knowledge tell`) — с его слов, и ночь партии — из находок ревью.",
    "Строка закрывается удалением: её убирает работа, которая эту строку назвала,",
    "или владелец своей рукой. Ключ в строке — то, чем на неё ссылаются.",
]

#: Whatever stands between a line's words and its segments.
SEPARATOR = " · "

_ITEM = re.compile(r"^\s*[-*]\s+(?P<body>.*\S)\s*$")
#: The last backticked segment of a line, and only the last — the same reason
#: `parts.py` anchors its own: an unanchored search finds the leftmost, which
#: reads a description holding a `word` as though it were a segment.
_SEGMENT = re.compile(r"`(?P<inside>[^`]+)`\s*$")
_PAIR = re.compile(r"^(?P<name>key|run):\s*(?P<value>[^·]+?)$")


@dataclass(frozen=True)
class Debt:
    """One line of the ledger, and where it stands."""

    key: str
    what: str
    #: The run that found it, or empty where the owner said it.
    run: str
    file: str
    line: int


def debt_key(what: str) -> str:
    """The key of a line, from its own words.

    Derived rather than drawn, for the reason S6 gives for a block's identifier:
    a bench case can ask the kit what the key must be instead of asserting
    whatever came out. Case and spacing are flattened first, so a complaint told
    twice with a capital letter is one line rather than two.
    """
    return identifier("debt", " ".join(what.split()).casefold())


def read_debt(file: str, lines: list[str]) -> list[Debt]:
    """Every line of the ledger, in the order they stand."""
    found: list[Debt] = []
    written = prose(file, lines)
    for index, line in enumerate(lines):
        item = _ITEM.match(line) if written[index] else None
        if item is None:
            continue
        one = _read_item(item.group("body"), file, index)
        if one is not None:
            found.append(one)
    return found


def _read_item(body: str, file: str, index: int) -> Debt | None:
    """A list item, if it carries a key and nothing that makes it a part.

    Its segments come off the end one at a time, and anything that is not one of
    this vocabulary's stops the peeling — a part's `walked:` among them, which
    is what keeps a part standing in this file from being read as debt.
    """
    said: dict[str, str] = {}
    rest = body
    while True:
        trimmed = rest.rstrip()
        segment = _SEGMENT.search(trimmed)
        if segment is None:
            break
        pair = _PAIR.match(segment.group("inside").strip())
        if pair is None:
            break
        said.setdefault(pair.group("name"), pair.group("value").strip())
        rest = trimmed[: segment.start()].rstrip().rstrip("·—-").rstrip()

    if "key" not in said or not rest.strip():
        return None
    return Debt(key=said["key"], what=rest.strip(), run=said.get("run", ""), file=file, line=index)


def render_debt(key: str, what: str, run: str = "") -> str:
    """One line, and one line only.

    A line that wrapped would need a parser that knows where a list item ends.
    What is long here is a finding that wants to be two findings.
    """
    said = f"{SEPARATOR}`run: {run}`" if run.strip() else ""
    return f"- {' '.join(what.split())}{SEPARATOR}`key: {key}`{said}"
