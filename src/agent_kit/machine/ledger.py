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

SCHEMA_VERSION = 1

#: How long a lease outlives the moment it was taken, when nobody says
#: otherwise. Only ever a backstop for a pid that was reused: what really says
#: a lease is dead is that its driver is not there any more.
DEFAULT_TTL = 3 * 60 * 60

#: A run is held for as long as its driver runs it, which is a night at most.
RUN_TTL = 24 * 60 * 60

#: What a limit costs when the provider said it was limited and named no hour.
#: A guess, and the row says so rather than passing it off as something read.
GUESSED_LIMIT = 60 * 60

SESSION = "session"
RUN = "run"

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

    @property
    def who(self) -> str:
        return f"{self.slug}/{self.step}" if self.step else self.slug


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

    @property
    def who(self) -> str:
        return f"{self.slug}/{self.step}" if self.step else self.slug


@dataclass(frozen=True)
class Busy:
    """The machine said no, by name. Every code here is one an exit code maps onto."""

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
class Picture:
    """Everything the page and `agent-kit machine` show, from one read."""

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

    @contextmanager
    def _writing(self) -> Iterator[sqlite3.Connection]:
        """One act, one transaction.

        Half of an act is what S6's review cost twice — a knowledge file rewritten
        and then refused. Taking a slot removes the waiter row in the same
        transaction that writes the lease, or neither happens.
        """
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield self._db
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
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

            ahead = self._ahead_of(db, want)
            if ahead is not None:
                return Busy("no-slot", f"{ahead.slug} asked for {want.account} first and is still waiting")

            full = self._full(db, want, ceilings)
            if full is not None:
                return full

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

    def _ahead_of(self, db: sqlite3.Connection, want: Want) -> Waiting | None:
        """Somebody asked for this account before us and is still waiting.

        Insertion order and not the clock: two waiters in one second are still
        two waiters, and the row that was written first is the one that asked first.
        """
        mine = db.execute(
            "SELECT id FROM waiters WHERE project = ? AND slug = ?", (want.project, want.slug)
        ).fetchone()
        limit = mine["id"] if mine else None
        if limit is None:
            row = db.execute(
                "SELECT * FROM waiters WHERE account = ? ORDER BY id LIMIT 1", (want.account,)
            ).fetchone()
        else:
            row = db.execute(
                "SELECT * FROM waiters WHERE account = ? AND id < ? ORDER BY id LIMIT 1",
                (want.account, limit),
            ).fetchone()
        return _waiting(row) if row else None

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

    # --- stop ---------------------------------------------------------------

    def ask_stop(self, project: str, slug: str, reason: str) -> None:
        """A person's stop, posted where the run's own driver will read it."""
        with self._writing() as db:
            db.execute(
                "INSERT INTO requests (project, slug, what, reason, asked_at) VALUES (?, ?, 'stop', ?, ?)",
                (project, slug, reason, now()),
            )

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
        gone += db.execute(
            "DELETE FROM requests WHERE NOT EXISTS ("
            "  SELECT 1 FROM leases WHERE leases.kind = ? AND leases.project = requests.project"
            "   AND leases.slug = requests.slug)",
            (RUN,),
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


# --- rows into what the rest of the kit reads -------------------------------


def _lease(row: sqlite3.Row) -> Lease:
    return Lease(
        id=int(row["id"]), kind=row["kind"], account=row["account"], provider=row["provider"],
        project=row["project"], slug=row["slug"], step=row["step"], pid=int(row["pid"]),
        boot=row["boot"], taken_at=row["taken_at"], expires_at=row["expires_at"],
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
