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
        options = types.SimpleNamespace(poll=60, hang=30, max_wait=6, model=None, ceiling=120)
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

    def test_a_batch_carrying_the_run_s_own_pull_request_is_not_closed_on_that_alone(self):
        """The trap, from the live run: one pull request covers a whole `epic`, so a batch can hold
        its number before it has done anything. Read as proof, it ends the closing session a minute
        after it starts — twice, on one night."""
        first, = self.batch("one")
        (self.runs / "m").mkdir()
        self.write("m", {"slug": "m", "command": "epic", "pr": 12, "children": ["b"]})
        self.write("b", {"slug": "b", "command": "sprint", "base": "main", "children": [first],
                         "parent": "m", "pr": 12})
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


class LiveQueueCase(DriverCase):
    """`children` is the queue, and a session between features may change what is left of it."""

    def test_a_feature_added_while_the_batch_runs_is_built(self):
        first, = self.batch("one")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:                  # the first feature adds one behind itself
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                    (case.runs / "b-02-late").mkdir(exist_ok=True)
                    case.write("b-02-late", {"slug": "b-02-late", "command": "ship",
                                             "step": "queued", "branch": "claude/late"})
                    batch = json.loads((case.runs / "b" / "run.json").read_text(encoding="utf-8"))
                    batch["children"] = [first, "b-02-late"]
                    case.write("b", batch)
                if "late" in name:
                    case.write("b-02-late", {"slug": "b-02-late", "step": "done",
                                             "branch": "claude/late"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first, "b-02-late"],
                                     "step": "done", "pr": 9})
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step("b-02-late"), "done")

    def test_a_feature_dropped_from_the_queue_is_never_started(self):
        first, second = self.batch("one", "two")
        case = self

        class Launcher(FakeLauncher):
            started = []

            def start(self, name, prompt, model=None):
                Launcher.started.append(name)
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                    batch = json.loads((case.runs / "b" / "run.json").read_text(encoding="utf-8"))
                    batch["children"] = [first]     # the second is taken off the list
                    case.write("b", batch)
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 9})
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertNotIn(second, Launcher.started)

    def test_a_child_that_is_not_a_ship_is_started_by_the_prompt_it_carries(self):
        first, = self.batch("one")
        state = json.loads((self.runs / first / "run.json").read_text(encoding="utf-8"))
        state["prompt"] = "/agent-kit:audit security"
        self.write(first, state)
        case = self

        class Launcher(FakeLauncher):
            prompts = []

            def start(self, name, prompt, model=None):
                Launcher.prompts.append(prompt)
                if first in name:
                    case.write(first, {"slug": first, "step": "done"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 9})
                return True

        self.drive(Launcher)
        self.assertIn("/agent-kit:audit security", Launcher.prompts)

    def test_a_run_with_no_children_hands_back_instead_of_stopping_in_silence(self):
        """A driver started on a file that is not a batch — an epic's own file, or a lone audit run
        put into the wrong list — used to log one word and exit. Nothing else was running, so the
        whole epic stopped there and only `--resume` ever found it."""
        (self.runs / "e").mkdir()
        self.write("e", {"slug": "e", "command": "epic", "children": ["b"]})
        (self.runs / "b").mkdir()
        self.write("b", {"slug": "b", "command": "sprint", "parent": "e", "children": []})

        class Launcher(FakeLauncher):
            started = []

            def start(self, name, prompt, model=None):
                Launcher.started.append((name, prompt))
                return True

        Launcher.started = []
        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 1)
        self.assertEqual([name for name, _prompt in Launcher.started], ["e-advance"])
        self.assertIn("--advance", Launcher.started[0][1])

    def test_an_instruction_the_driver_does_not_know_is_said_rather_than_swallowed(self):
        """`control` is read and deleted whatever it says. An unrecognised word would then vanish
        exactly like one that was obeyed, and the owner who watched the file disappear would
        believe it was. `wait` was such a word until it was removed: it stopped the run for hours
        on a question nobody was able to answer, because nothing in the kit could clear it."""
        first, = self.batch("one")
        (self.runs / "b" / "control").write_text("wait 2 the OpenRouter key is not in .env",
                                                 encoding="utf-8")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 9})
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertLess(self.waited(), 3600, "nothing stands still on a word nobody knows")
        self.assertEqual(self.step(first), "done")
        self.assertIn("not recognised", (self.runs / "b" / "run.log").read_text(encoding="utf-8"))

    def test_what_a_batch_spent_is_written_down(self):
        first, = self.batch("one")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    batch = json.loads((case.runs / "b" / "run.json").read_text(encoding="utf-8"))
                    batch.update({"step": "done", "pr": 9})
                    case.write("b", batch)
                return True

        self.drive(Launcher)
        spent = json.loads((self.runs / "b" / "run.json").read_text(encoding="utf-8"))["spent"]
        self.assertEqual(spent["features"], 1)
        self.assertGreaterEqual(spent["sessions"], 1)
        self.assertIn("hours", spent)


