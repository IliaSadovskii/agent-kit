"""What is true on this machine right now: slots, limits, the queue, stop requests.

One SQLite file, and every driver reads and writes it directly. The daemon is
not in this path on purpose — a ceiling that only holds while a process is alive
is a ceiling that is off at 02:00, which is the hour it exists for. The daemon
serves the page and reaps what died; the truth is here, and it is transactional
across processes whether anything is running or not.

Nothing in this file is a setting. What this installation *chose* — how many
sessions, which account, which port — is `config.toml`, and it is passed in.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from ..errors import ProviderError
from .linux import boot_id, is_alive

SCHEMA_VERSION = 3

#: How long a lease outlives the moment it was taken, when nobody says
#: otherwise. Only ever a backstop for a pid that was reused: what really says
#: a lease is dead is that its driver is not there any more.
DEFAULT_TTL = 3 * 60 * 60

#: A run is held for as long as its driver runs it, which is a night at most.
RUN_TTL = 24 * 60 * 60

#: What a limit costs when the provider said it was limited and named no hour.
#: A guess, and the row says so rather than passing it off as something read.
GUESSED_LIMIT = 60 * 60

#: Сколько имён подряд пробуется для вопроса, прежде чем это перестаёт быть
#: совпадением и становится дефектом.
_NAMES_TRIED = 16

SESSION = "session"
RUN = "run"
#: The process driving a batch. It runs no session and holds no slot: what it
#: holds is the batch's own file, so that two `batch go` on one batch is
#: refused by name rather than becoming two writers.
BATCH = "batch"
#: Whoever is reading the owner's channel right now. `getUpdates` is
#: single-consumer: two processes reading at once steal each other's answers.
CHANNEL = "channel"

#: Who is building in a working copy right now. A run with a worktree of its
#: own holds that and nothing else; a run started by hand has no worktree, so it
#: builds in the project's own checkout and holds *that*. Two runs in one
#: checkout is two sessions editing one file, which is what S8 gave the batch a
#: tree per child to prevent and left standing everywhere else.
CHECKOUT = "checkout"

#: What a request against a batch is called when it names a feature.
SKIP = "skip"

#: How long the reader holds the channel. Short, because it is one poll: a
#: driver that dies mid-poll must not keep everybody else out for three hours.
READER_TTL = 60

#: How long a question outlives its own deadline before it is swept. The driver
#: reads once more after the deadline before it takes the default, and sweeping
#: in that gap is how an answer that did arrive is thrown away.
ASK_GRACE = 60 * 60

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leases (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL,
    account    TEXT NOT NULL,
    provider   TEXT NOT NULL,
    project    TEXT NOT NULL,
    slug       TEXT NOT NULL,
    step       TEXT NOT NULL,
    pid        INTEGER NOT NULL,
    boot       TEXT NOT NULL,
    taken_at   TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS waiters (
    id       INTEGER PRIMARY KEY,
    account  TEXT NOT NULL,
    provider TEXT NOT NULL,
    project  TEXT NOT NULL,
    slug     TEXT NOT NULL,
    step     TEXT NOT NULL,
    pid      INTEGER NOT NULL,
    boot     TEXT NOT NULL,
    asked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS limits (
    account TEXT PRIMARY KEY,
    until   TEXT NOT NULL,
    said    TEXT NOT NULL DEFAULT '',
    said_at TEXT NOT NULL,
    said_by TEXT NOT NULL,
    guessed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS asks (
    id          TEXT PRIMARY KEY,
    project     TEXT NOT NULL,
    slug        TEXT NOT NULL,
    step        TEXT NOT NULL,
    question    TEXT NOT NULL,
    "default"   TEXT NOT NULL,
    message     TEXT NOT NULL DEFAULT '',
    asked_at    TEXT NOT NULL,
    until       TEXT NOT NULL,
    answer      TEXT
);
CREATE TABLE IF NOT EXISTS channel (
    what  TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
    id       INTEGER PRIMARY KEY,
    project  TEXT NOT NULL,
    slug     TEXT NOT NULL,
    what     TEXT NOT NULL,
    reason   TEXT NOT NULL,
    asked_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).replace(microsecond=0).isoformat()


def moment(said: str | None) -> str | None:
    """A time this file can compare, out of whatever a provider called it.

    Times here are compared as strings, which only works while every one of
    them is the same shape and the same zone. What a CLI prints is a phrase a
    person reads — `5pm (America/Los_Angeles)`, `17:00`, an offset three hours
    from here — and storing that as it came made `5pm` sort above every date
    there will ever be. That is an account limited for good.

    So: read it, put it in UTC, or say plainly that it could not be read.
    """
    if not isinstance(said, str) or not said.strip():
        return None
    text = said.strip().replace("Z", "+00:00")
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return None
    if when.tzinfo is None:
        # No zone said is this machine's zone, which is where the run is.
        when = when.astimezone()
    return when.astimezone(timezone.utc).replace(microsecond=0).isoformat()


# --- what is asked, and what comes back ------------------------------------


@dataclass(frozen=True)
class Want:
    """One session's worth of machine, asked for by the driver that will run it."""

    account: str
    provider: str
    project: str
    slug: str
    step: str = ""
    ttl: int = DEFAULT_TTL
    pid: int = field(default_factory=os.getpid)
    boot: str = field(default_factory=boot_id)


