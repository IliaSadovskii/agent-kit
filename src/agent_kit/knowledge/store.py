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

from ..errors import ExitCode, KitError
from ..state.store import write_whole
from .format import (
    ASSUMED,
    Anchor,
    Block,
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


class KnowledgeError(KitError):
    """The knowledge cannot answer what was asked of it, and this says what."""

    exit_code = ExitCode.STATE


class Knowledge:
    """One directory of markdown files, and the blocks standing in them."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    # --- reading ----------------------------------------------------------

    @property
    def exists(self) -> bool:
        return self.root.is_dir()

    def files(self) -> list[Path]:
        return sorted(self.root.glob("*.md")) if self.exists else []

    def _lines(self, path: Path) -> list[str]:
        """A file that cannot be read is a named refusal, not a stack trace.

        The knowledge is the owner's, written by hand as often as by a program,
        and every other failure in the kit names a code.
        """
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as unreadable:
            raise KnowledgeError(
                "unreadable-knowledge", f"{path.name} could not be read: {unreadable}"
            ) from unreadable

    def anchors(self) -> list[Anchor]:
        return [anchor for path in self.files() for anchor in read_anchors(path.name, self._lines(path))]

    def blocks(self) -> list[Block]:
        return [block for path in self.files() for block in read_blocks(path.name, self._lines(path))]

    def resolve(self, at: str) -> Anchor:
        """`file#anchor`, resolved against the file rather than trusted.

        An address nobody resolved is a block that lands wherever the writer
        guessed, and the point of an address is that somebody finds it again.
        """
        if "#" not in at:
            raise KnowledgeError("bad-address", f"{at!r} is not an address: it wants the shape file.md#anchor")
        name, _, wanted = at.partition("#")
        name, wanted = name.strip(), wanted.strip()
        path = self.root / name
        if not wanted:
            raise KnowledgeError("bad-address", f"{at!r} names a file and no record in it")
        if "/" in name or name in ("", ".", "..") or not path.is_file():
            raise KnowledgeError(
                "no-such-file",
                f"{name} is not a file of this project's knowledge: {', '.join(p.name for p in self.files()) or 'none'}",
            )

        matching = [anchor for anchor in read_anchors(name, self._lines(path)) if anchor.anchor == wanted]
        if not matching:
            raise KnowledgeError("no-such-record", f"{at} names no record {name} holds")
        if len(matching) > 1:
            raise KnowledgeError(
                "ambiguous-record", f"{at} names {len(matching)} records of {name}, and the kit will not choose"
            )
        return matching[0]

    def find(self, id: str) -> Block:
        for block in self.blocks():
            if block.id == id:
                return block
        raise KnowledgeError("no-such-block", f"no block of this project's knowledge carries the identifier {id!r}")

    def free_id(self, slug: str, what: str, run: str) -> str:
        """The derived identifier, unless it is already somebody else's.

        Ours is one this run wrote before — the same slug and the same
        assumption produce it again, which is what makes a second attempt a
        replacement rather than a duplicate. Anybody else's is a collision, and
        it is stepped over rather than overwritten.
        """
        standing = {block.id: block for block in self.blocks() if block.id}
        for salt in range(64):
            wanted = identifier(slug, what, salt)
            held = standing.get(wanted)
            if held is None or held.run == run:
                return wanted
        raise KnowledgeError("no-free-identifier", f"64 identifiers derived for {what!r} are all taken")

    # --- writing ----------------------------------------------------------

    def write(self, at: str, run: str, body: str, id: str, date: str, kind: str = ASSUMED) -> Path:
        """Put the block at the end of the record it addresses, replacing its own.

        Its own, and only its own: a block with this identifier is removed
        wherever it stands before the new one is written, so a second attempt
        does not lay one beside the other and a changed address moves it.
        """
        anchor = self.resolve(at)  # before anything is removed: a bad address changes nothing
        self._remove(id, missing_ok=True)

        path = self.root / anchor.file
        lines = self._lines(path)
        anchor = self.resolve(at)  # the removal may have moved it
        end = section_end(lines, anchor)
        while end > anchor.line + 1 and not lines[end - 1].strip():
            end -= 1

        block = render(kind, date, run, id, body)
        _write_lines(path, lines[:end] + [""] + block + lines[end:])
        return path

    def close(self, id: str) -> Path:
        """Closing is deletion, and deletion needs an address. That is the identifier's second reason."""
        return self._remove(id, missing_ok=False)

    def _remove(self, id: str, missing_ok: bool) -> Path:
        try:
            block = self.find(id)
        except KnowledgeError:
            if missing_ok:
                return self.root
            raise

        path = self.root / block.file
        lines = self._lines(path)
        start, end = block.start, block.end
        # One blank line above it goes too, or closing leaves a hole where the
        # block was and every later block drifts down by one.
        while start > 0 and not lines[start - 1].strip() and end < len(lines) and not lines[end].strip():
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
    while lines and not lines[-1].strip():
        lines.pop()
    write_whole(path, "\n".join(lines) + "\n")
