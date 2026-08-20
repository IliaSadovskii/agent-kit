#!/usr/bin/env python3
"""Drive a batch of ship runs, one visible session at a time.

    orchestrate.py <run-dir> [options]

<run-dir> is `.agent-kit/runs/<slug>/` for a run whose `children` names the features to build, in
order. Each child is one `claude` session running `/agent-kit:ship --run <its own run dir>`.

This program holds no judgement. It reads run files, watches a transcript's modification time, knows
one HTTP status, and calls git and gh. Everything that requires an opinion belongs to a session:
the brief that filled the children, the child that builds one, the closing session that opens the
pull request. See docs/design/sprint.md for why the driver is a loop rather than an agent.

Python 3.9+, standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:                                              # 3.9+, but not on every distribution
    from zoneinfo import ZoneInfo
except ImportError:                               # pragma: no cover - fallback below covers it
    ZoneInfo = None

# The two ship side by side, and the driver is the one thing present at the moment a child stops —
# which is the only moment a defect in a run file can still be acted on.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import run_defects                     # noqa: E402 - the path above is what makes it work
import runfile                                    # noqa: E402 - what a run is, for every reader of one

# What a run is has one home now, and this is the name the driver uses for it.
TERMINAL_STEPS = set(runfile.TERMINAL)
HANDOFF_LINE = ("[driver] your context has grown past what one session should carry — hand this run "
                "over: finish the task you are on, close it in the run file, fill `handoff`, and "
                "stop. The rule is the Handing over section of skills/ship/SKILL.md. Do not start "
                "the next task, and do not finish the run to get out of it.")
LIMIT_MARKER = '"apiErrorStatus":429'
OVERLOADED_MARKER = '"apiErrorStatus":529'
RESET_RE = re.compile(r"resets\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:\(([^)]+)\))?", re.I)


# --------------------------------------------------------------------------------------------
# run files


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    tmp.replace(path)


class Run:
    """One run directory: its state file, its log, and the questions asked of both."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.file = directory / "run.json"
        self.log = directory / "run.log"

    @property
    def slug(self) -> str:
        return self.dir.name

    def state(self) -> dict:
        try:
            return read_json(self.file)
        except (OSError, json.JSONDecodeError):
            return {}

    def set(self, **fields) -> None:
        state = self.state()
        state.update(fields)
        self.dir.mkdir(parents=True, exist_ok=True)
        write_json(self.file, state)

    def event(self, event: str, detail: str = "") -> None:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{stamp} step=driver event={event} detail={detail}\n"
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write(line)
        print(line.rstrip(), flush=True)

    def own_pr(self, state: dict | None = None) -> int | None:
        """This run's pull request, when opening it was this run's own job.

        `pr` is the driver's second signal that a run finished: a session can die between opening
        the pull request and writing its step, and the world is the better witness. But inside an
        `epic` **one** pull request covers the whole run, so every batch after the first carries a
        number that was already there — and a batch may carry it before it has done anything.

        Measured twice on one live run: the number was written into a batch's file in advance, this
        returned true a minute after the closing session started, and the driver killed the session
        that was closing the batch. Both times the branch, the pull request body and the digest were
        put right by hand the next morning. A number inherited from the run above says nothing about
        this run, so it is not read as evidence of anything.
        """
        state = self.state() if state is None else state
        pr = state.get("pr")
        if not pr:
            return None
        parent = state.get("parent")
        if parent and Run(self.dir.parent / parent).state().get("pr") == pr:
            return None
        return pr

    def terminal(self) -> bool:
        state = self.state()
        return state.get("step") in TERMINAL_STEPS or bool(self.own_pr(state))


# --------------------------------------------------------------------------------------------
# sessions
#
# The kit cannot depend on this server's helpers, so the launcher is the one place that knows how a
# visible session is made. `claude-new` is used when it exists because it registers the session and
# names it for the app; plain tmux is the portable fallback. Both must produce a session whose
# transcript is discoverable and which can be typed into — that is the whole contract.


