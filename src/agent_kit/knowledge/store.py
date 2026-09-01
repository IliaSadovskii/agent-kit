"""A project's knowledge, read and written by the program.

The owner's answer of 22 August settles the format: the second version's,
unchanged. Nothing here rewrites a line anybody wrote. What it adds is an
address — an identifier on the blocks this version writes — because the join
S6 exists for needs to say *which block answers which assumption*, and a date
with a branch cannot say it.

Reading is not an instruction: `index()` is what the driver encloses in the
design step's input, so a step that must address the knowledge is never sent to
go and find it.
"""

from __future__ import annotations

from pathlib import Path

from ..state.store import write_whole
from .debt import (
    BADLY, DEBT_SEED, LEDGER, LEDGER_HEAD, SECTIONS, Debt, debt_key, read_debt, render_debt,
)
from .parts import PARTS_HEADING, PRODUCT, Part, read_parts, render_part
from .format import (
    ASSUMED,
    prose,
    FRAME,
    Anchor,
    Block,
    KnowledgeError,
    identifier,
    read_anchors,
    read_blocks,
    render,
    section_end,
)

#: Where the second version left it, and where the third looks unless the
#: project says otherwise.
DEFAULT_DIR = "docs/knowledge"

#: How much of a block's first line the index carries.
GLIMPSE = 120

#: How far the derived identifier walks before giving up. It is a bound on a
#: loop and not a refusal anybody will meet: reaching it needs every one of
#: these names to stand in this project's knowledge under other runs.
SALTS = 64