@dataclass(frozen=True)
class Ceilings:
    """What this installation chose, read from `config.toml` and passed in."""

    max_sessions: int = 4
    per_provider: dict[str, int] = field(default_factory=dict)

    def for_provider(self, name: str) -> int | None:
        return self.per_provider.get(name)


@dataclass(frozen=True)
class Lease:
    id: int
    kind: str
    account: str
    provider: str
    project: str
    slug: str
    step: str
    pid: int
    boot: str
    taken_at: str
    expires_at: str

    granted = True


@dataclass(frozen=True)
class Busy:
    """The machine said no, by name.

    What the code becomes at the surface is the caller's: `_slot` raises it as a
    provider failure (4, an agent cannot be run right now), `_hold` as a state
    one (3, a run's state refuses what was asked). The name is the same either
    way, which is what a script and a bench judge read.
    """

    code: str
    detail: str
    until: str | None = None

    granted = False


@dataclass(frozen=True)
class Waiting:
    id: int
    account: str
    provider: str
    project: str
    slug: str
    step: str
    pid: int
    asked_at: str


@dataclass(frozen=True)
class Limited:
    account: str
    until: str
    said_at: str
    said_by: str
    guessed: bool
    #: What the provider actually said, in its own words. Kept because a
    #: guessed hour is only honest if the phrase it was guessed from is there
    #: to read: `machine` and the page both print it.
    said: str = ""


@dataclass(frozen=True)
class Ask:
    """A question standing against a person's phone, and the hour it gives up.

    It lives here rather than in the run file because it is live truth and it
    crosses projects: the page shows it, and whoever is polling the channel has
    to be able to address an answer that belongs to somebody else's run. What
    the run file keeps is the other fact — that its step asked, and what came
    of it.
    """

    id: str
    project: str
    slug: str
    step: str
    question: str
    default: str
    until: str
    #: What the channel called the message this went out as, where it says. A
    #: person on a phone replies to the message rather than typing an
    #: identifier, and this is what turns that reply back into a question.
    message: str = ""
    asked_at: str = field(default_factory=now)
    answer: str | None = None


@dataclass(frozen=True)
class Standing:
    """What one project has alive on this machine, and one reader: the door.

    Not `Picture`, which is the machine's whole screen across every project.
    This is one project's slice and it is the only thing the door asks the
    ledger for — is anything of mine being written right now, and is a question
    of mine standing against somebody's phone.
    """

    runs: list[Lease]
    batches: list[Lease]
    checkouts: list[Lease]
    asks: list[Ask]

    @property
    def anything(self) -> bool:
        return bool(self.runs or self.batches or self.checkouts)


@dataclass(frozen=True)
class Picture:
    """The three the page and `agent-kit machine` both show, from one read.

    Which runs have a driver on them is a fourth, and it is asked for
    separately: it is a different question — who is writing — and only two
    readers want it.
    """

    held: list[Lease]
    queue: list[Waiting]
    limits: list[Limited]


