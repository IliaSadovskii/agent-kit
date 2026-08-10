"""The driver's loop, with no tmux, no claude and no network.

    python3 -m unittest discover -s tests

Everything the driver decides is decided here: which feature runs next, when a silence is a limit
rather than a hang, and what a run that never came back is called. It runs unattended overnight, so
the cheap way to find out it is wrong is not the first live sprint.
"""

import contextlib
import datetime as dt
import importlib.util
import io
import json
import shutil
import tempfile
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "orchestrate", ROOT / "plugins" / "agent-kit" / "scripts" / "orchestrate.py")
orch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orch)


class FakeLauncher:
    """A launcher that starts nothing. Subclasses decide what the imaginary session does."""

    def __init__(self, *_args, **_kwargs):
        self.helper = None
        self.typed = []
        self.told = []
        self.reclaimed = None

    def start(self, name, prompt, model=None):
        return True

    def send(self, name, text):
        self.typed.append(text)
        return True

    def alive(self, _name):
        return True

    def tmux_name(self, name):
        return f"cc-{name}"

    def stop(self, _name):
        pass

    def send_to(self, target, text):
        self.told.append((target, text))
        return True

    def alive_at(self, _target):
        return True


class DriverCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cwd = self.tmp / "proj"
        self.runs = self.cwd / ".agent-kit" / "runs"
        self.runs.mkdir(parents=True)
        self.transcripts = orch.transcript_dir(self.cwd)
        self.transcripts.mkdir(parents=True, exist_ok=True)
        self.transcript = self.transcripts / "session.jsonl"
        self.transcript.write_text('{"type":"assistant"}\n', encoding="utf-8")

        # The clock is swapped inside the driver's own namespace rather than in the time module, so
        # a test that waits out a limit does not make the whole process think an hour went by.
        self.clock = [time.time()]
        self.started = self.clock[0]
        self._real = (orch.time, orch.newest_transcript, orch.read_tail, orch.Launcher)
        orch.time = types.SimpleNamespace(
            time=lambda: self.clock[0],
            sleep=lambda seconds=0: self.clock.__setitem__(0, self.clock[0] + max(seconds, 30)))
        orch.newest_transcript = lambda cwd, after: self.transcript
        orch.read_tail = lambda path, lines=40: ""
        orch.Driver.branch_pushed = lambda _self, _branch: False

    def tearDown(self):
        orch.time, orch.newest_transcript, orch.read_tail, orch.Launcher = self._real
        shutil.rmtree(self.tmp, ignore_errors=True)

    def waited(self):
        """How much time the driver believes has passed since it started."""
        return self.clock[0] - self.started

    # ---- helpers ---------------------------------------------------------------------------

    def batch(self, *features):
        slugs = [f"b-{i:02d}-{f}" for i, f in enumerate(features, 1)]
        (self.runs / "b").mkdir()
        self.write("b", {"slug": "b", "command": "sprint", "base": "main", "children": slugs})
        for i, slug in enumerate(slugs):
            (self.runs / slug).mkdir()
            self.write(slug, {"slug": slug, "command": "ship", "step": "queued",
                              "branch": f"claude/{slug}", "parent": slugs[i - 1] if i else None,
                              "deliver": "branch", "pr": None})
        return slugs

    def write(self, slug, state):
        (self.runs / slug / "run.json").write_text(json.dumps(state), encoding="utf-8")

    def step(self, slug):
        return json.loads((self.runs / slug / "run.json").read_text(encoding="utf-8")).get("step")

    def drive(self, launcher_class, **overrides):
        orch.Launcher = launcher_class
        options = types.SimpleNamespace(poll=60, hang=30, max_wait=6, model=None)
        for key, value in overrides.items():
            setattr(options, key, value)
        driver = orch.Driver(orch.Run(self.runs / "b"), self.cwd, options)
        with contextlib.redirect_stdout(io.StringIO()):    # the driver narrates to the run log too
            return driver, driver.go()

    # ---- the limit record ------------------------------------------------------------------

    def test_limit_record_carries_its_reset(self):
        line = ('{"isApiErrorMessage":true,"apiErrorStatus":429,"text":"You\'ve hit your session '
                'limit · resets 2:20am (Asia/Tbilisi)"}')
        kind, when = orch.limit_reset(line)
        self.assertEqual(kind, "limit")
        self.assertIsNotNone(when)
        self.assertLess(when - time.time(), 25 * 3600)

    def test_overloaded_is_not_a_limit(self):
        self.assertEqual(orch.limit_reset('"apiErrorStatus":529')[0], "overloaded")
        self.assertEqual(orch.limit_reset('{"type":"assistant"}')[0], "")

    # ---- the batch -------------------------------------------------------------------------

    def test_a_failed_feature_takes_its_descendants_with_it(self):
        first, second, third = self.batch("one", "two", "three")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first, second, third],
                                     "step": "done", "pr": 42})
                return True

            def alive(self, _name):
                return False                       # the second feature's session dies

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(first), "done")
        self.assertEqual(self.step(second), "blocked")
        self.assertEqual(self.step(third), "skipped")

    def test_a_live_but_silent_session_is_nudged_before_it_is_restarted(self):
        """Ending a turn and finishing a run are different things, and nothing in the harness ties
        them together: a live child stopped one step short of `done`, branch pushed, context
        intact. Restarting throws away everything it read, so it gets one word first."""
        first, = self.batch("one")
        case = self
        starts = []

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                starts.append(name)
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 7})
                return True

            def send(self, name, text):
                self.typed.append(text)
                if text == "continue" and first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                return True

        driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(first), "done")
        self.assertIn("continue", driver.launcher.typed)
        self.assertEqual([n for n in starts if first in n], [first])
        self.assertIn("nudged", (self.runs / first / "run.log").read_text(encoding="utf-8"))

    def test_a_limit_is_waited_out_and_the_session_resumes(self):
        first, second = self.batch("one", "two")
        case = self
        limited = {"still": True}
        resets = time.strftime("%-I:%M%p", time.localtime(time.time() + 3600)).lower()
        orch.read_tail = lambda path, lines=40: (
            '{"isApiErrorMessage":true,"apiErrorStatus":429,"text":"resets %s"}' % resets
            if limited["still"] else "")

        class Launcher(FakeLauncher):
            def send(self, name, text):
                self.typed.append(text)
                limited["still"] = False           # the reset has passed; the session carries on
                for slug in (first, second):
                    case.write(slug, {"slug": slug, "step": "done", "branch": f"claude/{slug}"})
                case.write("b", {"slug": "b", "children": [first, second], "step": "done", "pr": 7})
                return True

        driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(first), "done")
        self.assertIn("continue", driver.launcher.typed)
        self.assertGreater(self.waited(), 1500)          # it actually waited for the reset

    def test_a_weekly_limit_stops_the_run_instead_of_sleeping_through_a_day(self):
        first, second = self.batch("one", "two")
        resets = time.strftime("%-I:%M%p", time.localtime(time.time() + 20 * 3600)).lower()
        orch.read_tail = lambda path, lines=40: (
            '{"isApiErrorMessage":true,"apiErrorStatus":429,"text":"resets %s"}' % resets)

        _driver, code = self.drive(FakeLauncher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(first), "blocked")
        self.assertEqual(self.step(second), "skipped")
        self.assertLess(self.waited(), 6 * 3600)

    def test_stop_from_the_control_file_is_taken_between_features(self):
        first, second = self.batch("one", "two")
        (self.runs / "b" / "control").write_text("stop\n", encoding="utf-8")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first, second], "step": "done", "pr": 9})
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(first), "skipped")
        self.assertEqual(self.step(second), "skipped")
        self.assertFalse((self.runs / "b" / "control").exists())

    def test_a_closing_session_that_never_returns_does_not_hang_the_driver(self):
        first, = self.batch("one")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                return True                        # the closing session writes nothing, ever

            def alive(self, _name):
                return False

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step("b"), "blocked")

    def test_the_driver_speaks_to_the_session_named_in_the_run_file(self):
        first, = self.batch("one")
        state = json.loads((self.runs / "b" / "run.json").read_text(encoding="utf-8"))
        state["window"] = "cc-my-own-session"
        self.write("b", state)
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    state["step"], state["pr"] = "done", 3
                    case.write("b", state)
                return True

        driver, _code = self.drive(Launcher)
        targets = {target for target, _text in driver.launcher.told}
        self.assertEqual(targets, {"cc-my-own-session"})
        self.assertTrue(all(text.startswith("[driver] ") for _t, text in driver.launcher.told))

    def test_a_batch_with_no_window_runs_unnarrated(self):
        first, = self.batch("one")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

        driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(driver.launcher.told, [])

    def test_a_pushed_branch_outvotes_a_run_file_left_behind(self):
        first, = self.batch("one")
        orch.Driver.branch_pushed = lambda _self, _branch: True

        class Launcher(FakeLauncher):
            def alive(self, _name):
                return False

        _driver, _code = self.drive(Launcher)
        self.assertEqual(self.step(first), "done")


