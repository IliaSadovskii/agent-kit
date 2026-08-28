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

from ..errors import ExitCode, KitError

#: Digits and consonants. Six characters of it cannot spell anything
#: unfortunate, which is the whole reason the vowels are not here.
ALPHABET = "23456789bcdfghjkmnpqrstvwxz"

ID_LENGTH = 6

#: Where the real knowledge already wraps: median 96, p90 101.
WIDTH = 100

QUOTE = "> "

#: The two kinds this version writes, and each of them has one writer.
#: `assumed` is a run's — `record` — and `frame` is the composing sitting's,
#: which is the one place a whole evening's features are visible at once.
#: `found` still belongs to a reviewer whose findings do not reach the
#: knowledge, and `stale` to whoever notices; a kind with no writer is the
#: mirror of a field with no reader, and the kit refuses both. `accepted` is
#: dropped.
ASSUMED = "assumed"
FRAME = "frame"

_HEADER = re.compile(r"^\s*>\s*\*\*\[(?P<kind>[a-z]+) (?P<date>\d{4}-\d{2}-\d{2})(?P<rest>[^\]]*)\]\*\*")
_QUOTED = re.compile(r"^\s*>")
_PAIR = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<value>.+)$")
#: Whatever separates the hashes from the words, and the words without it.
#: One space was the rule, so `###  Оффер` kept its second space in the
#: anchor — an address the index printed and `resolve`, which strips what it
#: is given, then refused — and `###\tОффер` was not a heading at all.
_HEADING = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>\S.*?)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_COMMENT_OPEN = "<!--"
_COMMENT_CLOSE = "-->"
#: Everything up to the closing backtick, which is what the second version's
#: `KEY_RE` took. A key is the project's word, not the kit's: `платёж` and
#: `offer request` are addresses like any other. The `·` is the one thing it
#: cannot hold, because that is what separates the key from `state:` beside it.
_KEY_LINE = re.compile(r"^`key:\s*(?P<key>[^`·]+?)\s*`")
_KEY_STARTS = re.compile(r"^`key:")

SEPARATOR = " · "


class KnowledgeError(KitError):
    """The knowledge cannot answer what was asked of it, and this says what."""

    exit_code = ExitCode.STATE


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


def prose(file: str, lines: list[str]) -> list[bool]:
    """Which lines the file writes, rather than only shows.

    Two things are shown. A fenced sample: a `### Пример` inside one is not a
    record, and a quoted block inside one illustrates a block rather than being
    one. And an HTML comment, which is where the second version's templates
    keep their example record — all six of them — so a project that has started
    its knowledge and not filled it in carries a `key:` no renderer displays.
    Reading that as a record puts it in the index the driver encloses, and a
    block addressed to it is written inside the comment, where nobody sees it
    again. The second version knew this and had `commented()` for it.

    What is opened and never closed is refused rather than obeyed. A fence
    with no partner used to hide the rest of the file, and the rest of the file
    is where the headings and the blocks are: the index then said how many
    blocks were standing and was wrong, `close` refused an identifier that was
    there all along, and `free_id` could hand out a name already taken. A file
    that cannot be read honestly says so.
    """
    outside: list[bool] = []
    fenced = comment = 0  # the line it was opened on, counted from one
    for number, line in enumerate(lines, start=1):
        if comment:
            outside.append(False)
            comment = 0 if _COMMENT_CLOSE in line else comment
            continue
        if fenced:
            outside.append(False)
            fenced = 0 if _FENCE.match(line) else fenced
            continue
        if _FENCE.match(line):
            fenced = number
            outside.append(False)
            continue
        # What stands before `<!--` on its line is written; what follows it is
        # not. A comment closed on the line it opened hides only itself.
        opens = line.find(_COMMENT_OPEN)
        comment = number if opens >= 0 and _COMMENT_CLOSE not in line[opens:] else 0
        outside.append(True)
    if fenced or comment:
        what = "a code fence" if fenced else "a comment"
        raise KnowledgeError(
            "unreadable-knowledge",
            f"{file}: {what} was opened on line {fenced or comment} and never closed, "
            "so everything below it would be read as though it were not written",
        )
    return outside


