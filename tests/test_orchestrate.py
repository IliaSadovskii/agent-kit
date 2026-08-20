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
import os
import shutil
import subprocess
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
        orch.newest_transcript = lambda cwd, after, mark="": self.transcript
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
        options = types.SimpleNamespace(poll=60, hang=30, max_wait=6, model=None, ceiling=120, room=60)
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


class NeedsCase(DriverCase):
    """What a failed feature takes with it, and what it does not.

    Before `needs` existed every child named the one before it as its parent whether or not it
    depended on it, so one blocked feature skipped every feature after it — measured on the live
    project as the cost of a session that died at three in the morning, not of anything the feature
    got wrong. The chain stays; only the skipping is now about real dependencies.
    """

    def needs(self, slug, wants):
        state = json.loads((self.runs / slug / "run.json").read_text(encoding="utf-8"))
        state["needs"] = wants
        self.write(slug, state)

    def state_of(self, slug):
        return json.loads((self.runs / slug / "run.json").read_text(encoding="utf-8"))

    def test_a_feature_that_needs_nothing_survives_the_one_before_it_failing(self):
        first, second, third = self.batch("one", "two", "three")
        self.needs(second, [])
        self.needs(third, [])
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if second in name:
                    return True                    # the middle feature's session never comes back
                for slug in (first, third):
                    if slug in name:
                        case.write(slug, {"slug": slug, "step": "done", "branch": f"claude/{slug}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first, second, third],
                                     "step": "done", "pr": 42})
                return True

            def alive(self, name):
                return False

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(second), "blocked")
        self.assertEqual(self.step(third), "done")

    def test_a_feature_that_needs_the_failed_one_is_skipped(self):
        first, second, third = self.batch("one", "two", "three")
        self.needs(second, [])
        self.needs(third, [second])
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
                return False

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(third), "skipped")

    def test_the_chain_runs_through_what_was_built_not_through_what_was_planned(self):
        first, second, third = self.batch("one", "two", "three")
        self.needs(second, [])
        self.needs(third, [])
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                for slug in (first, third):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first, second, third],
                                     "step": "done", "pr": 42})
                return True

            def alive(self, _name):
                return False

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.state_of(third)["base"], f"claude/{first}")
        self.assertEqual(self.state_of(third)["parent"], first)
        self.assertEqual(self.state_of(first)["base"], "main")

    def test_a_batch_whose_children_name_no_parent_is_a_batch_of_independents(self):
        """The fallback is the authored `parent`, not the neighbour in the queue. They are the same
        thing in an ordinary batch and differ here — and the old code skipped nothing when `parent`
        was null, so reading the neighbour instead would have skipped everything."""
        first, second, third = self.batch("one", "two", "three")
        for slug in (first, second, third):
            self.write(slug, dict(self.state_of(slug), parent=None))
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                for slug in (second, third):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

            def alive(self, _name):
                return False

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(first), "blocked")
        self.assertEqual(self.step(second), "done")
        self.assertEqual(self.step(third), "done")

    def test_a_missing_needs_still_means_the_one_before_it(self):
        """`[]` is an answer and no field at all is not, so a batch composed before this existed
        behaves exactly as it did — the alternative reads every old batch as independents."""
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
                return False

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(third), "skipped")