if __name__ == "__main__":
    unittest.main()


class ModelCase(unittest.TestCase):
    """Which model a session is started on — the run file's, the run's default, or the install's."""

    def test_a_run_that_names_one(self):
        self.assertEqual(orch.Driver.model_for({"model": "sonnet"}), "sonnet")

    def test_a_run_that_does_not(self):
        for state in ({}, {"model": None}, {"model": "   "}, None):
            self.assertIsNone(orch.Driver.model_for(state), state)


class LauncherCase(unittest.TestCase):
    """A session name that is already taken.

    `claude-new` prints "that name is taken" and exits 0, so a launcher that trusted the exit code
    believed it had a fresh session and typed the prompt into whatever was standing there — a real
    mvp run left its hand-back session idle with half a sentence in its box, and the next batch
    would have appended its instruction to that. The name is taken back instead.
    """

    def setUp(self):
        self._time = orch.time
        orch.time = types.SimpleNamespace(sleep=lambda _s: None, time=time.time)

    def tearDown(self):
        orch.time = self._time

    def launcher(self, alive: bool):
        made = orch.Launcher.__new__(orch.Launcher)
        made.cwd = Path(".")
        made.model = None
        made.helper = None
        made.closer = None
        made.reclaimed = None
        made.calls = []
        made.alive = lambda _name: alive
        made.stop = lambda name: made.calls.append(("stop", name))
        made._tmux = lambda *args: types.SimpleNamespace(returncode=0, stdout="", stderr="")
        made.send = lambda name, text: made.calls.append(("send", text)) or True
        return made

    def test_a_taken_name_is_closed_before_anything_is_typed(self):
        made = self.launcher(alive=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(made.start("batch-advance", "/agent-kit:mvp --advance x"))
        self.assertEqual(made.reclaimed, "batch-advance")
        self.assertEqual(made.calls[0], ("stop", "batch-advance"))
        self.assertIn(("send", "/agent-kit:mvp --advance x"), made.calls)

    def test_a_free_name_is_left_alone(self):
        made = self.launcher(alive=False)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(made.start("batch-advance", "/agent-kit:mvp --advance x"))
        self.assertIsNone(made.reclaimed)
        self.assertNotIn("stop", [c[0] for c in made.calls])


class WindowNoticeCase(unittest.TestCase):
    """What the driver says to the owner's window.

    The window is told its job at a gate that may be hours and one compaction behind by the time
    the first news arrives — a live run reviewed a finished batch on its own and asked the owner a
    question, out of a rule file it had never opened. The reminder rides with the first line.
    """

    def driver(self, window):
        made = orch.Driver.__new__(orch.Driver)
        made.launcher = FakeLauncher()
        made.run = types.SimpleNamespace(state=lambda: {"window": window})
        return made

    def test_the_first_news_carries_the_rule_and_later_news_does_not(self):
        made = self.driver("ccp-proj")
        made.tell("the batch is finished, pull request 12")
        made.tell("starting the next feature")
        sent = [text for _target, text in made.launcher.told]
        self.assertEqual(len(sent), 3)
        self.assertIn("never put a question", sent[0])
        self.assertIn("window.md", sent[0])
        self.assertEqual(sent[1], "[driver] the batch is finished, pull request 12")
        self.assertEqual(sent[2], "[driver] starting the next feature")

    def test_a_run_with_no_window_is_told_nothing(self):
        made = self.driver(None)
        made.tell("the batch is finished")
        self.assertEqual(made.launcher.told, [])


class SilenceCase(unittest.TestCase):
    """How long a session has actually been quiet.

    The driver read the transcript's mtime, and a live run was measured with its child silent for
    44 minutes while the driver saw 24 — the harness had touched the file once, for reasons of its
    own, and bought the stalled child twenty-one free minutes. The records carry their own
    timestamps; those are the answer.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "session.jsonl"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_last_record_is_what_counts_not_the_last_touch(self):
        self.path.write_text(
            '{"type":"assistant","timestamp":"2026-08-10T17:40:00.000Z"}\n'
            '{"type":"system","timestamp":"2026-08-10T17:59:34.232Z"}\n', encoding="utf-8")
        spoke = orch.last_spoke(self.path)
        self.assertEqual(
            dt.datetime.fromtimestamp(spoke, dt.timezone.utc).strftime("%H:%M:%S"), "17:59:34")

    def test_a_tail_with_no_timestamps_falls_back_to_mtime(self):
        self.path.write_text('not json at all\n{"type":"assistant"}\n', encoding="utf-8")
        self.assertIsNone(orch.last_spoke(self.path))

