"""S8g — the work a night cannot do for itself, and the proof that closes it.

Place a secret, apply a migration, create an account, point a domain. The
second version kept these in a run file that is git-ignored and dies with the
machine, and its only reader composed them out of a pull request body nobody
opens again after the merge. So they live in a file of the repository, shaped
like the ledger of S8f — a line of words with `key: value` segments after them,
read by the same parser.

**Not in the knowledge directory, and that is the one place this departs from
the ledger.** A project may say out loud that nobody describes it
(`knowledge = ""`), and then it has no knowledge directory and never gets one
from a night. The ledger is silent for such a project on purpose — *works
badly* is a sentence about a product somebody is describing. A secret nobody
placed is not: it is the most urgent thing the kit can hand over, and the
project the kit knows least about is exactly the one whose owner most needs
telling. `.agent-kit/v3/` is repository content — `project.toml` lives there
and travels with a clone — while `runs/`, `batches/`, `audits/` and
`sittings/` keep the `*` of their own beside their paperwork.

**The writer is the evening, never the feature.** Measured for the ledger and
true here for the same reason: two features of one batch branch from one base
and append to one insertion point, and that is two branches that will not
merge, 200 of 200. The feature names its actions in `record`; the evening lays
them once, in the owner's own checkout, when there is nothing left to build.

**The closer is the proof.** `agent-kit manual check` runs it, and a command
that comes back zero takes its own line away — nobody has to remember to tick
anything, and *done* is not a claim anybody makes about their own work. Where
no check can be written, because it truly needs a person holding a phone, the
line stays and says so in its own words. Its last closer is the owner deleting
it by hand, which they can do because the file is in git and reads as prose.

**This file's content is executed**, which `[commands]` and `[verification]`
already are. It is repository content: whoever may write to it may already run
what the project declares.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ExitCode, KitError
from .knowledge.format import identifier, read_items
from .logs import get_logger
from .paths import project_paths
from .shell import ran_alone
from .verification.answers import proves_nothing

log = get_logger("manual")

#: The file. The kit's own name, beside the declaration and inside the history.
MANUAL = "manual.md"

#: What a segment of a line may be called. Anything else stops the peeling.
SEGMENTS = frozenset({"key", "proof", "by-hand"})

#: The two things a line may say about itself, and it says exactly one.
PROOF = "proof"
BY_HAND = "by-hand"

#: What a key is derived from, beside the words. One place, because `free_key`
#: walks the same derivation with a salt.
MANUAL_SEED = "manual"

#: How far the derived key walks before giving up, as a block's identifier does.
SALTS = 64

#: How long one proof is given. Not the project's `command_timeout`: that is
#: for its test suite, minutes of docker, and this is a person standing at a
#: terminal — six stuck lines would be six of those in a row.
PROOF_TIMEOUT = 30

SEPARATOR = " · "

#: What the file is made with. Written once, when it is created; a file that
#: already stands keeps the header it has, because no line anybody wrote is
#: rewritten. Nothing here promises a check no program performs.
MANUAL_HEAD = [
    "# Сделать руками",
    "",
    "Что ночь сделать не может: положить секрет, применить миграцию, завести",
    "аккаунт, направить домен. Строки кладёт вечер партии из того, что назвал",
    "замысел фичи. Строку с `proof:` снимает сам кит — `agent-kit manual check`",
    "запускает команду, и строка уходит, когда та возвращает ноль. Строку с",
    "`by-hand:` не снимет никто, кроме вас: удалите её тем же коммитом, что",
    "делает работу.",
]

#: What a value may not hold, because the reader would not read it back: the
#: backtick that ends a segment, the separator between segments, and a line
#: break, which would make a line the parser cannot see the end of.
CANNOT_HOLD = ("`", "·", "\n", "\r")


class ManualError(KitError):
    """The file cannot answer what was asked of it, and this says what."""

    exit_code = ExitCode.STATE


class ManualRefused(KitError):
    """An action a session named cannot become a line.

    Its own class because its two callers turn it into two different events —
    an attempt refused at the design, a step failed at `record` — and a code
    that meant both would be a code that means one thing to nobody. The same
    shape `UnprovedKind` has, for the same reason.
    """

    exit_code = ExitCode.STATE


@dataclass(frozen=True)
class Action:
    """One line of the file, and where it stands."""

    key: str
    what: str
    #: The command that comes back zero once this has been done. Empty where
    #: no check can be written.
    proof: str
    #: Why no command could prove it. Empty where one can.
    by_hand: str
    line: int

    @property
    def provable(self) -> bool:
        return bool(self.proof)


def manual_key(what: str) -> str:
    """The key of a line, from its own words.

    Flattened for case and spacing exactly as a ledger key is: *положить
    STRIPE_KEY* said twice in two capitalisations is one chore, not two.
    """
    return identifier(MANUAL_SEED, " ".join(what.split()).casefold())


def read_actions(file: str, lines: list[str]) -> list[Action]:
    """Every line of the file, in the order they stand."""
    return [
        Action(
            key=item.said["key"],
            what=item.body,
            proof=item.said.get(PROOF, ""),
            by_hand=item.said.get(BY_HAND, ""),
            line=item.line,
        )
        for item in read_items(file, lines, SEGMENTS)
        if "key" in item.said and item.body
    ]


def render_action(key: str, what: str, proof: str = "", by_hand: str = "") -> str:
    """One line, and one line only.

    A line that wrapped would need a parser that knows where a list item ends.
    What is long here is a chore that wants to be two chores.
    """
    said = f"{SEPARATOR}`{PROOF}: {proof}`" if proof.strip() else f"{SEPARATOR}`{BY_HAND}: {by_hand}`"
    return f"- {' '.join(what.split())}{SEPARATOR}`key: {key}`{said}"


def cannot_be_written(value: str) -> str:
    """The first character of a value the reader would not read back, if there is one."""
    return next((one for one in CANNOT_HOLD if one in value), "")


class Manual:
    """One file of chores, and the actions standing in it."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    @property
    def path(self) -> Path:
        return project_paths(self.root).kit_dir / MANUAL

    # --- reading ------------------------------------------------------------

    def actions(self) -> list[Action]:
        """Every action standing, and a key two lines claim is refused.

        The whole use of a key is that whoever comes back finds the same line
        again, and two lines answering to one key is a removal that takes
        whichever the reader happened to look at.
        """
        path = self.path
        if not path.is_file():
            return []
        found = self._read(self._lines(path))
        seen: dict[str, Action] = {}
        for action in found:
            held = seen.get(action.key)
            if held is not None:
                raise ManualError(
                    "two-actions-one-key",
                    f"{action.key} names two actions of this project: {held.what!r} on line "
                    f"{held.line + 1} and {action.what!r} on line {action.line + 1}",
                )
            seen[action.key] = action
        return found

    def _lines(self, path: Path) -> list[str]:
        """A file that cannot be read is a named refusal, not a stack trace."""
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as unreadable:
            raise ManualError("unreadable-manual", f"{path.name} could not be read: {unreadable}") from unreadable

    def _read(self, lines: list[str]) -> list[Action]:
        """The reader's own refusal, in this file's vocabulary.

        A fence opened and never closed hides everything below it, and the
        knowledge says so by its own code. Here it is the same fact about a
        different file, so it is named for this one: a judge reads a code, and
        two files answering with one code cannot be told apart.
        """
        from .knowledge.format import KnowledgeError

        try:
            return read_actions(MANUAL, lines)
        except KnowledgeError as unreadable:
            raise ManualError("unreadable-manual", unreadable.detail) from unreadable

    def free_key(self, what: str, claimed: set[str] | None = None) -> str:
        """The derived key, unless it is already spoken for.

        The two goals `free_key` holds apart for the ledger, in this file's
        terms. A line with these words is *this chore*: naming it again
        replaces it, which is what makes a second night idempotent rather than
        doubling. Two chores of one feature worded the same are two chores, and
        `claimed` is what tells them apart.
        """
        claimed = claimed if claimed is not None else set()
        standing = {action.key: action for action in self.actions()}
        wanted_words = " ".join(what.split()).casefold()
        for salt in range(SALTS):
            wanted = identifier(MANUAL_SEED, wanted_words, salt)
            if wanted in claimed:
                continue
            held = standing.get(wanted)
            if held is None or " ".join(held.what.split()).casefold() == wanted_words:
                return wanted
        raise ManualError("no-free-identifier", f"{SALTS} keys derived for {what!r} are all taken")

    # --- writing ------------------------------------------------------------

    def write(self, what: str, proof: str = "", by_hand: str = "", key: str = "") -> Path:
        """One line, replaced where it stands and laid where it does not.

        A file the repository ignores is refused rather than written. The kit
        of S0 to S3 wrote `.agent-kit/v3/.gitignore` = `*`, and only
        `agent-kit init` clears it away: a project set up by that kit and never
        re-initialised would swallow this file in silence, which is the exact
        defect the second version was measured on.
        """
        ignored = self._ignored()
        if ignored:
            raise ManualError(
                "manual-ignored",
                f"{self.path} is ignored by {ignored}, and a chore in a file nobody commits dies "
                "with this machine — which is what this file exists against",
                hint="agent-kit init",
            )
        key = key or manual_key(what)
        line = render_action(key, what, proof, by_hand)

        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = self._lines(path) if path.is_file() else list(MANUAL_HEAD)

        for standing in self._read(lines):
            if standing.key == key:
                lines[standing.line] = line
                _write_lines(path, lines)
                return path

        while lines and not lines[-1].strip():
            lines.pop()
        _write_lines(path, lines + ["", line])
        return path

    def close(self, key: str) -> Path:
        """Closing is deletion, here as everywhere: a ticked box is not a closing."""
        for standing in self.actions():
            if standing.key == key:
                path = self.path
                lines = self._lines(path)
                _write_lines(path, lines[: standing.line] + lines[standing.line + 1 :])
                return path
        raise ManualError("no-such-action", f"no line of this project carries the key {key!r}")

    def _ignored(self) -> str:
        """What ignores this file, or nothing. A repository is not required."""
        try:
            asked = subprocess.run(
                ["git", "check-ignore", "-v", "--no-index", str(self.path)],
                cwd=self.root, capture_output=True, text=True, timeout=20,
            )
        except (OSError, subprocess.SubprocessError):  # pragma: no cover - no git here
            return ""
        if asked.returncode != 0:
            return ""
        said = (asked.stdout or "").strip().splitlines()
        return said[0].split("\t")[0] if said else ".gitignore"


