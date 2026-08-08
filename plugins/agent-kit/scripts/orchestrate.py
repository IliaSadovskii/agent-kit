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

TERMINAL_STEPS = {"done", "blocked", "skipped"}
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

    def terminal(self) -> bool:
        state = self.state()
        return bool(state.get("pr")) or state.get("step") in TERMINAL_STEPS


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

    def _tmux(self, *args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(["tmux", *args], capture_output=True, text=True)
        except FileNotFoundError:                 # checked once in main(); this is the belt
            return subprocess.CompletedProcess(args, 127, "", "tmux is not installed")

    def tmux_name(self, name: str) -> str:
        return f"cc-{name}" if self.helper else f"agent-kit-{name}"

    def start(self, name: str, prompt: str, model: str | None = None) -> bool:
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
        if self.helper and self.closer:
            subprocess.run([self.closer, name], capture_output=True, text=True)
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


def newest_transcript(cwd: Path, after: float) -> Path | None:
    directory = transcript_dir(cwd)
    if not directory.is_dir():
        return None
    fresh = [p for p in directory.glob("*.jsonl") if p.stat().st_mtime >= after]
    return max(fresh, key=lambda p: p.stat().st_mtime, default=None)


def read_tail(path: Path, lines: int = 40) -> str:
    """Last lines of a file, without reading a transcript that can be hundreds of megabytes."""
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 200_000))
            text = fh.read().decode("utf-8", errors="replace")
        return "\n".join(text.splitlines()[-lines:])
    except OSError:
        return ""


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
# the owner's three instructions


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

    # ---- the control window -----------------------------------------------------------------
    #
    # The driver raises no session for talking to the owner. The one they briefed the batch in is
    # already exactly that, and it knows why the batch looks the way it does — so it records its own
    # tmux name in the run file and stays. If it is gone, the run carries on without a narrator.

    def tell(self, message: str) -> None:
        window = self.run.state().get("window")
        if window and self.launcher.alive_at(window):
            self.launcher.send_to(window, f"[driver] {message}")

    # ---- watching one session ----------------------------------------------------------------

    @staticmethod
    def model_for(state: dict) -> str | None:
        """A run's own model, if it named one. Absent means the install's default."""
        model = (state or {}).get("model")
        return model.strip() if isinstance(model, str) and model.strip() else None

    def watch(self, name: str, run: Run, prompt: str) -> str:
        """Run a session until its run file goes terminal. Returns '' or why it did not.

        Every session the driver starts is watched the same way, the closing one included: an
        unbounded wait on a session that quietly died is how a night is lost without anyone
        noticing.
        """
        model = self.model_for(run.state())
        if not self.launcher.start(name, prompt, model):
            return "could not start a session"

        run.event("session-start", f"{name}{' on ' + model if model else ''}")
        launched = time.time() - 1
        transcript = None
        restarts = 0

        def restart(why: str) -> bool:
            nonlocal transcript, launched, restarts
            restarts += 1
            if restarts > 1:
                return False
            self.launcher.stop(name)
            transcript = None
            launched = time.time() - 1
            if not self.launcher.start(name, prompt, self.model_for(run.state())):
                return False
            run.event("restarted", why)
            return True

        while True:
            time.sleep(self.opt.poll)

            if run.terminal():
                return ""

            if transcript is None:
                transcript = newest_transcript(self.cwd, launched)
                if transcript is None:
                    if time.time() - launched > 300:
                        return "no transcript — the session cannot be watched"
                    continue

            idle = time.time() - transcript.stat().st_mtime
            gone = not self.launcher.alive(name)
            if idle < self.opt.hang * 60 and not gone:
                continue

            # Something stopped. Silence alone means nothing — ask the transcript why.
            kind, when = limit_reset(read_tail(transcript))

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
                if self.launcher.alive(name) and self.launcher.send(name, "continue"):
                    run.event("resumed", "typed into the live session")
                    continue
                if restart("session was gone after the limit"):
                    continue
                return "did not come back after the limit"

            if kind == "overloaded" and not gone:
                run.event("overloaded", "retrying shortly")
                time.sleep(120)
                self.launcher.send(name, "continue")
                continue

            why = "session died" if gone else f"no progress for {idle / 60:.0f}m"
            run.event("stalled", why)
            if restart(why):
                continue
            return why

    # ---- one child --------------------------------------------------------------------------

    def build(self, child: Run) -> str:
        # The child's slug already carries the batch's, and it is what the owner sees in the app.
        name = child.slug[:60]
        why = self.watch(name, child, f"/agent-kit:ship --run {child.dir}")
        self.launcher.stop(name)

        # Judge by the world, not by the exit: a limit at the tail of a feature looks exactly like a
        # crash while the work is already done.
        state = child.state()
        if state.get("pr") or state.get("step") == "done":
            self.audit(child, state)
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

    def audit(self, child: Run, state: dict) -> None:
        """What a child closed with that it should not have.

        The branch is pushed and reviewed either way, so this does not park the feature and lose the
        rest of the night: it writes the defect into `blockers`, which the closing session reads and
        names in the pull request. A hole a batch reports is recoverable; one nobody noticed is not.
        """
        defects = run_defects(state)
        if not defects:
            return
        child.set(blockers=(state.get("blockers") or []) + defects)
        child.event("closed-with-defects", "; ".join(defects))
        self.tell(f"{child.slug} closed with {len(defects)} thing(s) it should not have: {defects[0]}")

    def branch_pushed(self, branch: str) -> bool:
        done = subprocess.run(["git", "ls-remote", "--heads", "origin", branch],
                              cwd=self.cwd, capture_output=True, text=True)
        return done.returncode == 0 and bool(done.stdout.strip())

    # ---- the batch --------------------------------------------------------------------------

    def go(self) -> int:
        state = self.run.state()
        children = state.get("children") or []
        if not children:
            self.run.event("empty", "no children to build")
            return 1

        self.run.set(step="building")
        self.run.event("start", f"{len(children)} features")
        window = state.get("window")
        self.run.event("window", window or "none — the run will have no narrator")

        built = 0
        for slug in children:
            child = Run(self.run.dir.parent / slug)
            if not child.file.is_file():
                self.run.event("missing", f"{slug} has no run file")
                continue

            instruction = take_control(self.run)
            if instruction.startswith("skip"):
                target = instruction.split(None, 1)[1].strip() if " " in instruction else slug
                self.skip.add(target)
                self.run.event("control", f"skip {target}")
            elif instruction == "stop":
                self.run.event("control", instruction)
                self.stopping = True

            if self.stopping:
                child.set(step="skipped")
                continue

            if child.terminal():
                self.run.event("already-terminal", slug)
                if child.state().get("step") == "done":
                    built += 1
                continue

            parent = child.state().get("parent")
            if slug in self.skip or (parent and parent in self.skip):
                self.skip.add(slug)               # descendants of a skipped feature follow it
                child.set(step="skipped")
                self.run.event("skipped", f"{slug} — parent {parent}" if parent else slug)
                continue

            self.tell(f"starting {slug}")
            if self.build(child) == "built":
                built += 1
            else:
                self.skip.add(slug)

        self.run.set(step="closing")
        self.run.event("children-done", f"{built}/{len(children)} built")
        self.close()
        return 0

    def close(self) -> None:
        """A pull request is judgement, so a session writes it — not this program."""
        name = f"{self.run.slug}-close"[:60]
        why = self.watch(name, self.run, f"/agent-kit:sprint --close {self.run.dir}")
        self.launcher.stop(name)

        state = self.run.state()
        if state.get("pr"):
            self.run.set(step="done")
            self.run.event("done", f"pr={state.get('pr')}")
            self.tell(f"the batch is finished, pull request {state.get('pr')}")
            self.hand_back(state)
            return
        self.run.set(step="blocked")
        self.run.event("close-failed", why or "no pull request")
        self.tell("the features are built and pushed, but the batch has no pull request — it needs one by hand")
        self.hand_back(state)

    def hand_back(self, state: dict) -> None:
        """A batch inside a longer run tells that run it is finished, and this program stops.

        An `mvp` is batches one after another, and something has to decide what the next one is —
        which is judgement, so it is a session. This launches it and does not watch it: the session's
        own product is another driver running, and there is no state of its own to wait for. If it
        dies before starting one, the run stops where it stands and `--resume` picks it up, which is
        the same recovery every other stall has.
        """
        parent = state.get("parent")
        if not parent:
            return
        above = Run(self.run.dir.parent / parent)
        if above.state().get("command") != "mvp":
            return
        name = f"{above.slug}-advance"[:60]
        self.run.event("hand-back", f"{parent} decides what follows")
        if not self.launcher.start(name, f"/agent-kit:mvp --advance {above.dir}",
                                   self.model_for(above.state())):
            above.event("stalled", "could not start the session that decides the next batch")
            self.tell(f"{above.slug} needs /agent-kit:mvp --resume — the next batch did not start")


# --------------------------------------------------------------------------------------------


def project_root(run_dir: Path) -> Path:
    for parent in run_dir.resolve().parents:
        if parent.name == ".agent-kit":
            return parent.parent
    return Path.cwd()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path, help=".agent-kit/runs/<slug>/ of the batch")
    parser.add_argument("--poll", type=int, default=60, help="seconds between looks at the run file")
    parser.add_argument("--hang", type=int, default=30, help="minutes of transcript silence before a session is treated as stuck")
    parser.add_argument("--max-wait", type=float, default=6, help="hours: a reset further away than this is a weekly limit, and the run stops")
    parser.add_argument("--model", default=None,
                        help="model for every session this run starts, unless its run file names "
                             "one of its own")
    options = parser.parse_args(argv)

    run_dir = options.run_dir.resolve()
    if not (run_dir / "run.json").is_file():
        print(f"no run file in {run_dir}", file=sys.stderr)
        return 1

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