class Ledger:
    """One ledger object, one connection per thread that uses it.

    sqlite refuses a connection outside the thread that opened it, and the
    daemon has several: one sweeping, one per request the page answers. Sharing
    one would make the page an empty reply and the sweep a stack trace in a log
    nobody is reading — which is exactly what the first live run did.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._mine = threading.local()
        self._db  # opening it here is what creates the schema

    @property
    def _db(self) -> sqlite3.Connection:
        held = getattr(self._mine, "db", None)
        if held is None:
            held = self._mine.db = self._open()
        return held

    def close(self) -> None:
        """Close this thread's connection. The others close with their threads."""
        held = getattr(self._mine, "db", None)
        if held is not None:
            held.close()
            self._mine.db = None

    def _open(self) -> sqlite3.Connection:
        with self._saying_why():
            return self._opened()

    def _opened(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA foreign_keys=ON")
        # `executescript` commits whatever is open before it runs, so the schema
        # is not wrapped in one of this file's transactions. `CREATE TABLE IF
        # NOT EXISTS` is what makes two threads and two processes opening it at
        # once harmless.
        db.executescript(_SCHEMA)
        (held,) = db.execute("PRAGMA user_version").fetchone()
        if held > SCHEMA_VERSION:
            db.close()
            raise ProviderError(
                "ledger-too-new",
                f"{self.path} was written by a kit that knows schema {held}; this one knows"
                f" {SCHEMA_VERSION}",
                hint="upgrade the kit, or move the ledger aside — it holds nothing that outlives a reboot",
            )
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        return db

    @staticmethod
    @contextmanager
    def _saying_why() -> Iterator[None]:
        """sqlite's own failures, named.

        A file that is not a database, a state directory nobody may write, a
        ledger still locked after the timeout: none of those is a defect in the
        kit, and exit 70 says they are.
        """
        try:
            yield
        except sqlite3.Error as broken:
            raise ProviderError(
                "unreadable-ledger",
                f"the machine's ledger could not be read or written: {broken}",
            ) from broken

    @contextmanager
    def _writing(self) -> Iterator[sqlite3.Connection]:
        """One act, one transaction.

        Half of an act is what S6's review cost twice — a knowledge file rewritten
        and then refused. Taking a slot removes the waiter row in the same
        transaction that writes the lease, or neither happens.
        """
        with self._saying_why():
            self._db.execute("BEGIN IMMEDIATE")
        try:
            yield self._db
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        with self._saying_why():
            self._db.execute("COMMIT")

    # --- slots ------------------------------------------------------------

    def take(self, want: Want, ceilings: Ceilings) -> Lease | Busy:
        """A slot for one live session, or the reason there is none."""
        with self._writing() as db:
            self._reap(db)

            limited = self._limit_of(db, want.account)
            if limited is not None:
                return Busy(
                    "provider-limited",
                    f"{want.account} is limited until {limited.until}, as {limited.said_by} found out",
                    until=limited.until,
                )

            # What holds *this* request back is asked first, so the refusal
            # names what is actually in the way rather than who is in front.
            full = self._full(db, want, ceilings)
            if full is not None:
                return full

            # Nothing holds it back, so the only question left is whose turn it
            # is. S7 asked that of the asking account alone, which ordered two
            # waiters on two accounts by whoever polled at a lucky moment —
            # its own second debt, and a batch across two providers is what
            # makes it real. The queue that decides is the whole queue: whoever
            # asked first and could take this slot now.
            ahead = self._ahead_of(db, want, ceilings)
            if ahead is not None:
                return Busy("no-slot", f"{ahead.slug} asked for a slot first and is still waiting")

            db.execute(
                "DELETE FROM waiters WHERE project = ? AND slug = ?", (want.project, want.slug)
            )
            return self._write_lease(db, want, SESSION, want.ttl)

    def release(self, lease: Lease | None) -> None:
        """Asked for twice is the same as asked for once.

        By identity and not by the number alone: `INTEGER PRIMARY KEY` without
        `AUTOINCREMENT` is `max(rowid) + 1`, so a row that is gone gives its
        number to the next one. A driver whose lease was swept for being stale,
        releasing it afterwards, would otherwise delete whoever now holds that
        number — and the ceiling would be one session wider than the machine
        allows, silently.
        """
        if lease is None:
            return
        with self._writing() as db:
            db.execute(
                "DELETE FROM leases WHERE id = ? AND pid = ? AND boot = ? AND taken_at = ?",
                (lease.id, lease.pid, lease.boot, lease.taken_at),
            )

    def held(self, kind: str = SESSION) -> list[Lease]:
        with self._writing() as db:
            self._reap(db)
            rows = db.execute(
                "SELECT * FROM leases WHERE kind = ? ORDER BY id", (kind,)
            ).fetchall()
        return [_lease(row) for row in rows]

    def _full(self, db: sqlite3.Connection, want: Want, ceilings: Ceilings) -> Busy | None:
        sessions = db.execute("SELECT * FROM leases WHERE kind = ? ORDER BY id", (SESSION,)).fetchall()

        ceiling = ceilings.for_provider(want.provider)
        if ceiling is not None:
            same = [row for row in sessions if row["provider"] == want.provider]
            if len(same) >= ceiling:
                return Busy(
                    "no-slot",
                    f"{want.provider} runs {_sessions(ceiling)} at once here and {_holds(same)}",
                )

        if len(sessions) >= ceilings.max_sessions:
            return Busy(
                "no-slot",
                f"this machine runs {_sessions(ceilings.max_sessions)} at once and {_holds(sessions)}",
            )
        return None

    def _write_lease(self, db: sqlite3.Connection, want: Want, kind: str, ttl: int) -> Lease:
        taken, expires = now(), after(ttl)
        cursor = db.execute(
            "INSERT INTO leases (kind, account, provider, project, slug, step, pid, boot, taken_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kind, want.account, want.provider, want.project, want.slug, want.step,
             want.pid, want.boot, taken, expires),
        )
        return Lease(
            id=int(cursor.lastrowid), kind=kind, account=want.account, provider=want.provider,
            project=want.project, slug=want.slug, step=want.step, pid=want.pid, boot=want.boot,
            taken_at=taken, expires_at=expires,
        )

    # --- the queue ---------------------------------------------------------

    def wants_one(self, want: Want) -> None:
        """Say out loud what is being waited for, before sleeping on it.

        Without the row a run that arrived first can be jumped by one that woke
        at a better moment, and the page has nothing to show under *queued*.
        """
        with self._writing() as db:
            self._reap(db)
            standing = db.execute(
                "SELECT id FROM waiters WHERE project = ? AND slug = ?", (want.project, want.slug)
            ).fetchone()
            if standing is not None:
                return
            db.execute(
                "INSERT INTO waiters (account, provider, project, slug, step, pid, boot, asked_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (want.account, want.provider, want.project, want.slug, want.step,
                 want.pid, want.boot, now()),
            )

    def gives_up(self, want: Want) -> None:
        with self._writing() as db:
            db.execute("DELETE FROM waiters WHERE project = ? AND slug = ?", (want.project, want.slug))

    def queue(self) -> list[Waiting]:
        with self._writing() as db:
            self._reap(db)
            rows = db.execute("SELECT * FROM waiters ORDER BY id").fetchall()
        return [_waiting(row) for row in rows]

    def _ahead_of(self, db: sqlite3.Connection, want: Want, ceilings: Ceilings) -> Waiting | None:
        """Somebody asked before us and could take this slot right now.

        Insertion order and not the clock: two waiters in one second are still
        two waiters, and the row that was written first is the one that asked
        first. *Could take it* is what makes the ordering honest across
        accounts — a waiter whose own account is limited, or whose provider is
        already full here, is not in front of anybody: letting it hold the
        queue would idle a machine that has room.
        """
        mine = db.execute(
            "SELECT id FROM waiters WHERE project = ? AND slug = ?", (want.project, want.slug)
        ).fetchone()
        rows = (
            db.execute("SELECT * FROM waiters ORDER BY id").fetchall()
            if mine is None
            else db.execute("SELECT * FROM waiters WHERE id < ? ORDER BY id", (mine["id"],)).fetchall()
        )
        sessions = db.execute("SELECT * FROM leases WHERE kind = ?", (SESSION,)).fetchall()
        for row in rows:
            if self._could_go(db, row, sessions, ceilings):
                return _waiting(row)
        return None

    def _could_go(self, db: sqlite3.Connection, row: sqlite3.Row, sessions: list, ceilings: Ceilings) -> bool:
        """Is this waiter actually able to run, or is it waiting on something else?

        Asked only of waiters ahead of a request the machine has already agreed
        to, so the machine's own ceiling is known to have room; what is left is
        the two things that bind one account and one provider.
        """
        if self._limit_of(db, str(row["account"])) is not None:
            return False
        ceiling = ceilings.for_provider(str(row["provider"]))
        if ceiling is None:
            return True
        return len([held for held in sessions if held["provider"] == row["provider"]]) < ceiling

    # --- limits ------------------------------------------------------------

    def limit(self, account: str, until: str | None, said_by: str) -> Limited:
        """One session paid to learn this. It must cost the next one nothing.

        An hour that cannot be read is an hour that was not read: the row says
        `guessed`, keeps the phrase, and stands for one hour rather than for
        however long the phrase happens to sort above today's date.
        """
        read = moment(until)
        held = Limited(
            account=account,
            until=read or after(GUESSED_LIMIT),
            said_at=now(),
            said_by=said_by,
            guessed=read is None,
            said=(until or "").strip(),
        )
        with self._writing() as db:
            db.execute(
                "INSERT INTO limits (account, until, said, said_at, said_by, guessed)"
                " VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(account) DO UPDATE SET until = excluded.until, said = excluded.said,"
                " said_at = excluded.said_at, said_by = excluded.said_by, guessed = excluded.guessed",
                (held.account, held.until, held.said, held.said_at, held.said_by, int(held.guessed)),
            )
        return held

    def unlimit(self, account: str) -> None:
        with self._writing() as db:
            db.execute("DELETE FROM limits WHERE account = ?", (account,))

    def limits(self) -> list[Limited]:
        with self._writing() as db:
            self._reap(db)
            rows = db.execute("SELECT * FROM limits ORDER BY account").fetchall()
        return [_limited(row) for row in rows]

    def _limit_of(self, db: sqlite3.Connection, account: str) -> Limited | None:
        row = db.execute("SELECT * FROM limits WHERE account = ?", (account,)).fetchone()
        return _limited(row) if row else None

    # --- one driver per run -------------------------------------------------

    def hold_run(self, project: str, slug: str, pid: int | None = None, boot: str | None = None) -> Lease | Busy:
        """Open question 2, enforced at last: a run has one writer, and it is its driver.

        The same driver asking again holds what it already holds — a run is
        advanced step by step, and each step asks.
        """
        want = Want(
            account="", provider="", project=project, slug=slug, step="",
            ttl=RUN_TTL, **({"pid": pid} if pid is not None else {}), **({"boot": boot} if boot is not None else {}),
        )
        with self._writing() as db:
            self._reap(db)
            row = db.execute(
                "SELECT * FROM leases WHERE kind = ? AND project = ? AND slug = ?", (RUN, project, slug)
            ).fetchone()
            if row is not None:
                if row["pid"] == want.pid and row["boot"] == want.boot:
                    return _lease(row)
                return Busy(
                    "run-held-elsewhere",
                    f"{slug} is being run by process {row['pid']} since {row['taken_at']};"
                    " two drivers on one run is how a record ends up truncated",
                )
            return self._write_lease(db, want, RUN, RUN_TTL)

    def hold_checkout(self, project: str, slug: str, pid: int | None = None, boot: str | None = None) -> Lease | Busy:
        """One writer per working copy, asked for by whoever has no tree of their own.

        Keyed on the checkout and not on the run: the point is that a second run
        cannot have it, so the row says which run does and the refusal names it.
        It takes no slot — a working copy is not quota.
        """
        want = Want(
            account="", provider="", project=project, slug=slug, step="",
            ttl=RUN_TTL, **({"pid": pid} if pid is not None else {}), **({"boot": boot} if boot is not None else {}),
        )
        with self._writing() as db:
            self._reap(db)
            row = db.execute(
                "SELECT * FROM leases WHERE kind = ? AND project = ?", (CHECKOUT, project)
            ).fetchone()
            if row is not None:
                if row["slug"] == slug and row["pid"] == want.pid and row["boot"] == want.boot:
                    return _lease(row)
                return Busy(
                    "checkout-held-elsewhere",
                    f"{row['slug']} is building in {project} itself (process {row['pid']},"
                    f" since {row['taken_at']}), and a run with no worktree of its own builds there too;"
                    " two of them in one working copy is two sessions editing one file",
                )
            return self._write_lease(db, want, CHECKOUT, RUN_TTL)

    def checkouts(self) -> list[Lease]:
        """Which working copies have a run building in them right now."""
        return self.held(kind=CHECKOUT)

    def hold_batch(self, project: str, name: str, pid: int | None = None, boot: str | None = None) -> Lease | Busy:
        """One driver per batch, for the reason there is one per run.

        It takes no slot: a batch driver starts children and waits, and a slot
        counts live sessions, whose cost is quota.
        """
        want = Want(
            account="", provider="", project=project, slug=name, step="",
            ttl=RUN_TTL, **({"pid": pid} if pid is not None else {}), **({"boot": boot} if boot is not None else {}),
        )
        with self._writing() as db:
            self._reap(db)
            row = db.execute(
                "SELECT * FROM leases WHERE kind = ? AND project = ? AND slug = ?", (BATCH, project, name)
            ).fetchone()
            if row is not None:
                if row["pid"] == want.pid and row["boot"] == want.boot:
                    return _lease(row)
                return Busy(
                    "batch-held-elsewhere",
                    f"{name} is being run by process {row['pid']} since {row['taken_at']};"
                    " two drivers on one batch is two writers on one file",
                )
            return self._write_lease(db, want, BATCH, RUN_TTL)

    def batches(self) -> list[Lease]:
        """Which batches have a driver on them right now."""
        return self.held(kind=BATCH)

    # --- stop ---------------------------------------------------------------

    def ask_stop(self, project: str, slug: str, reason: str) -> None:
        """A person's stop, posted where the run's own driver will read it."""
        with self._writing() as db:
            db.execute(
                "INSERT INTO requests (project, slug, what, reason, asked_at) VALUES (?, ?, 'stop', ?, ?)",
                (project, slug, reason, now()),
            )

    def stop_pending(self, project: str, slug: str) -> str | None:
        """Is a stop standing? Read without taking it: whoever acts on it takes it."""
        with self._writing() as db:
            self._reap(db)
            row = db.execute(
                "SELECT reason FROM requests WHERE project = ? AND slug = ? AND what = 'stop'"
                " ORDER BY id LIMIT 1",
                (project, slug),
            ).fetchone()
        return None if row is None else str(row["reason"])

    def stop_asked(self, project: str, slug: str) -> str | None:
        """Read once. Asked for twice, a run still stops once."""
        with self._writing() as db:
            rows = db.execute(
                "SELECT * FROM requests WHERE project = ? AND slug = ? AND what = 'stop' ORDER BY id",
                (project, slug),
            ).fetchall()
            if not rows:
                return None
            db.execute(
                "DELETE FROM requests WHERE project = ? AND slug = ? AND what = 'stop'", (project, slug)
            )
        return str(rows[0]["reason"])

    # --- skip, whose unit is a feature inside a batch -------------------------

    def ask_skip(self, project: str, name: str, feature: str, reason: str) -> None:
        """Do not build this feature tonight, posted where the batch driver reads it.

        Addressed to the batch and naming the feature, because that is what a
        skip is: outside a batch there is no night to take a feature out of, and
        a run on its own is stopped by a door that already exists.
        """
        with self._writing() as db:
            db.execute(
                "INSERT INTO requests (project, slug, what, reason, asked_at) VALUES (?, ?, ?, ?, ?)",
                (project, name, f"{SKIP}:{feature}", reason, now()),
            )

    def skips_asked(self, project: str, name: str) -> list[tuple[str, str]]:
        """Read once, in the order they were asked for. Asked twice, skipped once."""
        with self._writing() as db:
            rows = db.execute(
                "SELECT * FROM requests WHERE project = ? AND slug = ? AND what LIKE ? ORDER BY id",
                (project, name, f"{SKIP}:%"),
            ).fetchall()
            if not rows:
                return []
            db.execute(
                "DELETE FROM requests WHERE project = ? AND slug = ? AND what LIKE ?",
                (project, name, f"{SKIP}:%"),
            )
        asked: list[tuple[str, str]] = []
        for row in rows:
            feature = str(row["what"]).split(":", 1)[1]
            if feature not in [named for named, _ in asked]:
                asked.append((feature, str(row["reason"])))
        return asked

    # --- questions waiting on a person ---------------------------------------

    def asked(self, ask: Ask) -> Ask:
        """Записать вопрос до того, как он уйдёт, и спросить дважды — это спросить раз.

        Драйвер, умерший между отправкой и ответом, поднимается заново и шлёт
        вопрос ещё раз — новым сообщением и с новым часом. Строка обязана
        назвать именно их: иначе реплай на второе сообщение не находит вопроса,
        а выметание сносит строку по первому, давно прошедшему часу — из-под
        драйвера, который в эту минуту её ждёт.

        Ответ при этом не трогается. Он пришёл к тому же вопросу, кто бы его ни
        отправлял, и первый ответ стоит.
        """
        with self._writing() as db:
            db.execute(
                "INSERT INTO asks (id, project, slug, step, question, \"default\", message, asked_at, until,"
                " answer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)"
                " ON CONFLICT(id) DO UPDATE SET message = excluded.message, until = excluded.until,"
                " asked_at = excluded.asked_at",
                (ask.id, ask.project, ask.slug, ask.step, ask.question, ask.default,
                 ask.message, ask.asked_at, ask.until),
            )
            row = db.execute("SELECT * FROM asks WHERE id = ?", (ask.id,)).fetchone()
        return _ask(row)

    def free_ask_id(self, project: str, slug: str, id: str) -> str:
        """Имя, которым этот вопрос может назваться, не отняв чужого.

        Идентификатор выводится из имени прогона и слов вопроса — так, чтобы
        случай стенда мог назвать его заранее. Но проекта он не знает, а строка
        одна на всех: два прогона с одинаковым именем и одинаковым вопросом в
        разных проектах делили бы её, и ответ одного доставался бы другому.

        Свой вопрос остаётся при своём имени; чужому подбирается следующее, тем
        же способом, каким знание разводит два одинаково сформулированных
        допущения.
        """
        from ..knowledge.format import identifier

        with self._writing() as db:
            taken = id
            for salt in range(_NAMES_TRIED):
                row = db.execute("SELECT project FROM asks WHERE id = ?", (taken,)).fetchone()
                if row is None or row["project"] == project:
                    return taken
                taken = identifier(f"{project}\0{slug}", taken, salt=salt + 1)
        raise ProviderError(
            "no-free-ask-id",
            f"{_NAMES_TRIED} имён для одного вопроса уже заняты; это не может быть правдой",
        )

    def answered(self, id: str, text: str) -> bool:
        """A person answered. True when this was the answer, false when it was not.

        Первый ответ стоит: второй, пришедший, пока шаг уже перезапускают,
        менял бы запись под ним. Час, когда ответили, живёт в `asks.json` шага
        — здесь он не нужен никому, а поле без читателя не пишется.
        """
        with self._writing() as db:
            changed = db.execute(
                "UPDATE asks SET answer = ? WHERE id = ? AND answer IS NULL",
                (text, id),
            ).rowcount
        return bool(changed)

    def ask_of(self, id: str) -> Ask | None:
        with self._writing() as db:
            row = db.execute("SELECT * FROM asks WHERE id = ?", (id,)).fetchone()
        return _ask(row) if row else None

    def ask_sent_as(self, message: str) -> Ask | None:
        """The question a person is replying to, found by the message they replied to."""
        if not message:
            return None
        with self._writing() as db:
            row = db.execute(
                "SELECT * FROM asks WHERE message = ? ORDER BY asked_at DESC LIMIT 1", (message,)
            ).fetchone()
        return _ask(row) if row else None

    def waiting_on_the_owner(self) -> list[Ask]:
        """What the page shows under *waiting for the owner*, and `machine` prints."""
        with self._writing() as db:
            self._reap(db)
            rows = db.execute(
                "SELECT * FROM asks WHERE answer IS NULL ORDER BY asked_at, id"
            ).fetchall()
        return [_ask(row) for row in rows]

    def forget(self, ids: list[str]) -> None:
        """The run is done with these, whether they were answered or defaulted."""
        with self._writing() as db:
            for id in ids:
                db.execute("DELETE FROM asks WHERE id = ?", (id,))

    # --- the channel: one reader, and an offset that outlives it -------------

    def read_channel(self, pid: int | None = None, boot: str | None = None) -> Lease | Busy:
        """The right to poll the channel, held by one process at a time."""
        want = Want(
            account="", provider="", project="", slug=CHANNEL, step="", ttl=READER_TTL,
            **({"pid": pid} if pid is not None else {}), **({"boot": boot} if boot is not None else {}),
        )
        with self._writing() as db:
            self._reap(db)
            row = db.execute("SELECT * FROM leases WHERE kind = ?", (CHANNEL,)).fetchone()
            if row is not None:
                if row["pid"] == want.pid and row["boot"] == want.boot:
                    return _lease(row)
                return Busy(
                    "channel-held-elsewhere",
                    f"process {row['pid']} has been reading the owner's channel since {row['taken_at']};"
                    " two readers of one channel steal each other's answers",
                )
            return self._write_lease(db, want, CHANNEL, READER_TTL)

    def offset(self) -> str:
        """Where the last reader got to. In the file, because a process is not a place."""
        with self._writing() as db:
            row = db.execute("SELECT value FROM channel WHERE what = 'offset'").fetchone()
        return "" if row is None else str(row["value"])

    def remember_offset(self, value: str) -> None:
        with self._writing() as db:
            db.execute(
                "INSERT INTO channel (what, value) VALUES ('offset', ?)"
                " ON CONFLICT(what) DO UPDATE SET value = excluded.value",
                (value,),
            )

    # --- what died ----------------------------------------------------------

    def reap(self) -> int:
        """What the daemon does on its own, and what everybody does before asking."""
        with self._writing() as db:
            return self._reap(db)

    def _reap(self, db: sqlite3.Connection) -> int:
        """Three ways a row is dead, in the order they are cheap to ask."""
        this_boot = boot_id()
        gone = 0
        this_moment = now()
        for table in ("leases", "waiters"):
            for row in db.execute(f"SELECT id, pid, boot FROM {table}").fetchall():
                if row["boot"] == this_boot and is_alive(row["pid"]):
                    continue
                db.execute(f"DELETE FROM {table} WHERE id = ?", (row["id"],))
                gone += 1
        gone += db.execute("DELETE FROM leases WHERE expires_at <= ?", (this_moment,)).rowcount
        gone += db.execute("DELETE FROM limits WHERE until <= ?", (this_moment,)).rowcount
        # A stop is addressed to the driver that was holding the run when it was
        # asked for. If that driver never came back, nobody is going to read it,
        # and a request left standing stops whatever run next carries that name.
        # A question outlives its deadline by an hour before it is swept: the
        # driver reads once more after the deadline, and sweeping in that gap
        # throws away an answer that did arrive.
        gone += db.execute(
            "DELETE FROM asks WHERE until <= ?", (after(-ASK_GRACE),)
        ).rowcount
        gone += db.execute(
            "DELETE FROM requests WHERE NOT EXISTS ("
            "  SELECT 1 FROM leases WHERE leases.kind IN (?, ?) AND leases.project = requests.project"
            "   AND leases.slug = requests.slug)",
            (RUN, BATCH),
        ).rowcount
        return gone

    # --- what the page reads ------------------------------------------------

    def picture(self) -> Picture:
        with self._writing() as db:
            self._reap(db)
            held = [_lease(row) for row in db.execute(
                "SELECT * FROM leases WHERE kind = ? ORDER BY id", (SESSION,)).fetchall()]
            queue = [_waiting(row) for row in db.execute("SELECT * FROM waiters ORDER BY id").fetchall()]
            limits = [_limited(row) for row in db.execute("SELECT * FROM limits ORDER BY account").fetchall()]
        return Picture(held=held, queue=queue, limits=limits)

    def runs(self) -> list[Lease]:
        """Which runs have a driver on them right now."""
        return self.held(kind=RUN)

    def standing(self, project: str) -> "Standing":
        """What of one project is alive right now, read without changing anything.

        Every other reader here goes through `_writing`, which opens a
        transaction and sweeps the dead before it answers. That is right for
        everybody who is about to act on what they read. The door is not: it
        reports, it is run by somebody standing in a project while a night may
        be going on in another, and a reader that takes `BEGIN IMMEDIATE` to
        print a screen is a reader that can block a driver.

        So the three conditions `_reap` deletes on are applied in memory
        instead: this boot, a live process, and a lease that has not expired. A
        row that fails them is dead and is not counted — it is simply left for
        whoever writes next to delete.
        """
        this_boot = boot_id()
        this_moment = now()

        def alive(row: sqlite3.Row) -> bool:
            return (
                row["boot"] == this_boot
                and is_alive(row["pid"])
                and str(row["expires_at"]) > this_moment
            )

        with self._saying_why():
            leases = self._db.execute(
                "SELECT * FROM leases WHERE project = ? AND kind IN (?, ?, ?) ORDER BY id",
                (project, RUN, BATCH, CHECKOUT),
            ).fetchall()
            asks = self._db.execute(
                "SELECT * FROM asks WHERE project = ? AND answer IS NULL ORDER BY asked_at, id",
                (project,),
            ).fetchall()

        held = [_lease(row) for row in leases if alive(row)]
        return Standing(
            runs=[one for one in held if one.kind == RUN],
            batches=[one for one in held if one.kind == BATCH],
            checkouts=[one for one in held if one.kind == CHECKOUT],
            asks=[_ask(row) for row in asks if str(row["until"]) > after(-ASK_GRACE)],
        )