#: A list item, and the last backticked segment of one. Anchored to the end for
#: the reason `parts.py` anchors its own: an unanchored search finds the
#: leftmost, which reads a description holding a `word` as though it were a
#: segment.
_ITEM = re.compile(r"^\s*[-*]\s+(?P<body>.*\S)\s*$")
_SEGMENT = re.compile(r"`(?P<inside>[^`]+)`\s*$")
_SEGMENT_PAIR = re.compile(r"^(?P<name>[a-z-]+):\s*(?P<value>[^·]+?)$")


@dataclass(frozen=True)
class Item:
    """One list item read as data: what it says, and what it says about itself."""

    body: str
    said: dict[str, str]
    line: int


def read_items(file: str, lines: list[str], vocabulary: frozenset[str]) -> list[Item]:
    """Every list item of one file, with its own segments peeled off the end.

    One peel and two files. The ledger of S8f and the manual actions of S8g are
    the same shape — a line of words with `key: value` segments after them — and
    a second spelling of one parser is one that will disagree with itself
    (finding 52 is what a second parser costs).

    `vocabulary` is what stops the peeling: a segment whose name is not in it is
    words, not data, and everything to its left stays words too. That is what
    keeps a part's `walked:` from turning a part of the product into a line of
    somebody else's file.
    """
    found: list[Item] = []
    written = prose(file, lines)
    for index, line in enumerate(lines):
        item = _ITEM.match(line) if written[index] else None
        if item is None:
            continue
        said: dict[str, str] = {}
        rest = item.group("body")
        while True:
            trimmed = rest.rstrip()
            segment = _SEGMENT.search(trimmed)
            if segment is None:
                break
            pair = _SEGMENT_PAIR.match(segment.group("inside").strip())
            if pair is None or pair.group("name") not in vocabulary:
                break
            said.setdefault(pair.group("name"), pair.group("value").strip())
            rest = trimmed[: segment.start()].rstrip().rstrip("·—-").rstrip()
        found.append(Item(body=rest.strip(), said=said, line=index))
    return found


def read_blocks(file: str, lines: list[str]) -> list[Block]:
    """Every block in one file, in the order they stand."""
    found: list[Block] = []
    written = prose(file, lines)
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
    written = prose(file, lines)
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
                anchor=_key_below(file, lines, index) or text,
                heading=text,
                level=len(heading.group("hashes")),
                line=index,
            )
        )
    return found


def _key_below(file: str, lines: list[str], index: int) -> str:
    """`key: money` on the first non-blank line under the heading, and nowhere else.

    A line that says `key:` and cannot be read is refused, not dropped. Dropping
    it addressed the record by its heading instead — a scheme of its own, for
    the whole project, arrived at without anybody choosing it.
    """
    for number in range(index + 1, min(index + 4, len(lines))):
        line = lines[number].strip()
        if not line:
            continue
        matched = _KEY_LINE.match(line)
        if matched is not None:
            return matched.group("key")
        if _KEY_STARTS.match(line):
            raise KnowledgeError(
                "unreadable-knowledge",
                f"{file} line {number + 1}: {line!r} names a key the kit cannot read, "
                "and a record whose key it cannot read has no address it can print",
            )
        return ""
    return ""


def section_end(lines: list[str], anchor: Anchor) -> int:
    """Where the anchor's section stops: the next heading of its level or higher."""
    written = prose(anchor.file, lines)
    for index in range(anchor.line + 1, len(lines)):
        heading = _HEADING.match(lines[index]) if written[index] else None
        if heading is not None and len(heading.group("hashes")) <= anchor.level:
            return index
    return len(lines)