def _write_lines(path: Path, lines: list[str]) -> None:
    from .state.store import write_whole

    write_whole(path, "\n".join(lines).rstrip("\n") + "\n")


# --- what a design owes, asked by two callers -------------------------------


def actions_of(design: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in (design.get("manual") or []) if isinstance(row, dict)]


def said(row: dict[str, Any], name: str) -> str:
    return str(row.get(name) or "").strip()


def refuse_unless_each_action_is_answered(design: dict[str, Any]) -> None:
    """Every action a design named, against what a line can hold.

    Asked twice, and the two are two events: at the design's own contract, so a
    session mends it in the attempt it is already in, and at `record`, which is
    what survives a run assembled from other steps. A design that names nothing
    owes nothing, and that is every design written before this existed.

    The values are held to being readable back, which the ledger never had to
    be: its values are a derived key and a slug, and these are a shell line and
    the owner's own prose. A backtick, a `·` or a line break makes a line the
    reader cannot read — the join would count it, the proof would never run,
    the rung would never stand, and nobody would have refused anything.
    """
    for row in actions_of(design):
        what = said(row, "what")
        proof, by_hand = said(row, "proof"), said(row, "by_hand")
        if not what:
            raise ManualRefused(
                "action-with-no-words",
                "an action with nothing said in it is not an action: the line would name a key "
                "and no work",
            )
        for name, value in (("what", what), ("proof", proof), ("by_hand", by_hand)):
            held = cannot_be_written(value)
            if held:
                raise ManualRefused(
                    f"action-that-cannot-be-written: {name}",
                    f"{what!r} carries {held!r} in its {name}, and a line holding it is one the "
                    "kit cannot read back — the chore would stand in the file and reach nobody",
                )
        if proof and by_hand:
            raise ManualRefused(
                "action-proved-and-by-hand",
                f"{what!r} carries both a command and a reason no command can prove it, and a "
                "record that says both has decided neither",
            )
        if not proof and not by_hand:
            raise ManualRefused(
                "action-unproved",
                f"{what!r} says neither how it will be proved done nor why no command can prove "
                "it; a chore nobody can close is what this file exists against",
            )
        empty = proves_nothing(proof)
        if empty:
            raise ManualRefused(
                "proof-that-proves-nothing",
                f"{what!r} is proved by {proof!r}, and {empty!r} exits zero whatever is wrong: it "
                "would take its own line away the first time anybody looked",
            )