class Launcher:
    def __init__(self, cwd: Path, model: str | None):
        self.cwd = cwd
        self.model = model
        self.helper = shutil.which("claude-new")
        self.closer = shutil.which("claude-close")
        self.reclaimed: str | None = None         # set by start() when it took a name back
        self.warned_closer = False                # the helper-without-a-closer line, said once

    def _tmux(self, *args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(["tmux", *args], capture_output=True, text=True)
        except FileNotFoundError:                 # checked once in main(); this is the belt
            return subprocess.CompletedProcess(["tmux", *args], 127, "", "tmux is not installed")

    def tmux_name(self, name: str) -> str:
        return f"cc-{name}" if self.helper else f"agent-kit-{name}"

    def start(self, name: str, prompt: str, model: str | None = None) -> bool:
        """Create a session and type the prompt into it — never into one that was already there.

        A helper can report "that name is taken" as success: `claude-new` prints it and exits 0.
        Trusting the exit code then sends the prompt to whatever is sitting at that name, appended
        to anything half-typed in its box. The hand-back session is where this bites — its name
        comes from the run above, so it is the same name on every batch, and the second batch would
        type its instruction into the first one's leftovers. A name that is alive here is a session
        whose work is behind it: take it back rather than write into it, and say that you did.
        """
        self.reclaimed = None
        if self.alive(name):
            self.stop(name)
            self.reclaimed = name
            time.sleep(1)                         # tmux frees the name a moment after the kill
        if self.helper:
            done = subprocess.run([self.helper, name, str(self.cwd)], capture_output=True, text=True)
            if done.returncode != 0:
                return False
        else:
            command = ["claude", "--dangerously-skip-permissions", "--remote-control"]
            done = self._tmux("new-session", "-d", "-s", self.tmux_name(name), "-c", str(self.cwd),
                              " ".join(command))
            if done.returncode != 0:
                return False
        time.sleep(5)                             # the session has to reach its prompt before it can be typed into
        # Typed rather than passed as a flag: `claude-new` takes no model, and losing it would cost
        # the session its registration and its name in the app. `/model` is what a person would use.
        model = model or self.model               # `--model` is the whole run's default
        if model and self.send(name, f"/model {model}"):
            time.sleep(2)
        return self.send(name, prompt)

    def send(self, name: str, text: str) -> bool:
        return self.send_to(self.tmux_name(name), text)

    def alive(self, name: str) -> bool:
        return self.alive_at(self.tmux_name(name))

    # The owner's own session is named by them, not by this program, so it is addressed verbatim.

    def send_to(self, target: str, text: str) -> bool:
        if self._tmux("send-keys", "-t", target, "-l", text).returncode != 0:
            return False
        time.sleep(0.5)
        return self._tmux("send-keys", "-t", target, "Enter").returncode == 0

    def alive_at(self, target: str) -> bool:
        return self._tmux("has-session", "-t", target).returncode == 0

    def stop(self, name: str) -> None:
        """Close a session this driver started. The helper's word is final where there is one.

        A session made by `claude-new` is *registered*, and killing its terminal without
        unregistering it is not closing it: on the machine this was measured on, a watchdog put the
        session back a minute later. So the helper decides — a refusal means either that it guards
        that session or that it stopped part way, and killing over the top of either is how the
        defect comes back. Where the helper made the session and cannot close it, say so once: a
        kill that leaves a registration behind is not a thing to do quietly.
        """
        if self.helper and not self.closer:
            if not self.warned_closer:
                self.warned_closer = True
                print(f"claude-new made these sessions and claude-close is not on the path — "
                      f"closing {self.tmux_name(name)} with tmux alone may leave it registered, "
                      f"and whatever restores registered sessions will bring it back",
                      file=sys.stderr)
        elif self.closer:
            done = subprocess.run([self.closer, name], capture_output=True, text=True)
            if done.returncode != 0:
                print(f"{self.closer} refused {name}: "
                      f"{done.stderr.strip() or done.stdout.strip() or done.returncode}",
                      file=sys.stderr)
            return                                # it unregisters, then kills, on its own clock
        self._tmux("kill-session", "-t", self.tmux_name(name))


# --------------------------------------------------------------------------------------------
# transcripts
#
# A session's own transcript grows on every message and every tool call, whether or not the agent
# writes anything to the run log. It is the only heartbeat that does not depend on the agent
# cooperating, and it is where the account limit records itself as data rather than as prose.


def transcript_dir(cwd: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
    return Path.home() / ".claude" / "projects" / slug


def newest_transcript(cwd: Path, after: float, mark: str = "") -> Path | None:
    """The transcript of the session this driver just started — not whatever wrote last here.

    Every session in a project shares one transcript directory, and the owner's own window is in
    there too. Picking the newest file by modification time means picking the one that was typed
    into most recently, which on a measured run was the window: the driver read a 370k conversation
    as if it were its child's context, asked the child to hand over on the strength of it, and did
    the same to every session that replaced it.

    A file this driver started *begins* after the session was launched, so the first record's
    timestamp is what tells it apart from a conversation that has been open for an hour. Among
    those, the one whose opening lines carry the run's own slug is certain; without a match the
    newest of them is the answer, which is the old behaviour narrowed to the right candidates.
    """
    directory = transcript_dir(cwd)
    if not directory.is_dir():
        return None
    fresh = []
    for path in directory.glob("*.jsonl"):
        try:
            if path.stat().st_mtime < after:
                continue
        except OSError:
            continue
        began = opened_at(path)
        if began is not None and began < after - 60:  # a conversation that was already running
            continue
        fresh.append(path)
    if mark:
        named = [p for p in fresh if mark in read_head(p)]
        if named:
            fresh = named
    return max(fresh, key=lambda p: p.stat().st_mtime, default=None)


def read_head(path: Path, lines: int = 12) -> str:
    """The opening records of a transcript — the prompt the driver typed is in them."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return "".join(next(fh, "") for _ in range(lines))
    except OSError:
        return ""


def opened_at(path: Path) -> float | None:
    """When this transcript's first record was written, or None when it carries no timestamp."""
    for line in read_head(path).splitlines():
        found = re.search(r'"timestamp"\s*:\s*"(\d{4}-\d\d-\d\dT[\d:.]+)Z"', line)
        if not found:
            continue
        try:
            return dt.datetime.strptime(found.group(1)[:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=dt.timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def last_spoke(path: Path) -> float | None:
    """When the session last actually wrote something, from the transcript's own timestamps.

    A file's mtime is not that. It moves when the harness touches the file for reasons of its own,
    and a live run was measured with its child silent for 44 minutes while the driver, reading
    mtime, saw 24 — twenty-one of them bought by one empty touch. On a night of thirty features
    that lag is hours of a watcher believing it is watching.

    The records carry ISO timestamps, so the tail already read for limit detection answers this
    exactly. Returns None when the tail carries none, and the caller falls back to mtime.
    """
    newest = None
    for line in read_tail(path, lines=200).splitlines():
        found = re.search(r'"timestamp"\s*:\s*"(\d{4}-\d\d-\d\dT[\d:.]+Z)"', line)
        if not found:
            continue
        try:
            when = dt.datetime.strptime(
                found.group(1)[:19], "%Y-%m-%dT%H:%M:%S").replace(
                    tzinfo=dt.timezone.utc).timestamp()
        except ValueError:
            continue
        newest = when if newest is None else max(newest, when)
    return newest


def read_tail(path: Path, lines: int = 40) -> str:
    """Last lines of a file, without reading a transcript that can be hundreds of megabytes.

    The window is bytes, and one transcript line is one record — a record carrying a large tool
    result is a long line. Measured over 186 sessions of two runs, the longest single line is 273k
    characters: a window of 200k could start inside it, leaving `splitlines` one fragment that
    parses as nothing, and everything read off this tail would then be silent rather than wrong.
    It never happened on those runs — 1459 simulated polls, no blind read — because such a line was
    never the last one. The window is 400k so that it cannot.
    """
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 400_000))
            text = fh.read().decode("utf-8", errors="replace")
        return "\n".join(text.splitlines()[-lines:])
    except OSError:
        return ""


USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def record_size(line: str) -> int:
    """The context one transcript record reports: its three input fields, counted once.

    *Counted once* is the whole of it. A record carries those three numbers twice — in `usage` and
    again inside `usage.iterations[]`, which repeats them per API iteration. The pattern match this
    replaces summed every occurrence in the line, so it reported exactly double on 20,249 of the
    20,260 usage records of one run, and the eleven it did not were the ones with no `iterations` at
    all. A ceiling of 300k fired at 150k of real context and a floor read 91k where it was 45.5k —
    the run behaved as if configured at half of what its own command line said.

    That is why this parses the record instead of scanning it. A field that appears twice is not a
    number to add up, and no regular expression over a line can tell the copy from the original.

    Zero for a line that is not a usage record, including the half line a tail read starts on.
    """
    try:
        record = json.loads(line)
    except (TypeError, ValueError):               # a tail begins mid-line as often as not
        return 0
    if not isinstance(record, dict):
        return 0
    message = record.get("message")
    usage = message.get("usage") if isinstance(message, dict) else None
    if not isinstance(usage, dict):
        return 0
    return sum(int(usage.get(field) or 0) for field in USAGE_FIELDS)


def context_size(text: str) -> int:
    """How big this session's context has grown, from the usage its own transcript records.

    Every turn re-sends the whole context, so a session's price grows with the square of its
    turns. Fitted over 170 sessions of two live runs, in tokens priced against a plain input token:
    `0.48M + 5.3k·n + 75.6·n²`. At 150 turns the square is already 57% of what a session costs, and
    the session cannot see its own size — only the transcript carries it. So the program measures
    and the session judges what to do about it, the split this driver keeps everywhere else.

    Zero when the tail carries no usage record — a number that cannot be read is not a small one,
    and the caller must not treat it as room to grow.
    """
    largest = 0
    for line in text.splitlines():                # one record per line, so one usage per line
        largest = max(largest, record_size(line))
    return largest


def opening_size(path: Path) -> int:
    """What a session's context weighed before it did anything: its first usage record.

    Not the first number the driver happens to poll — that one already includes whatever the
    session did in the first minute, and it moves with the poll interval. The reading set is what a
    handoff has to buy again, and it is written at the top of the transcript: measured over 104
    sessions of one run, a median of 45.5k with the quartiles at 45.3k and 45.8k.

    Zero when the head carries no usage record. Then `room` cannot be applied — `size - 0` clears
    any floor there is — and the ceiling decides alone, which is the deliberate behaviour and is
    what the tests hold. What must not also happen is silence: the caller says `floor-unreadable`
    into the run log once, because a guard that quietly stopped applying and a guard that had
    nothing to complain about would otherwise look identical.

    Measured over 186 sessions of two runs, the head carried a usage record every time, so this is
    a path that has never been taken rather than one that is taken often.
    """
    for line in read_head(path, lines=40).splitlines():
        size = record_size(line)
        if size:
            return size
    return 0


def handoff_due(size: int, floor: int, ceiling: int, room: int) -> bool:
    """Whether a session has grown enough that starting a new one is worth what it costs.

    A handoff is not free: the session that takes it pays the whole reading set again — the skill,
    the rules, the project's own instructions, the run file, the note — before it does anything.
    That floor is 45.7k written into a cold cache, and the session then spends **8 turns** getting
    back to where the last one stood: the median first `Edit` over 48 sessions that took a handoff,
    against 18 in a session starting from nothing. One cut therefore costs about 0.17M, once.

    **Eight, not forty.** The earlier figure counted transcript records rather than the model's own
    replies, and one reply with several content blocks is several records — a factor of ~1.9 on the
    turn axis, the same shape of defect as the doubled context above and on the other axis. The
    failure it was blamed for is not this trade: a session handing over eleven times in an hour came
    from the doubled counter putting the real trigger at 85.5k, which is barely past orienting.

    So the ceiling alone cannot decide it: what matters is how much this session did *of its own*,
    over the floor it started at. Both conditions, and a size that could not be read is not a small
    one. `room` binds only where the ceiling is below the floor plus `room` — see its own help.

    **What sets the ceiling is cost, and not the model's window.** Claude Opus 5 carries a 1M token
    window as both default and maximum, so nothing here is near a limit. The question is only where
    a segment is cheapest. A turn re-sends the whole context and reads it from cache at a tenth of
    the price, so a session's cost grows with the square of its turns; a cut pays the floor again
    and buys those 8 turns back.

    **Fitted over 119 ship sessions of two live runs**, a session of `n` turns costs
    `0.076M + 10.67k·n + 87·n²` and its context is `45.7k + 1.64k·n`. Checked against the observed
    medians of the same sessions, that curve is out by 4% on average; the curve this replaces —
    `0.48M + 5.3k·n + 75.6·n²`, with re-orientation at 40 — is out by 21%, and not evenly: it reads
    ~20% low across 130-190 turns, which is exactly the band where a ceiling is decided. That is
    what put its bottom at 144 turns and 282k, and the ceiling at 280.

    Priced over the real distribution of feature lengths of one run — 36 features, median 114 turns,
    p90 243 — the whole cost of building them lands like this:

        ceiling   130k   150k   170k   190k   210k   240k   280k   340k
        vs best  +0.4%     --  +1.0%  +2.7%  +4.9%  +7.4% +14.0% +18.6%

    The bottom is a plateau from 130k to 170k, and it is shallow: everything up to 190k is inside
    3%. **The ceiling is 210k** — off the bottom by a measured 5%, and set there deliberately as the
    next step of a live experiment: 280 was never compared with anything (300 → 280 is 0.8%, which
    no single night can resolve), and 210 against it is a difference a run can actually show. The
    number to go to if it holds is 160.

    **What this mechanism is worth is small, and knowing that matters more than the number.** The
    whole span from 130k to 280k is 14% of the feature children, which is ~10% of a run; between any
    two sensible values it is a few percent. A ceiling is a guard against a session growing without
    bound, not a way to save money. The larger numbers are elsewhere and are named in
    docs/design/2026-08-14-where-the-tokens-burn.md.

    The harness compacts by itself at about 83% of the window, which is where an uncontrolled
    version of this would happen anyway.

    **A project on a 200k-window model must lower this to about 130k.** There the harness would
    compact at ~166k and a 210k ceiling would never fire — the very failure this replaced, in the
    other direction.
    """
    if not size or ceiling <= 0:               # 0 is how the whole mechanism is turned off
        return False
    return size > ceiling * 1000 and size - floor >= room * 1000


def limit_reset(text: str) -> tuple[str, float | None]:
    """Classify the tail of a transcript: ('limit', when) | ('overloaded', None) | ('', None)."""
    if LIMIT_MARKER in text:
        match = RESET_RE.search(text)
        if not match:
            return "limit", None
        hour = int(match.group(1)) % 12
        minute = int(match.group(2) or 0)
        if (match.group(3) or "").lower() == "pm":
            hour += 12
        zone = None
        if match.group(4) and ZoneInfo is not None:
            try:
                zone = ZoneInfo(match.group(4))
            except Exception:                      # noqa: BLE001 - an unknown zone is not fatal
                zone = None
        now = dt.datetime.now(zone) if zone else dt.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += dt.timedelta(days=1)
        return "limit", target.timestamp()
    if OVERLOADED_MARKER in text:
        return "overloaded", None
    return "", None


# --------------------------------------------------------------------------------------------
# the owner's two instructions


def order_by_needs(children: list, needs_of: dict) -> tuple[list, list]:
    """The queue, re-sorted so nothing is built before what it needs.

    Stable: the order the composing session wrote survives everywhere the dependencies do not
    contradict it. That order is not arbitrary — an owner named it, and an `epic`'s gate puts the
    batch that makes a whole scenario walkable first — so it is the tie-break rather than something
    to be recomputed from scratch.

    A cycle cannot be sorted, and this returns the queue untouched and names the features caught in
    it rather than picking one of them to go first. Choosing silently would be this program forming
    an opinion out of input it could not read, and the run would look ordered.
    """
    order: list = []
    placed: set = set()
    left = list(children)
    while left:
        # One at a time, always the earliest that can go: taking every ready feature in a pass
        # would move independents ahead of a dependent that was written before them, which is a
        # reorder nothing asked for. Measured on ["a", "b", "c"] with b needing a: a pass-at-a-time
        # sort answers a, c, b.
        ready = next((slug for slug in left
                      if all(w in placed for w in needs_of.get(slug) or [])), None)
        if ready is None:
            return list(children), left
        order.append(ready)
        placed.add(ready)
        left.remove(ready)
    return order, []


def take_control(run: Run) -> str:
    """Read and clear the control file. The window writes it; the driver obeys between features."""
    path = run.dir / "control"
    if not path.is_file():
        return ""
    instruction = path.read_text(encoding="utf-8").strip()
    path.unlink(missing_ok=True)
    return instruction


# --------------------------------------------------------------------------------------------
# building one feature


class Driver:
    def __init__(self, run: Run, cwd: Path, options: argparse.Namespace):
        self.run = run
        self.cwd = cwd
        self.opt = options
        self.launcher = Launcher(cwd, options.model)
        self.skip: set[str] = set()
        self.stopping = False
        self.sessions = 0
        self.began = time.time()
        self.watched: str | None = None           # the session `watch` has live, numbered
        self.segments = 1                         # how many that run has needed so far

    @staticmethod
    def numbered(name: str, segment: int) -> str:
        """A run's first session carries its slug; each one that takes a handoff carries a number.

        The slug is trimmed rather than the number dropped: a name that collides is a session typed
        into by the driver that owns the *other* one, and `claude-new` takes letters, digits and
        dashes only.
        """
        return name[:60] if segment <= 1 else f"{name[:56]}-{segment}"

    # ---- the control window -----------------------------------------------------------------
    #
    # The driver raises no session for talking to the owner. The one they briefed the batch in is
    # already exactly that, and it knows why the batch looks the way it does — so it records its own
    # tmux name in the run file and stays. If it is gone, the run carries on without a narrator.

    WINDOW_RULE = ("[driver] you are this run's window: turn the lines below into one sentence for "
                   "the owner, decide nothing, investigate nothing, and never put a question to "
                   "them — the rule is rules/window.md, read it before you "
                   "answer anything")

    def tell(self, message: str) -> None:
        """News for the owner's window — and, once per driver, what a window is.

        The window was told its job hours ago, at a gate that has been compacted since; what
        survives is a path to a file, and a path is not a rule. A run reached this point, read the
        finished batch on its own initiative and asked the owner which of two things was wrong —
        the one shape `window.md` forbids, in the file it never opened. The reminder rides with the
        first news instead, where it costs one line and arrives at the moment it applies.
        """
        window = self.run.state().get("window")
        if not (window and self.launcher.alive_at(window)):
            return
        if not getattr(self, "_reminded", False):
            self._reminded = True
            self.launcher.send_to(window, self.WINDOW_RULE)
        self.launcher.send_to(window, f"[driver] {message}")

    # ---- watching one session ----------------------------------------------------------------

    @staticmethod
    def model_for(state: dict) -> str | None:
        """A run's own model, if it named one. Absent means the install's default."""
        model = (state or {}).get("model")
        return model.strip() if isinstance(model, str) and model.strip() else None

    def watch(self, name: str, run: Run, prompt: str, hand_over: bool = True) -> str:
        """Run a session until its run file goes terminal. Returns '' or why it did not.

        Every session the driver starts is watched the same way, the closing one included: an
        unbounded wait on a session that quietly died is how a night is lost without anyone
        noticing.

        `hand_over` is what differs. Handing a run to a fresh session is a rule of `ship` and of
        nothing else, so only a session that is building a feature is ever asked. The closing
        session has no next session to hand to — it reads every child once and writes one pull
        request — and asking it would restart the one session in the batch whose context cannot be
        rebuilt from the run files.
        """
        # Every session of this run has its own name, numbered: the first is the run's slug and the
        # one that takes a handoff is `-2`, `-3`. They used to share one name, and eleven sessions
        # deep into a live feature nothing on the machine, in the app, or in the log could say which
        # of them was speaking — the log line for the fourth handoff reads exactly like the first.
        current = self.numbered(name, 1)
        self.watched = current
        self.segments = 1
        model = self.model_for(run.state())
        if not self.launcher.start(current, prompt, model):
            return "could not start a session"
        self.sessions += 1

        # The stop hook matches a session to its run on this field and on nothing else, which is
        # what keeps it silent in every session the kit did not start. See docs/design/stop-hook.md.
        # Numbered names make this a *live* obligation: every handoff must write the new name here,
        # or the hook goes on guarding a session that is already dead.
        run.set(session=self.launcher.tmux_name(current))
        run.event("session-start", f"{current}{' on ' + model if model else ''}")
        launched = time.time() - 1
        transcript = None
        restarts = 0
        segment = 1                               # which session of this run is speaking
        floor = 0                                 # what its context started at, before it did anything
        nudged = False                            # one word before a restart, once per session
        asked = False                             # the handoff has been asked for, once per session
        blind = False                             # the floor could not be read, said once per session
        # The note as it stood when the handoff was asked for. Nothing ever clears `handoff`, so a
        # run that has already been handed over once carries a filled field for the rest of its
        # life — and "the note has landed" read as "the field is not empty" would fire instantly on
        # every handoff after the first, killing a live session and passing on a stale note.
        note_before = ""

        def fresh(why: str, event: str) -> bool:
            """Start this run's next session. Everything counted per session starts again with it."""
            nonlocal transcript, launched, nudged, asked, current, segment, floor, blind
            self.launcher.stop(current)
            transcript = None
            launched = time.time() - 1
            nudged = False
            asked = False
            blind = False
            floor = 0
            segment += 1
            current = self.numbered(name, segment)
            self.watched = current
            self.segments = segment
            if not self.launcher.start(current, prompt, self.model_for(run.state())):
                return False
            self.sessions += 1
            run.set(session=self.launcher.tmux_name(current))
            run.event(event, f"{why} — session {segment}")
            return True

        def restart(why: str) -> bool:
            nonlocal restarts
            restarts += 1
            if restarts > 1:
                return False
            return fresh(why, "restarted")

        while True:
            time.sleep(self.opt.poll)

            if run.terminal():
                return ""

            if transcript is None:
                transcript = newest_transcript(self.cwd, launched, run.slug)
                if transcript is None:
                    if time.time() - launched > 300:
                        return "no transcript — the session cannot be watched"
                    continue

            spoke = last_spoke(transcript)
            idle = time.time() - (spoke if spoke is not None else transcript.stat().st_mtime)
            gone = not self.launcher.alive(current)
            tail = read_tail(transcript)

            # The handoff the session was asked for has landed: the note is new, and the session has
            # stopped. Take it on to a session that starts near the floor again.
            note = (run.state().get("handoff") or "").strip()
            if asked and note and note != note_before and (gone or idle > self.opt.poll):
                if fresh(f"{run.slug} carried on in a new session", "handed-off"):
                    continue
                return "could not start the session that takes the handoff"

            if idle < self.opt.hang * 60 and not gone:
                # A healthy session, and its context has grown past what a session should carry.
                # One line, once: what to hand over and how is the session's own business, in
                # skills/ship/SKILL.md — this program only says when.
                size = context_size(tail)
                floor = floor or opening_size(transcript)   # the reading set, read once
                # A floor of nothing is not a floor: `room` stops applying and the ceiling decides
                # alone. That is the behaviour, and it is fine — what is not fine is doing it
                # quietly, because then a guard that lapsed reads exactly like a guard with nothing
                # to say. Once per session, in the log the driver already keeps.
                if hand_over and not blind and not floor and size:
                    blind = True
                    run.event("floor-unreadable",
                              f"no opening usage record — `room` cannot apply and the ceiling of "
                              f"{self.opt.ceiling}k decides this session alone")
                if hand_over and not asked and handoff_due(size, floor, self.opt.ceiling,
                                                           self.opt.room):
                    if self.launcher.send(current, HANDOFF_LINE):
                        asked = True
                        note_before = note
                        # Logged with the minutes so the numbers behind the ceiling stop being an
                        # estimate: floor, size and how long the segment lasted are what a later
                        # reading needs to fit the growth per turn and price a run's segments.
                        run.event("handoff-asked",
                                  f"context {size // 1000}k over a floor of {floor // 1000}k "
                                  f"after {(time.time() - launched) / 60:.0f}m")
                continue

            # Something stopped. Silence alone means nothing — ask the transcript why.
            kind, when = limit_reset(tail)

            if kind == "limit":
                wait = (when - time.time()) if when else self.opt.poll * 5
                if wait > self.opt.max_wait * 3600:
                    self.stopping = True
                    self.tell(f"{run.slug}: a weekly limit, not a session one — stopping the run")
                    return f"limit resets in {wait / 3600:.1f}h"
                if wait > 0:
                    run.event("limit", f"sleeping {wait / 60:.0f}m")
                    self.tell(f"{run.slug}: limit reached, waiting {wait / 60:.0f} min for the reset")
                    time.sleep(wait + 60)
                # A limit does not kill the process: it is idle with its context intact, so one
                # typed line resumes it and nothing is re-read.
                if self.launcher.alive(current) and self.launcher.send(current, "continue"):
                    run.event("resumed", "typed into the live session")
                    continue
                if restart("session was gone after the limit"):
                    continue
                return "did not come back after the limit"

            if kind == "overloaded" and not gone:
                run.event("overloaded", "retrying shortly")
                time.sleep(120)
                self.launcher.send(current, "continue")
                continue

            why = "session died" if gone else f"no progress for {idle / 60:.0f}m"

            # A session that is still up has simply ended its turn — most often one step short of
            # the terminal one, because ending a turn and finishing a run are different things and
            # nothing in the harness ties them together. Its context is intact, so the same line
            # that resumes a session after a limit resumes this one: one word against a restart
            # that throws away everything it read. Only a session that will not move on that word,
            # or one that is gone, is worth rebuilding from nothing.
            if not gone and not nudged and self.launcher.send(current, "continue"):
                nudged = True
                run.event("nudged", f"{why} — typed into the live session")
                time.sleep(self.opt.poll)
                continue

            run.event("stalled", why)
            if restart(why):
                continue
            return why

    # ---- one child --------------------------------------------------------------------------

    def build(self, child: Run) -> str:
        # The child's slug already carries the batch's, and it is what the owner sees in the app.
        name = child.slug[:60]
        # Handing a run on is a rule of `ship` alone: asking anything else to hand over sends it to
        # a section of a file it never read, and there is no next session to take it. Which is which
        # comes from `runfile.kind` — a child whose kind nothing can work out is not asked, because
        # that is the harmless half of being wrong.
        why = self.watch(name, child, self.prompt_for(child),
                         hand_over=runfile.kind(child.state()) == "feature")
        self.launcher.stop(self.watched or name)
        # What this feature cost, on the feature itself. The batch's total says 1.67 sessions per
        # feature and hides the shape: on a measured batch one feature took four while three took
        # one each, and it was the one where a person's action and a background job had been
        # composed into a single child. Per feature, that is visible; averaged, it is not — and the
        # frame child of the next batch is the reader, deciding what to split before anything is
        # built.
        # Merged, not replaced: `hours` and `features` are the child's own to write, and a fresh
        # dict here drops them. The batch's `record_spend` keeps all three; this path is the one
        # that did not.
        spent = dict(child.state().get("spent") or {})
        spent["sessions"] = max(int(spent.get("sessions") or 0), self.segments)
        child.set(spent=spent)

        # Judge by the world, not by the exit: a limit at the tail of a feature looks exactly like a
        # crash while the work is already done.
        state = child.state()
        if child.own_pr(state) or state.get("step") == "done":
            self.audit(child, state)
            self.costly(child, state)
            child.event("built", state.get("branch") or "")
            return "built"
        branch = state.get("branch")
        if branch and self.branch_pushed(branch):
            child.set(step="done")
            child.event("built", f"{branch} — found pushed, the run file was behind")
            return "built"
        child.set(step="blocked")
        child.event("blocked", why or "no terminal state")
        return "blocked"

    @staticmethod
    def prompt_for(child: Run) -> str:
        """What gets typed into this child's session.

        `ship` unless the run file says otherwise. It said otherwise for the first time on a live
        `epic`: the audit is not a `ship`, so the driver could not start it, and the session that
        wanted one wrote a shell script into the run directory to launch it by hand and another to
        hand control back. A mechanism nobody declared, in a directory nothing tracks — and every
        limit, stall and restart this program handles was outside it.

        A child that is not a `ship` keeps everything else: its own run file, and a terminal `step`
        as the signal it finished. Whoever writes `prompt` writes that instruction into it, because
        a command with no run file of its own will not close one by accident.
        """
        prompt = (child.state().get("prompt") or "").strip()
        return prompt or f"/agent-kit:ship --run {child.dir}"

    def audit(self, child: Run, state: dict) -> None:
        """What a run closed with that it should not have.

        The branch is pushed and reviewed either way, so this does not park the feature and lose the
        rest of the night: it writes the defect into `blockers`, which the closing session reads and
        names in the pull request. A hole a batch reports is recoverable; one nobody noticed is not.

        The batch's own closing goes through here too. Its one rule that a child cannot break is the
        durable record in `docs/runs/`, which the closing session writes and nothing else would
        notice the absence of — `.agent-kit/runs/` dies with the machine.
        """
        defects = run_defects(state, self.cwd)
        if not defects:
            return
        child.set(blockers=(state.get("blockers") or []) + defects)
        child.event("closed-with-defects", "; ".join(defects))
        self.tell(f"{child.slug} closed with {len(defects)} thing(s) it should not have: {defects[0]}")

    def costly(self, child: Run, state: dict) -> None:
        """The decisions this child took with nobody there, said while the night is still running.

        `assumptions[].expensive` has been written by every `ship` since the field existed and read
        by nothing — a record with a writer and no reader, which by this kit's own rule is a defect
        and not a spare field. The owner meets these in the morning, in a pull request that on one
        measured run carried seventy of them, while the channel to their phone was open all night.

        One line per child, the expensive ones only, and **no way back**. An answer cannot be
        applied to a decision the child has already built on, and a run that stands still for one
        was measured twice arriving exactly where it would have arrived without waiting — which is
        why `wait` was cut in 2.5.0 and is not being rebuilt here. What this buys is the hours
        between the decision and the morning: the owner can stop the run, skip what is behind it, or
        type into the session themselves, all of which they can only do while it is still running.
        """
        costly = [a for a in (state.get("assumptions") or [])
                  if isinstance(a, dict) and a.get("expensive")]
        if not costly:
            return
        first = " ".join(str(costly[0].get("what") or "").split())[:120] or "unnamed"
        self.tell(f"{child.slug} took {len(costly)} decision(s) with nobody to ask that are "
                  f"expensive to reverse — first: {first}")

    def apply_frame(self, child: Run, state: dict) -> None:
        """Take the frame child's map of what needs what, and make it the queue.

        The map is judgement and belongs to a session; ordering a list by it is arithmetic and
        belongs here. That split is also what keeps ownership intact: a `ship` may not write another
        run's file, and this program already writes `step` into every child, so it is the one thing
        present that is allowed to write `needs` as well.

        Applied once, when that child is built — and applying it twice changes nothing, which is
        what `--resume` needs. A feature the map does not mention gets `[]` rather than being left
        alone: the child was asked about the whole batch, so silence about one of them is an answer.
        """
        frame = state.get("frame")
        if not isinstance(frame, dict) or not frame:
            # Only where one was owed. A frame child that wrote its prose and forgot the map would
            # otherwise close green and leave the batch on the fallback, which is indistinguishable
            # from a batch where nothing depends on anything.
            # Both forms: `--frame <dir>` is what a batch writes now, and `frame.md` is what run
            # files written before 2.15.0 carry. A `--resume` reads those, and reading one as an
            # ordinary child would drop the defect this line exists to report.
            if re.search(r"--frame\b|frame\.md", state.get("prompt") or ""):
                self.note_defect(f"{child.slug} left no `frame` map, so no feature knows what it "
                                 f"needs and the batch falls back to the queue order")
            return
        children = self.run.state().get("children") or []
        known = set(children)
        rest = [slug for slug in children if slug != child.slug]

        needs_of = {}
        for slug in rest:
            run = Run(self.run.dir.parent / slug)
            # A slug in `children` with no file of its own is a hole the loop already reports.
            # Writing `needs` into it would create the file, and the driver would then start a
            # session on a run that names no feature and carries no task.
            if not run.file.is_file():
                continue
            written = run.state().get("needs")
            if isinstance(written, list):
                # The composing session had the owner in front of it. This map was made overnight.
                needs_of[slug] = [w for w in written if w in known]
                continue
            wants = frame.get(slug)
            # Never this feature and never the frame child: it is built before all of them, so
            # naming it is true and useless, and it is not in the list being sorted.
            wants = ([w for w in wants if w in rest and w != slug]
                     if isinstance(wants, list) else [])
            needs_of[slug] = wants
            run.set(needs=wants)

        # A name outside this batch is the one thing the map can say that nothing can act on. It is
        # dropped above — a slug with no run file cannot be waited for — and said out loud here,
        # because a dependency the driver ignored is exactly what nobody would go looking for.
        named = set(frame) | {w for wants in frame.values() if isinstance(wants, list) for w in wants}
        stray = sorted(named - known)

        order, cycle = order_by_needs(rest, needs_of)
        self.run.set(children=[child.slug] + order)
        child.event("frame", f"{len(rest)} features ordered")

        defects = []
        if cycle:
            defects.append(f"{child.slug} made these features need each other in a circle, so the "
                           f"queue was left in the order it was written: {', '.join(cycle)}")
        if stray:
            defects.append(f"{child.slug} named features that are not in this batch, and they were "
                           f"ignored: {', '.join(dict.fromkeys(stray))}")
        for line in defects:
            self.note_defect(line)

    def note_defect(self, line: str) -> None:
        """Something the batch has to carry to the pull request, found by this program.

        Into `blockers` of the batch's own file, because the closing session reads run files and
        never this program's log — and a defect nobody reads is the shape of every hole this kit
        has already paid for.
        """
        self.run.set(blockers=(self.run.state().get("blockers") or []) + [line])
        self.run.event("frame-defect", line)
        self.tell(line)

    def chain(self, child: Run, last: Run | None, batch_base: str | None) -> None:
        """Point this child at the last feature that was actually built.

        Written by the composing session as *the one before it in the list*, `base` names a branch
        that may not exist: a batch whose second feature is blocked would have every feature after
        it branch off nothing. The chain is what makes integration a property rather than a step, so
        it is kept — it just runs through what was built rather than through what was planned.
        """
        state = child.state()
        base = (last.state().get("branch") if last else None) or batch_base
        if not base:
            # Nothing to point at and nothing pointed at it: the composing session left this batch
            # no base, so whatever is in the child's own file is all there is. Said rather than
            # left, because a stale `base` here is a feature branching off a branch nobody pushed.
            self.note_defect(f"{child.slug} was started with no base to chain onto — this batch's "
                             f"run file has no `base`, so it is building on {state.get('base')!r}")
            return
        if state.get("base") == base and state.get("parent") == (last.slug if last else None):
            return
        child.set(base=base, parent=last.slug if last else None)

    def branch_pushed(self, branch: str) -> bool:
        done = subprocess.run(["git", "ls-remote", "--heads", "origin", branch],
                              cwd=self.cwd, capture_output=True, text=True)
        return done.returncode == 0 and bool(done.stdout.strip())

    # ---- the batch --------------------------------------------------------------------------

    def go(self) -> int:
        state = self.run.state()
        children = state.get("children") or []
        if not children:
            # Nothing to build, and this program is the only thing running: without the hand-back
            # an `epic` whose next step was started on the wrong file stops here in silence, and
            # only `--resume` finds it. Judgement about what that means belongs to the session
            # above; saying so is this program's job.
            # Written before the hand-back, because a batch left at the step it was composed at is
            # one the advance session cannot tell from a batch nobody started yet — and it decides
            # what follows by reading exactly that field.
            self.run.set(step="blocked")
            self.run.event("empty", "no children to build — handing back")
            self.tell(f"{self.run.slug} has no children to build")
            self.hand_back(state)
            return 1

        # The session that started this driver has nothing left to do — its own product is this
        # process running. It is told to close itself last, and measured on a live run it never
        # did: the instruction sits at the end of a section, after the work is finished, which is
        # where instructions go to be forgotten. So the driver closes it, and knows which one it is
        # from `parent`. Safe because the driver is started under `nohup` and ignores the SIGHUP
        # that killing a session sends — `setsid` would do the same and does not exist on macOS.
        # Nothing depends on the kill working — a session left standing is reclaimed by
        # the next hand-back, which is what happened for every batch before this line existed.
        parent = state.get("parent")
        if parent:
            self.launcher.stop(f"{parent}-advance"[:60])

        self.run.set(step="building")
        self.run.event("start", f"{len(children)} features")
        window = state.get("window")
        self.run.event("window", window or "none — the run will have no narrator")

        built = 0
        seen: set = set()
        last: Run | None = None                   # the last feature actually built: the chain's tip
        # What the composing session wrote as each child's `parent`, read before this loop moves
        # any of them. It is the fallback for a child with no `needs`, and it has to be the
        # authored value: `chain()` rewrites `parent` as the run goes, so reading it later would
        # answer with the tip of the chain — which is always built, and would never skip anything.
        authored = {slug: Run(self.run.dir.parent / slug).state().get("parent")
                    for slug in children}
        while True:
            # `children` is the queue, and it is read again here rather than taken as a snapshot:
            # a session between features may reorder what is left, drop something, or add a batch
            # of fixes it decided is needed. Nothing else is the queue — there is no second file to
            # disagree with this one. What has already run is remembered here instead, so a list
            # that changed under the loop cannot make it build the same feature twice.
            children = self.run.state().get("children") or []
            remaining = [slug for slug in children if slug not in seen]
            if not remaining:
                break
            slug = remaining[0]
            seen.add(slug)

            # Read before the missing-file check below: `control` is the owner's one lever, and
            # skipping it because the head of the queue has no run file loses a `stop` written
            # while that head was current — the file is not deleted either, so the owner watching
            # it sit there gets no signal at all.
            instruction = take_control(self.run)
            if instruction.startswith("skip"):
                target = instruction.split(None, 1)[1].strip() if " " in instruction else slug
                self.skip.add(target)
                self.run.event("control", f"skip {target}")
            elif instruction == "stop":
                self.run.event("control", instruction)
                self.stopping = True
            elif instruction:
                # The file is read and deleted whatever it says. An instruction nobody recognised
                # would then vanish exactly like one that was obeyed, and the owner — who watched
                # the file disappear — would believe it was.
                self.run.event("control", f"not recognised, ignored: {instruction[:60]}")
                self.tell(f"the instruction in `control` was not recognised and did nothing: "
                          f"{instruction[:60]} — the two words are `skip <slug>` and `stop`")

            child = Run(self.run.dir.parent / slug)
            if not child.file.is_file():
                self.run.event("missing", f"{slug} has no run file")
                continue

            # Asked before `stopping`, and that order is the whole point: a child a previous pass
            # closed `done` must not be overwritten `skipped` because the owner stopped the batch
            # or a weekly limit did. Written the other way round the feature reads as never built,
            # `terminal()` still answers True so nothing rebuilds it, and its branch sits in the
            # repository with nothing pointing at it.
            if child.terminal():
                self.run.event("already-terminal", slug)
                if child.state().get("step") == "done":
                    built += 1
                    last = child
                    self.apply_frame(child, child.state())
                continue

            if self.stopping:
                child.set(step="skipped")
                continue

            # A child that is not a feature — the frame child, an audit between two waves — has
            # nothing built on it, so it is never anybody's dependency and its failure cascades to
            # nobody. Without this the batch opens with its own most fragile link: a frame child
            # whose session died would skip every feature behind it, which is the exact failure
            # that release was written to end.
            #
            # Asked of `runfile.kind`, which every reader of a run file now asks. It used to be
            # *does this child carry a prompt*, and that made a feature whose prompt was typed out
            # — the very line the template offers as its default — into an errand: nothing behind
            # it was skipped when it failed, though everything behind it was built on it.
            state_of = child.state()
            errand = runfile.kind(state_of) != "feature"

            # What this feature cannot be built without. `[]` is somebody's answer; the field
            # missing altogether is nobody's, and then the fallback is the `parent` the composing
            # session wrote — which is what a chained batch has meant since it was written, and is
            # read from the snapshot above so this run's own rewrites cannot answer it.
            needs = state_of.get("needs")
            if not isinstance(needs, list):
                if slug not in authored:          # added to the queue while the batch was running
                    authored[slug] = state_of.get("parent")
                needs = [authored[slug]] if authored[slug] else []
            missing = [n for n in needs if n in self.skip]
            if slug in self.skip or missing:
                self.skip.add(slug)               # and whatever needs this one follows it
                child.set(step="skipped")
                self.run.event("skipped", f"{slug} — needs {', '.join(missing)}" if missing else slug)
                continue

            self.chain(child, last, state.get("base"))
            self.tell(f"starting {slug}")
            if self.build(child) == "built":
                built += 1
                last = child
                self.apply_frame(child, child.state())
            elif not errand:
                self.skip.add(slug)

        self.run.set(step="closing")
        self.run.event("children-done", f"{built}/{len(seen)} built")
        self.record_spend(built)
        self.close()
        return 0

    def record_spend(self, built: int) -> None:
        """What this batch cost in the units an owner can use: hours, features, sessions.

        The gate of an `epic` prices its scope out of a number written in prose, and on the run this
        was added for that number was four times under. Nothing fed a measurement back into it,
        because nothing measured. This does — accumulating, so a batch picked up by `--resume` adds
        to what the first pass spent rather than replacing it.

        Not tokens and not money: the owner cannot forecast either, and said so. Wall-clock and the
        count of what was built are what a person can hold against a plan.
        """
        before = self.run.state().get("spent") or {}
        hours = float(before.get("hours") or 0) + (time.time() - self.began) / 3600
        self.run.set(spent={"hours": round(hours, 1),
                            "features": int(before.get("features") or 0) + built,
                            "sessions": int(before.get("sessions") or 0) + self.sessions})

    def close(self) -> None:
        """A pull request is judgement, so a session writes it — not this program."""
        name = f"{self.run.slug}-close"[:60]
        why = self.watch(name, self.run, f"/agent-kit:sprint --close {self.run.dir}",
                         hand_over=False)
        self.launcher.stop(self.watched or name)

        # Judge the closing session by its step first. Inside an `epic` the batch's `pr` is the run's
        # one pull request, which the closing session rewrites rather than opens — so it is there
        # whether or not this batch was closed, and reading it as proof is what killed two closings.
        state = self.run.state()
        if state.get("step") in TERMINAL_STEPS or self.run.own_pr(state):
            self.run.set(step="done")
            self.run.event("done", f"pr={state.get('pr')}")
            self.audit(self.run, self.run.state())
            self.tell(f"the batch is finished, pull request {state.get('pr')}")
            self.hand_back(state)
            return
        self.run.set(step="blocked")
        self.run.event("close-failed", why or "the closing session left no terminal step")
        self.tell("the features are built and pushed, but the batch was never closed — its branch, "
                  "its pull request body and its digest need finishing by hand")
        self.hand_back(state)

    def hand_back(self, state: dict) -> None:
        """A batch inside a longer run tells that run it is finished, and this program stops.

        An `epic` is batches one after another, and something has to decide what the next one is —
        which is judgement, so it is a session. This launches it and does not watch it: the session's
        own product is another driver running, and there is no state of its own to wait for. If it
        dies before starting one, the run stops where it stands and `--resume` picks it up, which is
        the same recovery every other stall has.
        """
        parent = state.get("parent")
        if not parent:
            return
        above = Run(self.run.dir.parent / parent)
        # `mvp` is what this command was called before 2.0.0. A run file on disk outlives the
        # rename, and a run half-finished under the old name still has to be handed back.
        if above.state().get("command") not in ("epic", "mvp"):
            return
        name = f"{above.slug}-advance"[:60]
        self.run.event("hand-back", f"{parent} decides what follows")
        started = self.launcher.start(name, f"/agent-kit:epic --advance {above.dir}",
                                      self.model_for(above.state()))
        # The session that decides what follows is the one session here nothing else can close.
        # The driver it may start closes it (`go`, above); the driver that started it — this one —
        # exits at the hand-back. So when the run it is deciding about turns out to be finished,
        # there is no next driver and the session stands until somebody notices it, which on a
        # measured run took eight hours. Writing its name here is what lets the stop hook close it:
        # the hook matches a session to its run on this field and on nothing else.
        if started:
            above.set(session=self.launcher.tmux_name(name))
        if self.launcher.reclaimed:
            above.event("reclaimed", f"{name} was still up from an earlier batch — closed it first")
        if not started:
            above.event("stalled", "could not start the session that decides the next batch")
            self.tell(f"{above.slug} needs /agent-kit:epic --resume — the next batch did not start")


# --------------------------------------------------------------------------------------------


def project_root(run_dir: Path) -> Path:
    for parent in run_dir.resolve().parents:
        if parent.name == ".agent-kit":
            return parent.parent
    return Path.cwd()


# --------------------------------------------------------------------------------------------
# outliving the session that started this driver
#
# A session starts the driver as a background process of its own shell, and then that session is
# closed — by the driver itself at the top of `go`, and, before 2.26.0, by an instruction the
# session was given in prose. `nohup` was believed to make that safe, and the comment saying so
# stood for a week.
#
# It is not safe. tmux 3.4 puts every pane in a systemd scope of its own, that scope's KillMode is
# `control-group`, and closing the pane takes down everything started from it. `nohup` only ignores
# SIGHUP; the scope's teardown is not a SIGHUP. **`setsid` does not help either** — a new session id
# is not a new control group, which is what the old comment offered as the portable equivalent.
# Measured on this machine: a plain `nohup` child and a `setsid nohup` child both report the pane's
# own `tmux-spawn-….scope`.
#
# What made this survivable until 19 August was that the session usually forgot to close itself: the
# instruction sat after the closing report, and one `epic`'s session from 17 August was still
# standing two days later. The night it did remember, the driver wrote two lines and died with it —
# four features queued, nothing started, and no message anywhere, because the launch line sends the
# driver's output to /dev/null.
#
# So the driver moves itself out of that control group before it does anything. Where systemd is not
# there to move into, it says so and carries on: a driver that runs and can be killed by its parent
# is better than no driver, and a silence here would be the same defect in a new place.

DETACHED = "AGENT_KIT_DRIVER_DETACHED"


def own_cgroup(path: Path = Path("/proc/self/cgroup")) -> str:
    """This process's control group, or `""` where the kernel does not publish one (macOS)."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def dies_with_its_session(cgroup: str) -> bool:
    """Whether this process would be killed by the closing of the pane that started it."""
    return "tmux-spawn" in cgroup and ".scope" in cgroup


def unit_name(slug: str) -> str:
    """A systemd unit name for this run. Slugs are dated feature names; units take a narrow set."""
    safe = re.sub(r"[^A-Za-z0-9-]", "-", slug)[:60].strip("-") or "run"
    return f"agent-kit-{safe}"


def detach_command(run_dir: Path, argv: list[str], runner: str) -> list[str]:
    """The command that starts this driver again, as a service of its own.

    `--collect` so a finished run does not leave a unit behind that the next one collides with, and
    the environment flag so the driver that comes up knows not to do this again.

    **`PATH` is carried across, and it is not optional.** A transient unit starts from the systemd
    user manager's environment, not from the shell's: measured here, that is
    `/usr/local/sbin:…:/snap/bin` and nothing else. The first driver to move itself out lost
    `~/.local/bin` with it, so `claude-new` was not on the path, no session could be started, and
    four features went to `blocked` in twenty seconds — the same night failing in a new way. It goes
    in `--setenv` rather than through the manager's own environment because this must hold for a
    driver started from anywhere, including a cron job or an ssh command.
    """
    return [runner, "--user", "--collect", "--quiet", f"--unit={unit_name(run_dir.name)}",
            f"--setenv={DETACHED}=1", f"--setenv=PATH={os.environ.get('PATH', '')}",
            f"--working-directory={Path.cwd()}",
            sys.executable or "python3", str(Path(__file__).resolve()), *argv]


def detach(run_dir: Path, argv: list[str]) -> tuple[str, str]:
    """Move this driver into a service of its own. Returns `(unit, "")` or `("", why not)`."""
    runner = shutil.which("systemd-run")
    if not runner:
        return "", "systemd-run is not on the path"
    command = detach_command(run_dir, argv, runner)
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return "", f"systemd-run did not finish: {exc}"
    if done.returncode != 0:
        return "", (done.stderr.strip() or done.stdout.strip()
                    or f"systemd-run exited {done.returncode} and said nothing")
    return unit_name(run_dir.name), ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path, help=".agent-kit/runs/<slug>/ of the batch")
    parser.add_argument("--poll", type=int, default=60, help="seconds between looks at the run file")
    parser.add_argument("--hang", type=int, default=30, help="minutes of transcript silence before a session is treated as stuck")
    parser.add_argument("--ceiling", type=int, default=210,
                        help="thousands of tokens: a session past this is asked to hand its run "
                             "over to a fresh one. What sets it is cost, not the model's window — "
                             "see handoff_due. 0 turns it off")
    parser.add_argument("--room", type=int, default=40,
                        help="thousands of tokens a session must have grown by, over the context it "
                             "started with, before the ceiling above can send it away. A safety net "
                             "rather than a lever: with a floor of ~46k it binds only where the "
                             "ceiling is under ~86k, which is a ceiling set by mistake")
    parser.add_argument("--max-wait", type=float, default=6, help="hours: a reset further away than this is a weekly limit, and the run stops")
    parser.add_argument("--model", default=None,
                        help="model for every session this run starts, unless its run file names "
                             "one of its own")
    options = parser.parse_args(argv)

    run_dir = options.run_dir.resolve()
    if not (run_dir / "run.json").is_file():
        print(f"no run file in {run_dir}", file=sys.stderr)
        return 1

    # Before anything else, and before this run's file is touched: the process that gets to watch
    # the night must not be the one the session can take with it. See the section above.
    if os.environ.get(DETACHED) != "1" and dies_with_its_session(own_cgroup()):
        unit, why = detach(run_dir, list(argv) if argv is not None else sys.argv[1:])
        if unit:
            print(f"driver moved out of its session's control group as {unit} — "
                  f"`journalctl --user -u {unit}` has its output")
            Run(run_dir).event("detached", unit)
            return 0
        print(f"could not move this driver out of its session's control group ({why}), so it is "
              f"running inside it: closing the session that started it will kill this driver and "
              f"the night stops where it stands", file=sys.stderr)
        Run(run_dir).event("detach-failed", why)

    # One visible session per feature is what makes a stalled child rescuable by hand and a limit
    # recoverable by typing into it. Without a multiplexer there is no such session, and a traceback
    # is a poor way to say so on a machine that simply has not installed one.
    if not shutil.which("tmux"):
        print("tmux is not installed, and it is what gives every feature its own visible session.\n"
              "Install it, or build features one at a time with /agent-kit:ship, which needs none.",
              file=sys.stderr)
        return 1

    run = Run(run_dir)
    cwd = project_root(run_dir)

    # Two drivers over one working tree is how a night ends with commits in the wrong branch. The
    # previous generation of this program could do it, because liveness was read from a log written
    # only at exit; a live tmux session is the fact itself.
    driver = Driver(run, cwd, options)
    for slug in run.state().get("children") or []:
        child = Run(run_dir.parent / slug)
        if child.file.is_file() and not child.terminal() and driver.launcher.alive(slug[:60]):
            print(f"{slug} still has a live session — another driver is already on this run",
                  file=sys.stderr)
            return 1
    return driver.go()


if __name__ == "__main__":
    sys.exit(main())
