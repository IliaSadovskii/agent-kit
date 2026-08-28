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

from dataclasses import dataclass

from .format import identifier, read_items

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

#: What a segment of a ledger line may be called. Everything else stops the
#: peeling, a part's `walked:` among them — which is what keeps a part standing
#: in this file from being read as debt.
SEGMENTS = frozenset({"key", "run"})


@dataclass(frozen=True)
class Debt:
    """One line of the ledger, and where it stands."""

    key: str
    what: str
    #: The run that found it, or empty where the owner said it.
    run: str
    file: str
    line: int


#: What a ledger key is derived from, beside the words themselves. One place,
#: because `free_key` walks the same derivation with a salt and two spellings of
#: one formula is one that will disagree with itself.
DEBT_SEED = "debt"


def debt_key(what: str) -> str:
    """The key of a line, from its own words.

    Derived rather than drawn, for the reason S6 gives for a block's identifier:
    a bench case can ask the kit what the key must be instead of asserting
    whatever came out. Case and spacing are flattened first, so a complaint told
    twice with a capital letter is one line rather than two.
    """
    return identifier(DEBT_SEED, " ".join(what.split()).casefold())


def read_debt(file: str, lines: list[str]) -> list[Debt]:
    """Every line of the ledger, in the order they stand.

    The peeling itself is `format.read_items`: one parser, and the manual
    actions of S8g are the second file read by it. A line is one that carries a
    key and still has words of its own left after its segments come off.
    """
    return [
        Debt(
            key=item.said["key"],
            what=item.body,
            run=item.said.get("run", ""),
            file=file,
            line=item.line,
        )
        for item in read_items(file, lines, SEGMENTS)
        if "key" in item.said and item.body
    ]


def render_debt(key: str, what: str, run: str = "") -> str:
    """One line, and one line only.

    A line that wrapped would need a parser that knows where a list item ends.
    What is long here is a finding that wants to be two findings.
    """
    said = f"{SEPARATOR}`run: {run}`" if run.strip() else ""
    return f"- {' '.join(what.split())}{SEPARATOR}`key: {key}`{said}"