# --- rows into what the rest of the kit reads -------------------------------


def _lease(row: sqlite3.Row) -> Lease:
    return Lease(
        id=int(row["id"]), kind=row["kind"], account=row["account"], provider=row["provider"],
        project=row["project"], slug=row["slug"], step=row["step"], pid=int(row["pid"]),
        boot=row["boot"], taken_at=row["taken_at"], expires_at=row["expires_at"],
    )


def _ask(row: sqlite3.Row) -> Ask:
    return Ask(
        id=row["id"], project=row["project"], slug=row["slug"], step=row["step"],
        question=row["question"], default=row["default"], message=row["message"],
        asked_at=row["asked_at"], until=row["until"], answer=row["answer"],
    )


def _waiting(row: sqlite3.Row) -> Waiting:
    return Waiting(
        id=int(row["id"]), account=row["account"], provider=row["provider"], project=row["project"],
        slug=row["slug"], step=row["step"], pid=int(row["pid"]), asked_at=row["asked_at"],
    )


def _limited(row: sqlite3.Row) -> Limited:
    return Limited(
        account=row["account"], until=row["until"], said_at=row["said_at"],
        said_by=row["said_by"], guessed=bool(row["guessed"]), said=row["said"],
    )


def _sessions(count: int) -> str:
    return "1 session" if count == 1 else f"{count} sessions"


def _holds(rows: list[sqlite3.Row]) -> str:
    named = ", ".join(f"{row['slug']}/{row['step']}" if row["step"] else row["slug"] for row in rows)
    return f"{named} holds it" if len(rows) == 1 else f"{named} hold them"