class FrameCase(DriverCase):
    """The frame child hands over a map; ordering the queue by it is arithmetic, so it is here."""

    def state_of(self, slug):
        return json.loads((self.runs / slug / "run.json").read_text(encoding="utf-8"))

    def test_the_map_becomes_the_queue_and_the_children_learn_what_they_need(self):
        frame, first, second = self.batch("frame", "one", "two")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if frame in name:
                    case.write(frame, dict(case.state_of(frame), step="done",
                                           frame={second: [], first: [second]}))
                for slug in (first, second):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.state_of("b")["children"], [frame, second, first])
        self.assertEqual(self.state_of(first)["needs"], [second])
        self.assertEqual(self.state_of(second)["needs"], [])

    def test_a_circle_leaves_the_queue_alone_and_says_so(self):
        frame, first, second = self.batch("frame", "one", "two")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if frame in name:
                    case.write(frame, dict(case.state_of(frame), step="done",
                                           frame={first: [second], second: [first]}))
                for slug in (first, second):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.state_of("b")["children"], [frame, first, second])
        blockers = " ".join(self.state_of("b").get("blockers") or [])
        self.assertIn("circle", blockers)

    def test_a_feature_from_another_batch_is_ignored_and_named(self):
        frame, first = self.batch("frame", "one")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if frame in name:
                    case.write(frame, dict(case.state_of(frame), step="done",
                                           frame={first: ["somebody-elses-feature"]}))
                if first in name:
                    case.write(first, dict(case.state_of(first), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.state_of(first)["needs"], [])
        blockers = " ".join(self.state_of("b").get("blockers") or [])
        self.assertIn("somebody-elses-feature", blockers)

    def test_ordering_moves_only_what_the_dependencies_move(self):
        """Taking every ready feature in one pass reorders independents for no reason: with b
        needing a, ["a","b","c"] came back as a, c, b. The owner's order is part of the bargain."""
        self.assertEqual(orch.order_by_needs(["a", "b", "c"], {}), (["a", "b", "c"], []))
        self.assertEqual(orch.order_by_needs(["a", "b", "c"], {"b": ["a"]})[0], ["a", "b", "c"])
        self.assertEqual(orch.order_by_needs(["a", "b", "c", "d"], {"c": ["a"]})[0],
                         ["a", "b", "c", "d"])
        self.assertEqual(orch.order_by_needs(["a", "b", "c"], {"a": ["c"]})[0], ["b", "c", "a"])

    def test_a_frame_child_that_never_came_back_does_not_skip_the_batch(self):
        """The batch would otherwise open with its own most fragile link. A frame child builds no
        product code, so nothing can be waiting on it — and it fails the way every child fails
        most often, by its session dying."""
        frame, first, second = self.batch("frame", "one", "two")
        self.write(frame, dict(self.state_of(frame), prompt="follow frame.md"))
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                for slug in (first, second):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

            def alive(self, _name):
                return False

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.step(frame), "blocked")
        self.assertEqual(self.step(first), "done")
        self.assertEqual(self.step(second), "done")

    def test_a_map_that_names_the_frame_child_is_not_a_circle(self):
        """It is built before all of them and is not in the list being sorted, so leaving it in
        `wants` made every feature unplaceable and the whole map was thrown away as a cycle."""
        frame, first, second = self.batch("frame", "one", "two")
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if frame in name:
                    case.write(frame, dict(case.state_of(frame), step="done",
                                           frame={first: [frame], second: [first]}))
                for slug in (first, second):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.state_of(first)["needs"], [])
        self.assertEqual(self.state_of(second)["needs"], [first])
        self.assertNotIn("circle", " ".join(self.state_of("b").get("blockers") or []))

    def test_a_child_named_in_the_queue_with_no_run_file_is_not_invented(self):
        """Writing `needs` into it would create the file, and the driver would then start a `ship`
        session on a run that names no feature and carries no task."""
        frame, first = self.batch("frame", "one")
        case = self
        shutil.rmtree(self.runs / first)
        batch = self.state_of("b")
        batch["children"] = [frame, first]
        self.write("b", batch)

        class Launcher(FakeLauncher):
            started = []

            def start(self, name, prompt, model=None):
                Launcher.started.append(name)
                if frame in name:
                    case.write(frame, dict(case.state_of(frame), step="done", frame={first: []}))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertFalse((self.runs / first / "run.json").is_file())
        self.assertFalse(any(first in name for name in Launcher.started))

    def test_a_map_the_owner_already_answered_is_not_overwritten(self):
        """The composing session had the owner in front of it; the map was made overnight."""
        frame, first, second = self.batch("frame", "one", "two")
        self.write(second, dict(self.state_of(second), needs=[first]))
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if frame in name:
                    case.write(frame, dict(case.state_of(frame), step="done",
                                           frame={first: [], second: []}))
                for slug in (first, second):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertEqual(self.state_of(second)["needs"], [first])

    def test_a_frame_child_that_left_no_map_says_so(self):
        """Prose written and the map forgotten closes green, and the batch silently falls back to
        the queue order — indistinguishable from a batch where nothing depends on anything."""
        frame, first = self.batch("frame", "one")
        self.write(frame, dict(self.state_of(frame), prompt="follow references/frame.md"))
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if frame in name:
                    case.write(frame, dict(case.state_of(frame), step="done"))
                if first in name:
                    case.write(first, dict(case.state_of(first), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertIn("no `frame` map", " ".join(self.state_of("b").get("blockers") or []))

    def test_a_frame_child_started_by_its_command_is_still_a_frame_child(self):
        """It is invoked as `/agent-kit:sprint --frame <dir>` since 2.15.0, and the run files a
        `--resume` reads may still carry the older form. Recognising one and not the other is how
        a missing map would go unreported on exactly the batches that were interrupted."""
        frame, first = self.batch("frame", "one")
        self.write(frame, dict(self.state_of(frame),
                               prompt="/agent-kit:sprint --frame .agent-kit/runs/b-00-frame"))
        case = self

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                for slug in (frame, first):
                    if slug in name:
                        case.write(slug, dict(case.state_of(slug), step="done"))
                if name.endswith("-close"):
                    case.write("b", dict(case.state_of("b"), step="done", pr=42))
                return True

        _driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        self.assertIn("no `frame` map", " ".join(self.state_of("b").get("blockers") or []))

    def test_applying_the_frame_twice_changes_nothing(self):
        frame, first, second = self.batch("frame", "one", "two")
        self.write(frame, dict(self.state_of(frame), step="done",
                               frame={first: [second], second: []}))
        driver = orch.Driver(orch.Run(self.runs / "b"), self.cwd,
                             types.SimpleNamespace(poll=60, hang=30, max_wait=6, model=None,
                                                   ceiling=120, room=60))
        child = orch.Run(self.runs / frame)
        with contextlib.redirect_stdout(io.StringIO()):
            driver.apply_frame(child, child.state())
            once = self.state_of("b")["children"]
            driver.apply_frame(child, child.state())
        self.assertEqual(self.state_of("b")["children"], once)
        self.assertEqual(once, [frame, second, first])


    def test_a_slug_the_frame_names_with_no_run_file_is_still_reported_as_stray(self):
        """Adoption is for a file the frame child actually wrote. A bare name is the old failure —
        a dependency on something that is not in this batch — and it must stay visible."""
        frame, first, second = self.batch("frame", "one", "two")
        self.write(frame, dict(self.state_of(frame), step="done",
                               frame={first: ["b-99-imaginary"], second: []}))
        driver = orch.Driver(orch.Run(self.runs / "b"), self.cwd,
                             types.SimpleNamespace(poll=60, hang=30, max_wait=6, model=None,
                                                   ceiling=120, room=60))
        child = orch.Run(self.runs / frame)
        with contextlib.redirect_stdout(io.StringIO()):
            driver.apply_frame(child, child.state())
        self.assertNotIn("b-99-imaginary", self.state_of("b")["children"])
        self.assertIn("b-99-imaginary", json.dumps(self.state_of("b"), ensure_ascii=False))


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


class TranscriptPickingCase(DriverCase):
    """Which of a project's transcripts belongs to the session the driver just started."""

    def jsonl(self, name, began, wrote, body=""):
        path = self.transcripts / name
        path.write_text(f'{{"timestamp":"{began}Z","body":"{body}"}}\n'
                        f'{{"timestamp":"{wrote}Z"}}\n', encoding="utf-8")
        return path

    def test_a_conversation_that_was_already_open_is_not_the_session_just_started(self):
        """The owner's own window sits in the same project directory, and its file is touched every
        time they type. Picked by modification time it wins — and a live run read a 370k
        conversation as its child's context, then asked every session that followed to hand over."""
        orch.newest_transcript = self._real[1]
        window = self.jsonl("window.jsonl", "2026-08-13T11:12:36", "2026-08-13T12:27:14")
        child = self.jsonl("child.jsonl", "2026-08-13T12:25:47", "2026-08-13T12:26:01")
        os.utime(window, (2_000_000_100, 2_000_000_100))     # the newest file by a clear margin
        os.utime(child, (2_000_000_000, 2_000_000_000))
        launched = dt.datetime(2026, 8, 13, 12, 25, tzinfo=dt.timezone.utc).timestamp()
        self.assertEqual(orch.newest_transcript(self.cwd, launched), child)

    def test_the_transcript_carrying_the_run_slug_wins_over_a_newer_one(self):
        """Two sessions can start within a minute of each other — a sibling in the same tree, the
        driver's own hand-back. The prompt the driver typed names the run."""
        orch.newest_transcript = self._real[1]
        mine = self.jsonl("mine.jsonl", "2026-08-13T12:25:47", "2026-08-13T12:26:01",
                               body="/agent-kit:ship .agent-kit/runs/b-01-table")
        other = self.jsonl("other.jsonl", "2026-08-13T12:25:50", "2026-08-13T12:26:30")
        os.utime(mine, (2_000_000_000, 2_000_000_000))
        os.utime(other, (2_000_000_100, 2_000_000_100))
        launched = dt.datetime(2026, 8, 13, 12, 25, tzinfo=dt.timezone.utc).timestamp()
        self.assertEqual(orch.newest_transcript(self.cwd, launched, "b-01-table"), mine)
        self.assertEqual(orch.newest_transcript(self.cwd, launched, "no-such-run"), other,
                         "with nothing matching, the newest of the candidates is still the answer")


class HandoverCase(DriverCase):
    """A feature outlasting one session, handed to the next instead of paying for its own history."""

    # Both carry `iterations`, because every record a live session writes carries it: the same
    # three numbers a second time. The totals below are the numbers counted once.
    BIG = ('{"message":{"usage":{"input_tokens":4,"cache_creation_input_tokens":2000,'
           '"cache_read_input_tokens":200000,"output_tokens":40,'
           '"iterations":[{"input_tokens":4,"cache_creation_input_tokens":2000,'
           '"cache_read_input_tokens":200000,"output_tokens":40}]}}}')
    SMALL = ('{"message":{"usage":{"input_tokens":4,"cache_creation_input_tokens":1000,'
             '"cache_read_input_tokens":40000,"output_tokens":40,'
             '"iterations":[{"input_tokens":4,"cache_creation_input_tokens":1000,'
             '"cache_read_input_tokens":40000,"output_tokens":40}]}}}')

    def test_the_size_is_read_off_the_transcript_a_record_at_a_time(self):
        self.assertEqual(orch.context_size(self.SMALL + "\n" + self.BIG), 202004)
        self.assertEqual(orch.context_size("nothing here"), 0)

    def test_a_repeated_field_is_one_number_and_not_two(self):
        """What `iterations` cost: scanning the line for the three field names summed each of them
        twice, on 20,249 of the 20,260 usage records of one run. Every number this driver decides
        by was doubled — a 300k ceiling fired at 150k, a 45.5k floor read as 91k — and the run did
        exactly half of what its own command line said. A field that appears twice is not a number
        to add up, so the record is parsed and its fields are read by name."""
        self.assertEqual(orch.context_size(self.BIG), 202004, "not 404008")
        self.assertEqual(orch.context_size(
            '{"message":{"usage":{"input_tokens":7,"cache_read_input_tokens":9}}}'), 16,
            "a record from before iterations existed still reads")
        self.assertEqual(orch.context_size('cache_read_input_tokens":200000}'), 0,
                         "the half line a tail read starts on is not a size")

    def test_a_reading_set_that_nearly_fills_the_ceiling_does_not_hand_over_forever(self):
        """The measured failure: a floor of 45.5k under a ceiling that really stood at 60k, where
        `room` made the true trigger 85.5k — so a session was sent away after 40k of growth, which
        is the ~40 turns it spends orienting and not one more. One feature was handed over eleven
        times in an hour. A handoff costs the new session the whole floor, so a segment that grew
        less than `room` costs more than it saves."""
        self.assertFalse(orch.handoff_due(70_000, 45_500, 60, 40))
        self.assertTrue(orch.handoff_due(86_000, 45_500, 60, 40))
        self.assertFalse(orch.handoff_due(281_000, 250_000, 280, 40),
                         "a session that opened on a long note has not grown enough to pass it on")

    def test_a_floor_that_cannot_be_read_leaves_the_ceiling_deciding_alone(self):
        """A number that is missing is not a small one — but here the safe reading is the old rule,
        not a floor of nothing: with no floor to measure from, growth is unknowable."""
        self.assertTrue(orch.handoff_due(151_000, 0, 120, 60))
        self.assertFalse(orch.handoff_due(0, 0, 120, 60))
        self.assertFalse(orch.handoff_due(900_000, 0, 0, 60), "0 turns the mechanism off")

    def test_a_floor_that_could_not_be_read_is_said_out_loud(self):
        """The rule above is the behaviour and is right. What may not come with it is silence: with
        no floor, `room` clears trivially and stops guarding anything, and a guard that lapsed reads
        exactly like a guard with nothing to complain about. So the driver says it into the run log,
        once per session — the same file that already records every other thing it decided."""
        first, = self.batch("one")
        case = self
        state = {"over": True, "alive": True, "starts": 0}
        orch.read_tail = lambda path, lines=40: case.BIG if state["over"] else case.SMALL

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                if first in name:
                    state["starts"] += 1
                    state["alive"] = True
                    if state["starts"] == 2:
                        case.write(first, {"slug": first, "step": "done",
                                           "branch": f"claude/{first}"})
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

            def send(self, name, text):
                self.typed.append(text)
                if "hand this run over" in text:
                    run = json.loads((case.runs / first / "run.json").read_text(encoding="utf-8"))
                    run["handoff"] = "stopped after task 2"
                    case.write(first, run)
                    state["over"], state["alive"] = False, False
                return True

            def alive(self, _name):
                return state["alive"]

        self.drive(Launcher)
        log = (self.runs / first / "run.log").read_text(encoding="utf-8")
        self.assertEqual(log.count("floor-unreadable"), 1,
                         "once per session — the driver polls this many times over")

    def test_the_floor_is_the_first_usage_record_and_not_the_first_poll(self):
        """The first number the driver polls already carries whatever the session did in that
        minute, and it moves with the poll interval. The reading set is at the top of the file."""
        path = self.cwd / "transcript.jsonl"
        path.write_text(self.SMALL + "\n" + self.BIG + "\n", encoding="utf-8")
        self.assertEqual(orch.opening_size(path), 41004)
        self.assertEqual(orch.opening_size(self.cwd / "gone.jsonl"), 0)

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

    def test_the_session_that_takes_a_handoff_is_numbered_and_the_run_file_follows(self):
        """Eleven sessions of one feature shared a name, so nothing on the machine, in the app or in
        the log could say which was speaking. And the run file's `session` is what the stop hook
        matches on: a new name that is not written there leaves the hook guarding a dead session."""
        first, = self.batch("one")
        case = self
        state = {"over": True, "alive": True, "starts": 0, "names": []}
        orch.read_tail = lambda path, lines=40: case.BIG if state["over"] else case.SMALL

        class Launcher(FakeLauncher):
            def start(self, name, prompt, model=None):
                state["names"].append(name)
                if first in name:
                    state["starts"] += 1
                    state["alive"] = True
                    if state["starts"] == 2:
                        case.write(first, dict(json.loads(
                            (case.runs / first / "run.json").read_text(encoding="utf-8")),
                            step="done", branch=f"claude/{first}"))
                if name.endswith("-close"):
                    case.write("b", {"slug": "b", "children": [first], "step": "done", "pr": 4})
                return True

            def send(self, name, text):
                self.typed.append(text)
                if "hand this run over" in text:
                    run = json.loads((case.runs / first / "run.json").read_text(encoding="utf-8"))
                    run["handoff"] = "stopped after task 2"
                    case.write(first, run)
                    state["over"], state["alive"] = False, False
                return True

            def alive(self, _name):
                return state["alive"]

        driver, code = self.drive(Launcher)
        self.assertEqual(code, 0)
        started = [name for name in state["names"] if name.startswith(first)]
        self.assertEqual(started[:2], [first, f"{first[:56]}-2"])
        session = json.loads(
            (self.runs / first / "run.json").read_text(encoding="utf-8"))["session"]
        self.assertTrue(session.endswith("-2"), f"the run file still names {session}")

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


class HandBackCase(DriverCase):
    """The session an `epic` hands back to, and the one thing nothing else knows about it.

    It is the only session here with no closer of its own: the driver it may start closes it, and
    the driver that started it exits at the hand-back. When the run turns out to be finished no next
    driver ever comes, and on a live run it stood for eight hours. The stop hook closes it — and
    can only find it if its name is in the run file it is deciding about.
    """

    def epic_with_batch(self):
        (self.runs / "e").mkdir()
        self.write("e", {"slug": "e", "command": "epic", "kind": "epic", "step": "building",
                         "children": ["b"]})
        (self.runs / "b").mkdir(exist_ok=True)
        self.write("b", {"slug": "b", "command": "sprint", "parent": "e", "children": []})
        options = types.SimpleNamespace(poll=60, hang=30, max_wait=6, model=None, ceiling=120,
                                        room=60)
        orch.Launcher = FakeLauncher
        return orch.Driver(orch.Run(self.runs / "b"), self.cwd, options)

    def state(self, slug):
        return json.loads((self.runs / slug / "run.json").read_text(encoding="utf-8"))

    def test_the_session_that_decides_what_follows_is_named_in_the_epic(self):
        driver = self.epic_with_batch()
        with contextlib.redirect_stdout(io.StringIO()):
            driver.hand_back(self.state("b"))
        self.assertEqual(self.state("e").get("session"), "cc-e-advance")

    def test_a_session_that_did_not_start_is_not_named(self):
        """A name written for a session nobody started points the hook at a session that is not
        there — and the epic's own `--resume` is what answers for this case."""
        driver = self.epic_with_batch()

        class Dead(FakeLauncher):
            def start(self, name, prompt, model=None):
                return False

        driver.launcher = Dead()
        with contextlib.redirect_stdout(io.StringIO()):
            driver.hand_back(self.state("b"))
        self.assertIsNone(self.state("e").get("session"))


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
        made.warned_closer = False
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

    # ---- closing one ---------------------------------------------------------------------------

    def closing(self, helper, closer, code=0, stderr=""):
        made = orch.Launcher.__new__(orch.Launcher)
        made.cwd, made.model, made.reclaimed = Path("."), None, None
        made.helper, made.closer, made.warned_closer = helper, closer, False
        made.killed = []
        made.ran = []
        made._tmux = lambda *args: made.killed.append(args) or types.SimpleNamespace(
            returncode=0, stdout="", stderr="")
        self._run = orch.subprocess.run
        orch.subprocess.run = lambda args, **_kw: (
            made.ran.append(tuple(args))
            or subprocess.CompletedProcess(args, code, "", stderr))
        self.addCleanup(lambda: setattr(orch.subprocess, "run", self._run))
        return made

    def test_the_helper_closes_it_and_tmux_is_not_asked(self):
        """A registered session killed without being unregistered comes back: a watchdog put one
        back a minute later, with `Continue from where you left off` typed into it."""
        made = self.closing("/bin/claude-new", "/bin/claude-close")
        made.stop("b-01")
        self.assertEqual(made.ran, [("/bin/claude-close", "b-01")])
        self.assertEqual(made.killed, [])

    def test_a_helper_that_refused_is_not_overridden_with_a_kill(self):
        made = self.closing("/bin/claude-new", "/bin/claude-close", code=1, stderr="not allowed")
        with contextlib.redirect_stderr(io.StringIO()) as said:
            made.stop("b-01")
        self.assertEqual(made.killed, [])
        self.assertIn("not allowed", said.getvalue())

    def test_a_helper_with_no_closer_says_so_once(self):
        """The kill still happens — there is nothing better — but a kill that may leave the session
        registered is not a thing to do quietly."""
        made = self.closing("/bin/claude-new", None)
        with contextlib.redirect_stderr(io.StringIO()) as said:
            made.stop("b-01")
            made.stop("b-02")
        self.assertEqual(len(made.killed), 2)
        self.assertEqual(said.getvalue().count("may leave it registered"), 1)

    def test_plain_tmux_says_nothing(self):
        made = self.closing(None, None)
        with contextlib.redirect_stderr(io.StringIO()) as said:
            made.stop("b-01")
        self.assertEqual(made.killed, [("kill-session", "-t", "agent-kit-b-01")])
        self.assertEqual(said.getvalue(), "")

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

    # ---- the decisions taken with nobody there --------------------------------------------------
    #
    # `assumptions[].expensive` has been written by every feature since the field existed and read
    # by nothing. The owner met them in the morning, in a pull request that on one measured run
    # carried seventy — while the channel to their phone was open all night. There is no way back
    # along it: an answer cannot be applied to a decision the child has already built on, and that
    # is what `wait` was cut for in 2.5.0.

    def test_an_expensive_decision_reaches_the_window_the_hour_it_is_taken(self):
        made = self.driver("ccp-proj")
        child = types.SimpleNamespace(slug="2026-08-16-offers-02-accept")
        made.costly(child, {"assumptions": [
            {"what": "cheap one", "expensive": False},
            {"what": "offers are stored\n  on the order, not on the user", "expensive": True}]})
        sent = [text for _target, text in made.launcher.told]
        self.assertIn("2026-08-16-offers-02-accept took 1 decision", sent[-1])
        self.assertIn("offers are stored on the order", sent[-1])   # folded onto one line

    def test_a_child_that_decided_nothing_expensive_says_nothing(self):
        made = self.driver("ccp-proj")
        made.costly(types.SimpleNamespace(slug="x"),
                    {"assumptions": [{"what": "a default nobody will notice", "expensive": False}]})
        self.assertEqual(made.launcher.told, [])

    def test_a_run_file_with_no_assumptions_at_all(self):
        made = self.driver("ccp-proj")
        made.costly(types.SimpleNamespace(slug="x"), {})
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



class DetachCase(unittest.TestCase):
    """Outliving the session that started the driver.

    The night of 19 August was lost here: the session that starts a driver is closed a second
    later, and everything started from that pane goes with it. These hold the answer to the two
    questions the old comment got wrong — whether this process can be taken down by its parent, and
    what to do about it.
    """

    PANE = ("0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
            "tmux-spawn-79c91a45-75d9-4f3b-bd7a-30877cc1f28d.scope")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_pane_scope_is_a_control_group_that_takes_this_process_with_it(self):
        self.assertTrue(orch.dies_with_its_session(self.PANE))

    def test_a_service_of_its_own_is_not(self):
        # What the driver looks like once it has moved: running again from here would fork forever.
        self.assertFalse(orch.dies_with_its_session(
            "0::/user.slice/user-1000.slice/user@1000.service/app.slice/agent-kit-b.service"))

    def test_a_machine_that_publishes_no_control_group_is_left_alone(self):
        # macOS has no /proc, and there is nothing there to escape from.
        self.assertEqual(orch.own_cgroup(self.tmp / "no-such-file"), "")
        self.assertFalse(orch.dies_with_its_session(""))

    def test_a_slug_becomes_a_unit_name_systemd_will_take(self):
        self.assertEqual(orch.unit_name("2026-08-19-reference-meaning"),
                         "agent-kit-2026-08-19-reference-meaning")
        self.assertEqual(orch.unit_name("a batch/with junk"), "agent-kit-a-batch-with-junk")
        self.assertEqual(orch.unit_name(""), "agent-kit-run")

    def test_the_command_carries_this_run_and_the_flag_that_stops_it_recursing(self):
        command = orch.detach_command(Path("/p/.agent-kit/runs/b"), ["/p/.agent-kit/runs/b",
                                                                    "--ceiling", "0"], "/bin/sr")
        self.assertEqual(command[0], "/bin/sr")
        self.assertIn("--user", command)
        self.assertIn("--collect", command)
        self.assertIn("--unit=agent-kit-b", command)
        self.assertIn(f"--setenv={orch.DETACHED}=1", command)
        self.assertEqual(command[-3:], ["/p/.agent-kit/runs/b", "--ceiling", "0"])
        self.assertTrue(command[-4].endswith("orchestrate.py"))

    def test_the_path_is_carried_across_because_the_manager_has_none(self):
        # The first driver to move itself out lost ~/.local/bin with it, `claude-new` went missing,
        # and four features were blocked in twenty seconds.
        real = os.environ.get("PATH")
        os.environ["PATH"] = "/home/dev/.local/bin:/usr/bin"
        try:
            command = orch.detach_command(Path("/p/.agent-kit/runs/b"), [], "/bin/sr")
        finally:
            if real is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = real
        self.assertIn("--setenv=PATH=/home/dev/.local/bin:/usr/bin", command)

    def test_without_systemd_it_says_so_rather_than_pretending(self):
        real = orch.shutil.which
        orch.shutil.which = lambda name: None if name == "systemd-run" else real(name)
        try:
            unit, why = orch.detach(Path("/p/.agent-kit/runs/b"), [])
        finally:
            orch.shutil.which = real
        self.assertEqual(unit, "")
        self.assertIn("systemd-run", why)