class HandoverCase(DriverCase):
    """A feature outlasting one session, handed to the next instead of paying for its own history."""

    BIG = ('{"message":{"usage":{"input_tokens":4,"cache_creation_input_tokens":2000,'
           '"cache_read_input_tokens":200000,"output_tokens":40}}}')
    SMALL = ('{"message":{"usage":{"input_tokens":4,"cache_creation_input_tokens":1000,'
             '"cache_read_input_tokens":40000,"output_tokens":40}}}')

    def test_the_size_is_read_off_the_transcript_a_record_at_a_time(self):
        self.assertEqual(orch.context_size(self.SMALL + "\n" + self.BIG), 202004)
        self.assertEqual(orch.context_size("nothing here"), 0)

    def test_a_session_over_the_ceiling_is_asked_once_and_carried_on_by_a_fresh_one(self):
        first, = self.batch("one")
        case = self
        state = {"over": True, "alive": True, "starts": 0}
        orch.read_tail = lambda path, lines=40: case.BIG if state["over"] else case.SMALL

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    state["starts"] += 1
                    state["alive"] = True
                    if state["starts"] == 2:       # the session that took the handoff finishes it
                        case.write(first, {"slug": first, "step": "done",
                                           "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

            def send(self, name, text):
                self.typed.append(text)
                if text is orch.HANDOFF_LINE or "hand this run over" in text:
                    # the session finishes its task, writes the note and stops
                    run = json.loads((case.runs / first / "run.json").read_text(encoding="utf-8"))
                    run["handoff"] = "stopped after task 2; tried the queue seam, it deadlocks"
                    case.write(first, run)
                    state["over"], state["alive"] = False, False
                return True

            def alive(self, _name):
                return state["alive"]

        driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(state["starts"], 2, "the run should have been carried on exactly once")
        self.assertEqual(self.step(first), "done")
        asks = [t for t in driver.launcher.typed if "hand this run over" in t]
        self.assertEqual(len(asks), 1, "asked once per session, not once per poll")

    def test_a_session_that_ignores_the_ask_is_still_treated_as_stuck(self):
        first, = self.batch("one")
        case = self
        orch.read_tail = lambda path, lines=40: case.BIG

        class Launcher(FakeLauncher):
            def alive(self, _name):
                return False                       # gone, and it never wrote a note

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(first), "blocked")

    def test_a_note_left_over_from_an_earlier_handoff_does_not_count_as_a_new_one(self):
        """Nothing clears `handoff`, so a run handed over once carries a filled field for the rest
        of its life. Read as "the note has landed", that would kill the next session on its first
        quiet minute and pass on a note about work already finished."""
        first, = self.batch("one")
        case = self
        state = {"starts": 0}
        orch.read_tail = lambda path, lines=40: case.BIG        # always over the ceiling

        stale = "stopped after task 2 — that was two sessions ago"
        run = json.loads((self.runs / first / "run.json").read_text(encoding="utf-8"))
        run["handoff"] = stale
        self.write(first, run)

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    state["starts"] += 1
                    if state["starts"] > 1:
                        raise AssertionError("restarted on a note nobody wrote this session")
                    case.write(first, {"slug": first, "step": "done", "handoff": stale,
                                       "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(state["starts"], 1)

    def test_the_closing_session_is_never_asked_to_hand_over(self):
        """Handing a run on is a rule of `ship`. The closing session has nobody to hand to, and
        restarting it throws away the one context in the batch that cannot be rebuilt from files."""
        first, = self.batch("one")
        case = self
        orch.read_tail = lambda path, lines=40: case.BIG

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

            def send(self, name, text):
                self.typed.append(text)
                if "hand this run over" in text and name.endswith("-close"):
                    raise AssertionError("the closing session was asked to hand over")
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)

    def test_a_child_that_is_not_a_ship_is_never_asked_to_hand_over(self):
        """`prompt` says this child is an audit or a review. Handing on is a rule of `ship`, so the
        ask would send it to a section of a file it never read, with nobody to hand to."""
        first, = self.batch("one")
        case = self
        orch.read_tail = lambda path, lines=40: case.BIG
        run = json.loads((self.runs / first / "run.json").read_text(encoding="utf-8"))
        run["prompt"] = "/agent-kit:audit security"
        self.write(first, run)

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

        driver, _code = self.drive(Launcher)
        self.assertEqual([t for t in driver.launcher.typed if "hand this run over" in t], [])

    def test_the_ceiling_can_be_switched_off(self):
        first, = self.batch("one")
        case = self
        orch.read_tail = lambda path, lines=40: case.BIG

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    case.write(first, {"slug": first, "step": "done", "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

        driver, _code = self.drive(Launcher, ceiling=0)
        self.assertEqual([t for t in driver.launcher.typed if "hand this run over" in t], [])


class InheritedPullRequestCase(unittest.TestCase):
    """`pr` is evidence a run finished only when opening it was that run's own job."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.runs = self.tmp / "runs"
        self.runs.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, slug, state):
        (self.runs / slug).mkdir(exist_ok=True)
        (self.runs / slug / "run.json").write_text(json.dumps(state), encoding="utf-8")
        return orch.Run(self.runs / slug)

    def test_a_pull_request_this_run_opened_is_terminal(self):
        run = self.write("solo", {"slug": "solo", "pr": 7, "step": "deliver"})
        self.assertEqual(run.own_pr(), 7)
        self.assertTrue(run.terminal())

    def test_a_number_inherited_from_the_run_above_is_not(self):
        self.write("m", {"slug": "m", "command": "epic", "pr": 12})
        run = self.write("b", {"slug": "b", "parent": "m", "pr": 12, "step": "closing"})
        self.assertIsNone(run.own_pr())
        self.assertFalse(run.terminal())

    def test_a_second_pull_request_under_the_same_parent_still_counts(self):
        self.write("m", {"slug": "m", "command": "epic", "pr": 12})
        run = self.write("b", {"slug": "b", "parent": "m", "pr": 13, "step": "closing"})
        self.assertEqual(run.own_pr(), 13)

    def test_the_step_alone_closes_a_batch_with_an_inherited_number(self):
        self.write("m", {"slug": "m", "command": "epic", "pr": 12})
        run = self.write("b", {"slug": "b", "parent": "m", "pr": 12, "step": "done"})
        self.assertTrue(run.terminal())

    def test_a_parent_that_is_not_there_leaves_the_number_this_run_s_own(self):
        run = self.write("b", {"slug": "b", "parent": "gone", "pr": 5, "step": "deliver"})
        self.assertEqual(run.own_pr(), 5)


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
    epic run left its hand-back session idle with half a sentence in its box, and the next batch
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
            self.assertTrue(made.start("batch-advance", "/agent-kit:epic --advance x"))
        self.assertEqual(made.reclaimed, "batch-advance")
        self.assertEqual(made.calls[0], ("stop", "batch-advance"))
        self.assertIn(("send", "/agent-kit:epic --advance x"), made.calls)

    def test_a_free_name_is_left_alone(self):
        made = self.launcher(alive=False)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(made.start("batch-advance", "/agent-kit:epic --advance x"))
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

