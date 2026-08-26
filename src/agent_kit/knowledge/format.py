"""The shape of a block, and the shape of an address.

The format is the second version's, measured rather than remembered. Over the
193 blocks of `beeplish/docs/knowledge` there are exactly two header shapes:

    > **[assumed 2026-08-18 · claude/2026-08-17-own-key-01-key-storage]** …
    > **[frame 2026-08-19 · 2026-08-19-teardown · pr: 29]** …

Segments after the kind and the date are `·`-separated, and one of them already
carries a `key: value`. That is why the identifier this version adds is not a
new syntax: it is one more segment of a kind the format already writes.
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import dataclass

#: Digits and consonants. Six characters of it cannot spell anything
#: unfortunate, which is the whole reason the vowels are not here.
ALPHABET = "23456789bcdfghjkmnpqrstvwxz"

ID_LENGTH = 6

#: Where the real knowledge already wraps: median 96, p90 101.
WIDTH = 100

QUOTE = "> "

#: The kind this version writes. `frame` belongs to a batch, `found` to a
#: reviewer whose findings do not reach the knowledge yet, and `stale` to
#: whoever notices. A kind with no writer is the mirror of a field with no
#: reader, and the kit refuses both. `accepted` is dropped.
ASSUMED = "assumed"

_HEADER = re.compile(r"^\s*>\s*\*\*\[(?P<kind>[a-z]+) (?P<date>\d{4}-\d{2}-\d{2})(?P<rest>[^\]]*)\]\*\*")
_QUOTED = re.compile(r"^\s*>")
_PAIR = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<value>.+)$")
_HEADING = re.compile(r"^(?P<hashes>#{1,6}) (?P<text>.+?)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_COMMENT_OPEN = "<!--"
_COMMENT_CLOSE = "-->"
_KEY_LINE = re.compile(r"^`key:\s*(?P<key>[A-Za-z0-9_.-]+)`")

SEPARATOR = " · "


@dataclass(frozen=True)
class Block:
    """One block, and where in its file it sits."""

    kind: str
    date: str
    run: str
    id: str
    first_line: str
    file: str
    start: int
    end: int  # exclusive


@dataclass(frozen=True)
class Anchor:
    """One addressable place: a record with a key, or a heading in a prose file."""

    file: str
    anchor: str
    heading: str
    level: int
    line: int


def identifier(slug: str, what: str, salt: int = 0) -> str:
    """The identifier a run gives an assumption, derived rather than drawn.

    Three reasons it is not random, in order of weight: a bench case can name
    it; an attempt that died after editing the file writes the same block again
    instead of a second one beside it; and it is short enough to say out loud.
    """
    seed = f"{slug}\0{what}" + (f"\0{salt}" if salt else "")
    number = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest(), "big")
    out = []
    for _ in range(ID_LENGTH):
        number, rest = divmod(number, len(ALPHABET))
        out.append(ALPHABET[rest])
    return "".join(out)


def header(kind: str, date: str, run: str, id: str) -> str:
    return f"**[{kind} {date}{SEPARATOR}{run}{SEPARATOR}id: {id}]**"


def render(kind: str, date: str, run: str, id: str, body: str) -> list[str]:
    """The block as lines, quoted and wrapped where the real knowledge wraps."""
    text = " ".join(body.split())
    wrapped = textwrap.wrap(
        f"{header(kind, date, run, id)} {text}",
        width=WIDTH - len(QUOTE),
        break_long_words=False,
        break_on_hyphens=False,
    )
    return [f"{QUOTE}{line}" for line in wrapped or [header(kind, date, run, id)]]


def prose(lines: list[str]) -> list[bool]:
    """Which lines the file writes, rather than only shows.

    Two things are shown. A fenced sample: a `### Пример` inside one is not a
    record, and a quoted block inside one illustrates a block rather than being
    one. And an HTML comment, which is where the second version's templates
    keep their example record — all six of them — so a project that has started
    its knowledge and not filled it in carries a `key:` no renderer displays.
    Reading that as a record puts it in the index the driver encloses, and a
    block addressed to it is written inside the comment, where nobody sees it
    again. The second version knew this and had `commented()` for it.
    """
    outside: list[bool] = []
    fenced = False
    commented = False
    for line in lines:
        if commented:
            outside.append(False)
            commented = _COMMENT_CLOSE not in line
            continue
        if fenced:
            outside.append(False)
            fenced = not _FENCE.match(line)
            continue
        if _FENCE.match(line):
            fenced = True
            outside.append(False)
            continue
        # What stands before `<!--` on its line is written; what follows it is
        # not. A comment closed on the line it opened hides only itself.
        opens = line.find(_COMMENT_OPEN)
        commented = opens >= 0 and _COMMENT_CLOSE not in line[opens:]
        outside.append(True)
    return outside


def read_blocks(file: str, lines: list[str]) -> list[Block]:
    """Every block in one file, in the order they stand."""
    found: list[Block] = []
    written = prose(lines)
    index = 0
    while index < len(lines):
        matched = _HEADER.match(lines[index]) if written[index] else None
        if matched is None:
            index += 1
            continue
        end = index + 1
        # A quoted line belongs to this block unless it starts the next one.
        # Two blocks with no blank line between them — or split by a bare `>`,
        # which is how markdown separates quotes — used to read as one, and
        # closing the first then took the second with it.
        while end < len(lines) and _QUOTED.match(lines[end]) and not _HEADER.match(lines[end]):
            end += 1
        run, pairs = _segments(matched.group("rest"))
        found.append(
            Block(
                kind=matched.group("kind"),
                date=matched.group("date"),
                run=run,
                id=pairs.get("id", ""),
                first_line=_HEADER.sub("", lines[index]).strip(),  # the header is a column of the index
                file=file,
                start=index,
                end=end,
            )
        )
        index = end
    return found


def _segments(rest: str) -> tuple[str, dict[str, str]]:
    """What comes after the date: one bare run name, and any number of `key: value`."""
    run = ""
    pairs: dict[str, str] = {}
    for segment in (piece.strip() for piece in rest.split("·")):
        if not segment:
            continue
        pair = _PAIR.match(segment)
        if pair is not None:
            pairs[pair.group("key")] = pair.group("value").strip()
        elif not run:
            run = segment
    return run, pairs


def read_anchors(file: str, lines: list[str]) -> list[Anchor]:
    """Every addressable place in one file.

    A record's anchor is its `key:` where it has one, and its heading's own text
    where it has not — which is how the three prose files of the real knowledge
    are addressed. No file there holds two headings of the same text, and where
    one does the address is refused rather than guessed.
    """
    found: list[Anchor] = []
    written = prose(lines)
    for index, line in enumerate(lines):
        heading = _HEADING.match(line) if written[index] else None
        if heading is None:
            continue
        if len(heading.group("hashes")) == 1:
            # The file's own title. A block "under `# Сущности`" is a block
            # anywhere in the file, which is not an address anybody wants.
            continue
        text = heading.group("text")
        found.append(
            Anchor(
                file=file,
                anchor=_key_below(lines, index) or text,
                heading=text,
                level=len(heading.group("hashes")),
                line=index,
            )
        )
    return found


def _key_below(lines: list[str], index: int) -> str:
    """`key: money` on the first non-blank line under the heading, and nowhere else."""
    for line in lines[index + 1: index + 4]:
        if not line.strip():
            continue
        matched = _KEY_LINE.match(line.strip())
        return matched.group("key") if matched else ""
    return ""


def section_end(lines: list[str], anchor: Anchor) -> int:
    """Where the anchor's section stops: the next heading of its level or higher."""
    written = prose(lines)
    for index in range(anchor.line + 1, len(lines)):
        heading = _HEADING.match(lines[index]) if written[index] else None
        if heading is not None and len(heading.group("hashes")) <= anchor.level:
            return index
    return len(lines)