class Knowledge:
    """One directory of markdown files, and the blocks standing in them."""

    def __init__(self, root: Path | str | None) -> None:
        #: None is a project that said out loud it is not being described. It
        #: answers every question the way an empty directory does, so nothing
        #: above has to ask twice — and, unlike a directory, it cannot be made
        #: true by somebody creating a folder the owner never declared.
        self.root = Path(root) if root is not None else None

    # --- reading ----------------------------------------------------------

    @property
    def declared(self) -> bool:
        return self.root is not None

    @property
    def exists(self) -> bool:
        return self.root is not None and self.root.is_dir()

    def files(self) -> list[Path]:
        return sorted(self.root.glob("*.md")) if self.exists and self.root else []

    def _lines(self, path: Path) -> list[str]:
        """A file that cannot be read is a named refusal, not a stack trace.

        The knowledge is the owner's, written by hand as often as by a program,
        and every other failure in the kit names a code.
        """
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as unreadable:
            raise KnowledgeError(
                "unreadable-knowledge", f"{path.name} не прочитался: {unreadable}"
            ) from unreadable

    def anchors(self) -> list[Anchor]:
        return [anchor for path in self.files() for anchor in read_anchors(path.name, self._lines(path))]

    def blocks(self) -> list[Block]:
        return [block for path in self.files() for block in read_blocks(path.name, self._lines(path))]

    def parts(self) -> list[Part]:
        """Every part of the product this project has written down.

        A key that two lines claim is refused rather than resolved to the first:
        the whole use of a key is that a second telling finds the same line
        again, and two lines answering to one key is a rewrite that lands
        wherever the reader happened to look.
        """
        found = [part for path in self.files() for part in read_parts(path.name, self._lines(path))]
        seen: dict[str, Part] = {}
        for part in found:
            held = seen.get(part.key)
            if held is not None:
                raise KnowledgeError(
                    "two-parts-one-key",
                    f"{part.key} называет две части этого продукта: {held.name!r} в {held.file} "
                    f"line {held.line + 1} and {part.name!r} in {part.file} line {part.line + 1}",
                )
            seen[part.key] = part
        return found

    def debt(self) -> list[Debt]:
        """Every line of the ledger, and only out of the ledger.

        A key two lines claim is refused rather than resolved to the first: the
        whole use of a key is that whoever comes back finds the same line again,
        and two lines answering to one key is a removal that takes whichever the
        reader happened to look at.
        """
        path = self.root / LEDGER if self.root else None
        if path is None or not path.is_file():
            return []
        found = read_debt(LEDGER, self._lines(path))
        seen: dict[str, Debt] = {}
        for line in found:
            held = seen.get(line.key)
            if held is not None:
                raise KnowledgeError(
                    "two-lines-one-key",
                    f"{line.key} называет две строки этого реестра: {held.what!r} в строке "
                    f"{held.line + 1} and {line.what!r} on line {line.line + 1}",
                )
            seen[line.key] = line
        return found

    def blocks_beside(self, part: Part) -> int:
        """How many blocks stand in the section this part's line is in.

        A part is a list item and a block is addressed to a heading, so a block
        is never *under* a part in the way a reader would mean. What is true and
        useful is the section: rewriting a line under which four runs have
        already written down what they assumed is a different act from
        rewriting one nothing has touched, and the person doing it should be
        told before they do it, not after.
        """
        path = self.root / part.file if self.root else None
        if path is None or not path.is_file():
            return 0
        lines = self._lines(path)
        above = [one for one in read_anchors(part.file, lines) if one.line < part.line]
        if not above:
            return 0
        anchor = above[-1]
        end = section_end(lines, anchor)
        return sum(1 for block in read_blocks(part.file, lines) if anchor.line < block.start < end)

    def part(self, key: str) -> Part:
        for part in self.parts():
            if part.key == key:
                return part
        raise KnowledgeError("no-such-part", f"ни одна часть этого продукта не несёт ключ {key!r}")

    @property
    def described(self) -> bool:
        """Whether anybody has written this project down at all.

        An addressable record is the measure — not a part with a mark. A project
        described the way the second version described one has 155 of them and
        no parts, and refusing that project would be the kit calling a
        description missing because it is not the shape this step writes.

        **The ledger does not count.** Its headings are records like any other,
        so an hour spent entirely on what is broken would otherwise leave a
        project the gate calls described and nobody has described — which is the
        exact defect this whole step exists against. It can be named here
        without naming anybody's language, because `debt.md` is the kit's own
        file name and not a word the project chose.
        """
        return any(anchor.file != LEDGER for anchor in self.anchors())

    def resolve(self, at: str) -> Anchor:
        """`file#anchor`, resolved against the file rather than trusted.

        An address nobody resolved is a block that lands wherever the writer
        guessed, and the point of an address is that somebody finds it again.
        """
        if "#" not in at:
            raise KnowledgeError("bad-address", f"{at!r} — не адрес: нужна форма file.md#anchor")
        name, _, wanted = at.partition("#")
        name, wanted = name.strip(), wanted.strip()
        path = self.root / name
        if not wanted:
            raise KnowledgeError("bad-address", f"{at!r} называет файл и ни одной записи в нём")
        # `files()` and not `is_file()`: a block written anywhere else could never
        # be found again — not by the index, not by `close`, not by `free_id`.
        if name not in {held.name for held in self.files()}:
            raise KnowledgeError(
                "no-such-file",
                f"{name} — не файл знания этого проекта: {', '.join(p.name for p in self.files()) or 'ни одного'}",
            )

        matching = [anchor for anchor in read_anchors(name, self._lines(path)) if anchor.anchor == wanted]
        if not matching:
            raise KnowledgeError("no-such-record", f"{at} называет запись, которой в {name} нет")
        if len(matching) > 1:
            raise KnowledgeError(
                "ambiguous-record", f"{at} называет записей в {name}: {len(matching)} — кит выбирать не станет"
            )
        return matching[0]

    def find(self, id: str) -> Block:
        for block in self.blocks():
            if block.id == id:
                return block
        raise KnowledgeError("no-such-block", f"ни один блок знания этого проекта не несёт идентификатор {id!r}")

    def free_id(self, slug: str, what: str, run: str, claimed: set[str] | None = None) -> str:
        """The derived identifier, unless it is already spoken for.

        Two things are true at once and they nearly cancel. A block this run
        wrote before is *ours*: the same slug and the same wording derive the
        same name again, which is what makes a second attempt a replacement
        rather than a duplicate. But two assumptions of one run worded the same
        derive the same name too, and treating the second as a replacement of
        the first deletes a block the run is supposed to be writing.

        `claimed` is what tells them apart: an identifier this execution has
        already handed out is taken, whoever holds it. The salt then walks on,
        deterministically, so the second sibling gets the same second name every
        time it is written.
        """
        claimed = claimed if claimed is not None else set()
        standing = {block.id: block for block in self.blocks() if block.id}
        for salt in range(SALTS):
            wanted = identifier(slug, what, salt)
            if wanted in claimed:
                continue
            held = standing.get(wanted)
            if held is None or held.run == run:
                return wanted
        raise KnowledgeError("no-free-identifier", f"все {SALTS} идентификаторов, выведенных для {what!r}, заняты")

    def free_key(self, what: str, claimed: set[str] | None = None) -> str:
        """The derived key of a line, unless it is already spoken for.

        The same two goals `free_id` holds apart, in the ledger's terms. A line
        with these words is *this complaint*: writing it again replaces it,
        which is what makes a second night idempotent rather than doubling. But
        two findings of one review worded the same are two findings, and reading
        the second as a replacement loses one — the shape of the blocker S6
        paid for. `claimed` is what tells them apart, and the salt walks on
        deterministically so the second gets the same second key every time.
        """
        claimed = claimed if claimed is not None else set()
        standing = {line.key: line for line in self.debt()}
        wanted_words = " ".join(what.split()).casefold()
        for salt in range(SALTS):
            wanted = identifier(DEBT_SEED, wanted_words, salt)
            if wanted in claimed:
                continue
            held = standing.get(wanted)
            if held is None or " ".join(held.what.split()).casefold() == wanted_words:
                return wanted
        raise KnowledgeError("no-free-identifier", f"все {SALTS} ключей, выведенных для {what!r}, заняты")

    # --- writing ----------------------------------------------------------

    def _root(self) -> Path:
        """The directory, once it is known to be declared. `_must_be_declared`
        is what refuses, by name; this is how the rest of a writer says so."""
        self._must_be_declared()
        return self.root  # type: ignore[return-value]

    def _must_be_declared(self) -> None:
        if self.root is None:
            raise KnowledgeError(
                "no-knowledge-declared",
                "объявление проекта говорит, что знания он не держит, значит и писать некуда",
            )

    def write(self, at: str, run: str, body: str, id: str, date: str, kind: str = ASSUMED) -> list[Path]:
        """Put the block at the end of the record it addresses, replacing its own.

        Its own, and only its own: a block with this identifier is removed
        wherever it stands before the new one is written, so a second attempt
        does not lay one beside the other and a changed address moves it.

        Every file it touched comes back, not only the destination — a move
        edits two, and the one it left had to reach the commit as well.
        """
        self._must_be_declared()
        anchor = self.resolve(at)  # before anything is removed: a bad address changes nothing
        touched = [self._remove(id, missing_ok=True)]

        path = self.root / anchor.file
        lines = self._lines(path)
        anchor = self.resolve(at)  # the removal may have moved it
        end = section_end(lines, anchor)
        while end > anchor.line + 1 and not lines[end - 1].strip():
            end -= 1

        block = render(kind, date, run, id, body)
        _write_lines(path, lines[:end] + [""] + block + lines[end:])
        return [held for held in dict.fromkeys([*touched, path]) if held is not None]

    def write_part(self, key: str, name: str, says: str, mark: str) -> Path:
        """One line: the part's own, replaced where it stands or laid beside the last.

        Replaced *by key*, which is why the key is written into the line rather
        than derived from the name every time: a second telling that renames a
        part must move its line, not lay a second one under a second name.

        Nothing else in the file is touched. A part the sitting never mentioned
        keeps the line somebody wrote by hand, down to its spacing.
        """
        self._must_be_declared()
        line = render_part(key, name, says, mark)
        standing = [part for part in self.parts() if part.key == key]
        if standing:
            held = standing[0]
            path = self.root / held.file
            lines = self._lines(path)
            lines[held.line] = line
            _write_lines(path, lines)
            return path

        every = self.parts()
        if every:
            path = self.root / every[-1].file
            lines = self._lines(path)
            at = every[-1].line + 1
            _write_lines(path, lines[:at] + [line] + lines[at:])
            return path

        # No parts anywhere: the file is made, or the heading is added to the
        # one that is already there. This is the only place the kit writes a
        # heading of its own, and it is the only place a project can have none.
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / PRODUCT
        lines = self._lines(path) if path.is_file() else ["# Продукт"]
        _write_lines(path, lines + ["", PARTS_HEADING, "", line])
        return path

    def write_debt(self, what: str, kind: str = BADLY, run: str = "", key: str = "") -> Path:
        """One line of the ledger, replaced where it stands and laid where it does not.

        A ledger line carries a key and no mark, and that is deliberate: a mark
        is what makes a list item a part of the product. The key may be given —
        the salt walk that keeps two findings worded alike apart happens where
        the findings are read, and the writer honours what it decided rather
        than deriving a second answer to the same question.
        """
        self._must_be_declared()
        root = self._root()
        key = key or debt_key(what)
        line = render_debt(key, what, run)

        root.mkdir(parents=True, exist_ok=True)
        path = root / LEDGER
        lines = self._lines(path) if path.is_file() else list(LEDGER_HEAD)

        for standing in read_debt(LEDGER, lines):
            if standing.key == key:
                lines[standing.line] = line
                _write_lines(path, lines)
                return path

        # Through `prose()`, the way the reading is: a heading shown inside a
        # fenced sample used to catch the write, and a line written there is one
        # `debt()` can never reach.
        heading = f"## {SECTIONS[kind]}"
        written = prose(LEDGER, lines)
        stands = [index for index, text in enumerate(lines) if written[index] and text.strip() == heading]
        if not stands:
            lines += ["", heading, "", line]
        else:
            at = stands[0] + 1
            while at < len(lines) and not (written[at] and lines[at].startswith("## ")):
                at += 1
            while at > 0 and not lines[at - 1].strip():
                at -= 1
            lines = lines[:at] + [line] + lines[at:]
        _write_lines(path, lines)
        return path

    def close_debt(self, key: str) -> Path:
        """Closing is deletion, here as everywhere: a ticked box is not a closing.

        Only the line, and nothing around it. The section it stood in stays,
        empty if it has to be — a heading the kit removed is a heading the owner
        would have to notice was gone.
        """
        self._must_be_declared()
        root = self._root()
        for standing in self.debt():
            if standing.key == key:
                path = root / LEDGER
                lines = self._lines(path)
                _write_lines(path, lines[: standing.line] + lines[standing.line + 1 :])
                return path
        raise KnowledgeError("no-such-debt", f"ни одна строка реестра этого проекта не несёт ключ {key!r}")

    def closable(self, id: str) -> Block:
        """The block, if it is one a run may close, and a named refusal if it is not.

        Only `assumed`. A `frame` is closed by whatever wrote it, when the work
        it framed is over — never by one of the features inside that work, which
        would be a feature deleting what the others are still being held to. A
        `found` belongs to the review that wrote it and a `stale` to whoever
        noticed. Asked here as well as in `close`, because `record` resolves
        everything before it edits anything: a run that closed one block and
        then refused the next leaves the owner's knowledge half-edited.
        """
        return self._closable(id, ASSUMED, wrote_it="")

    def closable_frame(self, id: str, wrote_it: str) -> Block:
        """A frame, and only one this same writer laid down.

        A frame is choreography: it says what several features must build alike
        while they are being built, and it stops being true when they are. So it
        has a closer, and the closer is whoever wrote it — the name in the
        block's own header. Anything else is one evening's work deleting
        another's.
        """
        return self._closable(id, FRAME, wrote_it=wrote_it)

    def _closable(self, id: str, kind: str, wrote_it: str) -> Block:
        block = self.find(id)
        if block.kind != kind:
            raise KnowledgeError(
                "not-closable-kind",
                f"{id} — блок вида {block.kind}, а здесь закрывают только {kind}: "
                f"{block.kind} is not this step's to delete",
            )
        if wrote_it and block.run != wrote_it:
            raise KnowledgeError(
                "not-its-block",
                f"{id} написал {block.run!r}, и {wrote_it!r} его не закрывает",
            )
        return block

    def close(self, id: str) -> Path:
        """Closing is deletion, and deletion needs an address. That is the identifier's second reason."""
        self.closable(id)
        return self._remove(id, missing_ok=False)

    def close_frame(self, id: str, wrote_it: str) -> Path:
        self.closable_frame(id, wrote_it)
        return self._remove(id, missing_ok=False)

    def _remove(self, id: str, missing_ok: bool) -> Path | None:
        try:
            block = self.find(id)
        except KnowledgeError:
            if missing_ok:
                return None
            raise

        path = self.root / block.file
        lines = self._lines(path)
        start, end = block.start, block.end
        # The blank line that separated it goes with it, or closing leaves a
        # hole. Which side it comes from depends on where the block stood: one
        # at the head of a file has nothing above it, one at the foot nothing
        # below, and taking from the wrong side leaves a file starting or
        # ending in white space it never had.
        while start > 0 and not lines[start - 1].strip() and end < len(lines) and not lines[end].strip():
            start -= 1
        while start == 0 and end < len(lines) and not lines[end].strip():
            end += 1
        while end >= len(lines) and start > 0 and not lines[start - 1].strip():
            start -= 1
        _write_lines(path, lines[:start] + lines[end:])
        return path

    # --- what the driver encloses -----------------------------------------

    def index(self) -> str:
        """Every file, every addressable record, every block standing — and no bodies.

        Not the knowledge itself: the real one is 7 380 lines, which is a window
        and not an enclosure. The files are on disk where the session stands,
        exactly like the code.
        """
        if not self.declared:
            return (
                "This project keeps no knowledge, and says so: `knowledge` is empty in its own\n"
                "declaration. Nothing can be addressed, and no assumption owes a block."
            )
        if not self.exists:
            return (
                f"This project keeps no knowledge: there is no {self.root.name}/ directory under it.\n"
                "Nothing can be addressed, and no assumption owes a block."
            )

        files = self.files()
        anchors = self.anchors()
        blocks = self.blocks()
        lines = [
            f"{len(files)} files, {len(anchors)} records, {len(blocks)} blocks standing.",
            "An address is `file#anchor`, and every one there is stands below.",
        ]
        for path in files:
            own = self._lines(path)
            lines += ["", f"## {path.name} — {_purpose(own)}"]
            width = max((len(f"{path.name}#{a.anchor}") for a in read_anchors(path.name, own)), default=0)
            for anchor in read_anchors(path.name, own):
                address = f"{path.name}#{anchor.anchor}"
                lines.append(f"   {address:<{width}}   {anchor.heading}")

        parts = self.parts()
        if parts:
            lines += [
                "",
                "## the parts of the product",
                "   Each is one line of the file it stands in. `walked` is a date the owner told it",
                "   themselves; `derived` is what was worked out from the code and never confirmed.",
            ]
            width = max(len(part.key) for part in parts)
            for part in parts:
                lines.append(
                    f"   {part.key:<{width}}  {part.mark:<16}  {part.file}  {part.name}"
                    + (f" — {part.says[:GLIMPSE]}" if part.says else "")
                )

        standing_debt = self.debt()
        if standing_debt:
            lines += [
                "",
                "## the ledger — built, and working badly",
                "   Each is one line of " + LEDGER + ". `run` is the night whose review found it;",
                "   a line with none was said by the owner. The work that answers a line takes it away.",
            ]
            width = max(len(line.key) for line in standing_debt)
            run = max((len(line.run) for line in standing_debt), default=0)
            for line in standing_debt:
                lines.append(f"   {line.key:<{width}}  {line.run:<{run}}  {line.what[:GLIMPSE]}")

        lines += ["", "## the blocks standing now"]
        # The run is a column and not part of the glimpse: it is the only thing
        # that identifies a block the second version wrote, which has no
        # identifier of its own.
        run = max((len(block.run) for block in blocks), default=0)
        for block in blocks:
            lines.append(
                f"   {block.id or '—':<6}  {block.kind:<8} {block.date}  {block.run:<{run}}  "
                f"{block.file}  {block.first_line[:GLIMPSE]}"
            )
        if any(not block.id for block in blocks):
            lines.append(
                "A block with no identifier was written before the kit could address one; it cannot be closed."
            )
        return "\n".join(lines)


def _purpose(lines: list[str]) -> str:
    """What the file says it is for: the first sentence of its own header comment."""
    for line in lines:
        text = line.strip()
        if not text or text.startswith(("<!--", "#")):
            continue
        return text
    return "no header comment says what this file is for"


def _write_lines(path: Path, lines: list[str]) -> None:
    """The file as it was, plus or minus a block.

    Nothing is trimmed: a round trip over the real knowledge used to give the
    owner a diff with a blank line removed at the end of a file the kit never
    meant to touch.
    """
    write_whole(path, "\n".join(lines) + "\n")
