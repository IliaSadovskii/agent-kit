"""What a measurement stood on, and how a later step checks it is still that.

`verify` runs the project's own commands over a working copy and records that
they came back green. The claim is about that working copy and no other, and
until this the run held nothing that said which one it was: a build that changed
six files and named four delivered a branch missing two of them, and every
artefact of the run still said `passed: true`.

So verify writes down two things — the commit the tree stood on, and every
change the tree held that the commit did not, by content as well as by name.

What `deliver` does with it is two different things, because the two directions
are not equally true:

- a commit carrying what the commands never ran over is delivery of unmeasured
  work, and it is refused;
- a change the commands ran over and the commit leaves behind is *not*
  necessarily wrong. A working copy legitimately holds what this feature is not
  about — an `agent-kit init --force` nobody committed, a suite the owner
  repaired by hand before carrying the run on — and both are the kit's own
  ordinary night. Refusing there costs a night to save a sentence, so it is
  written into the pull request instead, where the owner sees what the branch
  does not carry.

The tree also moves once between the two steps by design: `record` writes the
project's knowledge into it after the commands have run. What it wrote it
names, and what it named delivery lets through.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ..providers.base import ExecutorFailed

#: git in a working copy is local work; one that has taken this long has hung.
TIMEOUT = 120

#: Enough of a digest to tell two versions of a file apart. The whole of it
#: would make the record unreadable and prove nothing more.
DIGEST = 16

#: What porcelain calls a file git has never been told about.
UNTRACKED = "??"

#: The digest of a path that is not there — a file the work deleted.
GONE = "-"


@dataclass(frozen=True)
class Change:
    """One difference between the tree the commands ran over and its commit."""

    code: str
    digest: str

    @property
    def tracked(self) -> bool:
        """False for a file git has never been told about.

        Untracked is not measured work: it is a `.env`, a log, a half-written
        experiment. Delivery commits only what the build named, so a stray file
        left beside the work must not read as work left out of the commit.
        """
        return self.code != UNTRACKED


def stood_on(where: Path | str) -> tuple[str | None, list[str]]:
    """The commit this working copy is on, and every change it holds beside it.

    Asked after the commands have run rather than before: what delivery will
    commit is the tree they left, and a suite that rewrites a file it tests is
    the project's business rather than a discrepancy for the kit to find.

    A tree that is no repository proves nothing and says so. The commands still
    ran, and what they printed is still true; there is simply no commit to bind
    the result to, and delivery then has nothing to compare.
    """
    root = Path(where)
    head = _git(root, "rev-parse", "HEAD")
    if head is None or not head.strip():
        return None, []
    printed = _git(root, "status", "--porcelain=v1", "--untracked-files=all", "-z")
    if printed is None:
        return None, []
    return head.strip(), [f"{code} {_digest(root / path)} {path}" for code, path in _porcelain(printed)]


def measured(verify: dict) -> tuple[str, dict[str, Change]] | None:
    """What verify wrote down, or nothing when it wrote nothing.

    Nothing is the ordinary case for a run whose steps hold no `verify` at all,
    and for one an older kit started. No claim was made about a tree, so there
    is none to hold the commit to.
    """
    at = str(verify.get("proved_at") or "").strip()
    if not at:
        return None
    held: dict[str, Change] = {}
    for line in verify.get("proved_over") or []:
        code, _, rest = str(line).strip().partition(" ")
        digest, _, path = rest.partition(" ")
        if path:
            held[path] = Change(code=code, digest=digest)
    return at, held


def refuse_unless_the_tree_is_where_it_was_proved(where: Path, verify: dict) -> None:
    """The commit the commands ran on, and the one this working copy is on now.

    Asked before anything touches the repository. A tree that has moved under
    the run — somebody committed in it, a branch was checked out — carries code
    nobody measured, and every later artefact would say the suite was green
    over it.
    """
    seen = measured(verify)
    if seen is None:
        return
    at, _ = seen
    head = (_git(Path(where), "rev-parse", "HEAD") or "").strip()
    if head and head != at:
        raise ExecutorFailed(
            "tree-moved-since-verify",
            f"the project's commands ran over {at[:12]} and this working copy stands on {head[:12]}; "
            "what was measured is not what would be delivered",
            retryable=False,
        )


def refuse_unless_the_commit_is_what_was_proved(
    where: Path, verify: dict, staged: set[str], written: list[str]
) -> None:
    """The index about to be committed, against the tree the commands ran over.

    Two ways a file in it is work nobody measured — the commands ran before it
    existed, or it has been written over since they ran — and the refusal names
    which files and which of the two.

    What `record` wrote is neither: it is named by the program that wrote it,
    and it reached the tree after the commands by design.
    """
    seen = measured(verify)
    if seen is None:
        return
    _, held = seen
    knowledge = set(written or [])

    never_ran_over = []
    for name in sorted(staged):
        if name in knowledge:
            continue
        change = held.get(name)
        if change is None:
            never_ran_over.append(f"{name} — the tree they ran over did not hold it")
        elif change.digest != _digest(Path(where) / name):
            never_ran_over.append(f"{name} — it has been written over since")
    if never_ran_over:
        raise ExecutorFailed(
            "not-what-was-verified",
            "this commit carries what the project's commands never ran over: "
            + "; ".join(never_ran_over),
            retryable=False,
        )


def left_behind(verify: dict, delivered: list[str]) -> list[str]:
    """Tracked changes the commands ran over that the commit will not carry.

    Not a refusal: a working copy holds what this feature is not about, and a
    night is worth more than the sentence a refusal would save. It goes into the
    pull request, where the six files the build changed and the four it named
    are finally something the owner can see.
    """
    seen = measured(verify)
    if seen is None:
        return []
    _, held = seen
    named = set(delivered or [])
    return sorted(
        name for name, change in held.items() if change.tracked and name not in named
    )


# --- git, and the tree it describes ------------------------------------------


def _porcelain(printed: str) -> Iterator[tuple[str, str]]:
    """Porcelain v1, read as records rather than as lines.

    `-z` and not a plain listing: git quotes a path with a byte over 127 in it,
    and a project whose files are named in Russian would come back under
    another spelling. A rename carries its old name in the record after it,
    which is a path this has no claim to make about.
    """
    entries = [entry for entry in printed.split("\0") if entry]
    while entries:
        entry = entries.pop(0)
        code, path = entry[:2].strip(), entry[3:]
        if code[:1] in ("R", "C") and entries:
            entries.pop(0)
        if code and path:
            yield code, path


def _digest(path: Path) -> str:
    """The content itself, so that a file written over keeps its name and loses this."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:DIGEST]
    except OSError:
        return GONE


def _git(root: Path, *argv: str) -> str | None:
    """git, asked a question it may have no answer to.

    None where there is no answer — no repository, no commit yet, a git that
    could not be run at all. A measurement that cannot say what it stood on is
    a measurement nothing is held to; refusing here would stop a run over what
    is not a claim about the code.
    """
    try:
        done = subprocess.run(
            ["git", *argv],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None