# --- the proofs, run by the one command that runs them ----------------------


@dataclass
class Checked:
    """What one walk of the file found, by key."""

    done: list[str] = field(default_factory=list)
    stands: list[tuple[str, str]] = field(default_factory=list)
    by_hand: list[tuple[str, str]] = field(default_factory=list)
    proves_nothing: list[str] = field(default_factory=list)

    @property
    def standing(self) -> int:
        return len(self.stands) + len(self.by_hand) + len(self.proves_nothing)


def check(root: Path | str, timeout: int = PROOF_TIMEOUT) -> Checked:
    """Every line, and what running its proof did to it.

    The whole file, every time: a red proof does not stop the walk, because
    this is a report and not a `verify` — the next line's chore has nothing to
    do with this one's, and stopping would hide it.

    Nothing here is run by the door, and nothing by a night. A door that acts is
    not a door; and a night would be running commands in a working copy it does
    not hold, which is the one thing the kit refuses by name everywhere else.
    """
    held = Manual(root)
    checked = Checked()
    for action in held.actions():
        if action.by_hand:
            checked.by_hand.append((action.key, action.by_hand))
            continue
        empty = proves_nothing(action.proof)
        if empty:
            # A line somebody wrote by hand: the design's own answer was held to
            # this before it was ever written. Not run and never closed.
            checked.proves_nothing.append(action.key)
            continue
        log.info("manual: %s — %s", action.key, action.proof)
        code, output = ran_alone(action.proof, Path(root), timeout)
        if code == 0:
            held.close(action.key)
            checked.done.append(action.key)
            continue
        checked.stands.append((action.key, output))
    return checked
