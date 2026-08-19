"""The stop hook, against the one thing it exists to catch and the many it must not.

    python3 -m unittest discover -s tests

A child ended its turn with `step: "deliver"` in its run file and the driver took thirty minutes to
notice. Blocking that is easy; blocking only that is the design — a hook that fired on the owner's
own session would trap them for most of a night, so the whole test set is about who is *not* judged.
"""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stop_hook", ROOT / "plugins" / "agent-kit" / "hooks" / "stop.py")
stop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stop)
runfile = stop.runfile


class StopHookCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.runs = self.tmp / ".agent-kit" / "runs"
        self.runs.mkdir(parents=True)
        self._session = stop.my_session
        stop.my_session = lambda: "cc-a-feature"
        # Nothing in this file may actually close a session: these tests run inside one.
        self._close = stop.close_myself
        self.closed = []
        stop.close_myself = lambda name: self.closed.append(name) or ""

    def tearDown(self):
        stop.my_session = self._session
        stop.close_myself = self._close
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_file(self, slug, **state):
        (self.runs / slug).mkdir(parents=True, exist_ok=True)
        (self.runs / slug / "run.json").write_text(json.dumps(state), encoding="utf-8")

    def verdict(self, **event):
        payload = {"cwd": str(self.tmp), "hook_event_name": "Stop"}
        payload.update(event)
        out = io.StringIO()
        stdin, sys.stdin = sys.stdin, io.StringIO(json.dumps(payload))
        try:
            with redirect_stdout(out):
                self.assertEqual(stop.main(), 0)
        finally:
            sys.stdin = stdin
        text = out.getvalue().strip()
        return json.loads(text) if text else None

    # ---- the one it exists for ----------------------------------------------------------------

    def test_a_run_left_mid_step_is_refused(self):
        self.run_file("a-feature", session="cc-a-feature", step="deliver")
        said = self.verdict()
        self.assertEqual(said["decision"], "block")
        self.assertIn("a-feature", said["reason"])
        self.assertIn("deliver", said["reason"])

    def test_every_terminal_step_is_allowed(self):
        for step in ("done", "blocked", "skipped"):
            self.run_file("a-feature", session="cc-a-feature", step=step)
            self.assertIsNone(self.verdict(), step)

    # ---- who is not judged --------------------------------------------------------------------

    def test_a_session_the_kit_did_not_start_is_not_judged(self):
        """The owner's own session, `blueprint`, `next`, every side conversation: they own no run
        here, so the hook has nothing to say — by construction, not by a list of exceptions."""
        self.run_file("a-feature", session="cc-somebody-else", step="deliver")
        self.assertIsNone(self.verdict())

    def test_a_session_outside_tmux_is_not_judged(self):
        stop.my_session = lambda: None
        self.run_file("a-feature", session="cc-a-feature", step="deliver")
        self.assertIsNone(self.verdict())

    def test_the_control_window_is_never_matched(self):
        """`window` holds the owner's own session so a batch can be narrated to them. Matching it
        would block the one session this design exists to keep free."""
        self.run_file("a-batch", window="cc-a-feature", step="building")
        self.assertIsNone(self.verdict())

    def test_a_run_handed_over_is_allowed_to_stop_mid_step(self):
        """The driver asked for the handoff, the note is written, and the next session carries on
        from the same file. Refusing here would hold the session open against its one instruction."""
        self.run_file("a-feature", session="cc-a-feature", step="build",
                      handoff="stopped after task 2; the queue seam deadlocks")
        self.assertIsNone(self.verdict())

    def test_an_empty_note_is_not_a_handoff(self):
        for note in (None, "", "   "):
            self.run_file("a-feature", session="cc-a-feature", step="build", handoff=note)
            self.assertIsNotNone(self.verdict(), repr(note))

    def test_a_project_with_no_runs_is_not_judged(self):
        self.assertIsNone(self.verdict())

    def test_a_directory_that_is_not_a_project_is_not_judged(self):
        self.assertIsNone(self.verdict(cwd=str(self.tmp.parent)))

    # ---- the three ways it must not misfire ---------------------------------------------------

    def test_it_refuses_once_and_then_stands_aside(self):
        """Told once, the driver owns it. Two mechanisms fighting over one session is worse than
        either alone."""
        self.run_file("a-feature", session="cc-a-feature", step="deliver")
        self.assertIsNotNone(self.verdict())
        self.assertIsNone(self.verdict(stop_hook_active=True))

    def test_a_step_it_cannot_read_is_not_a_step_to_block_on(self):
        (self.runs / "broken").mkdir()
        (self.runs / "broken" / "run.json").write_text("{not json", encoding="utf-8")
        self.assertIsNone(self.verdict())
        self.run_file("no-step", session="cc-a-feature")
        self.assertIsNone(self.verdict())

    # ---- the finished epic, which nothing else closes -----------------------------------------

    def test_a_finished_epic_closes_its_own_session(self):
        """The hand-back session decides what follows; when nothing follows, no driver comes for
        it. Measured on a live run, it stood for eight hours after writing `done`."""
        for step in ("done", "blocked", "skipped"):
            self.closed.clear()
            self.run_file("an-epic", command="epic", session="cc-a-feature", step=step)
            self.assertIsNone(self.verdict(), step)
            self.assertEqual(self.closed, ["cc-a-feature"], step)

    def test_an_epic_in_flight_is_neither_closed_nor_blocked(self):
        """An `epic` decides one batch, hands the building to a driver that outlives its session,
        and says so. Its steps belong to the run and not to the turn — blocking on them traps the
        one session that has no way to satisfy the condition, and closing it kills a live run."""
        for step in ("gate", "building", "auditing", "proving"):
            self.closed.clear()
            self.run_file("an-epic", command="epic", session="cc-a-feature", step=step)
            self.assertIsNone(self.verdict(), step)
            self.assertEqual(self.closed, [], step)

    def test_a_feature_of_the_same_session_is_still_judged(self):
        """Standing aside for an `epic` is about that run, not about the session."""
        self.run_file("an-epic", command="epic", session="cc-a-feature", step="building")
        self.run_file("a-feature", command="ship", session="cc-a-feature", step="deliver")
        self.assertEqual(self.verdict()["decision"], "block")

    def test_an_epic_nobody_has_touched_for_a_day_closes_nothing(self):
        """A hand-back session's name comes from the run's slug, so it is the same name every time
        that run is picked up. Without the age test a run finished last month would go on closing
        whatever session next carried its name."""
        self.run_file("an-epic", command="epic", session="cc-a-feature", step="done")
        old = time.time() - runfile.STALE_AFTER - 60
        os.utime(self.runs / "an-epic" / "run.json", (old, old))
        self.assertIsNone(self.verdict())
        self.assertEqual(self.closed, [])

    def test_a_finished_feature_is_left_to_the_driver_that_is_watching_it(self):
        """Every other session the kit starts already has a closer, and closing one from here
        would race the driver reading its step."""
        self.run_file("a-feature", command="ship", session="cc-a-feature", step="done")
        self.assertIsNone(self.verdict())
        self.assertEqual(self.closed, [])

    def test_somebody_else_s_finished_epic_is_not_closed(self):
        self.run_file("an-epic", command="epic", session="cc-somebody-else", step="done")
        self.assertIsNone(self.verdict())
        self.assertEqual(self.closed, [])

    def test_the_window_of_a_finished_epic_is_never_closed(self):
        """`window` is the owner's own session. Closing it is the one mistake this whole design is
        built to make impossible."""
        self.run_file("an-epic", command="epic", window="cc-a-feature", step="done")
        self.assertIsNone(self.verdict())
        self.assertEqual(self.closed, [])

    def test_a_finished_epic_beside_a_feature_mid_step_closes_nothing(self):
        """Two run files, one session. The unfinished one is what the turn is judged on, and the
        session stays up: closing it here would kill a session with work in flight."""
        self.run_file("an-epic", command="epic", session="cc-a-feature", step="done")
        self.run_file("a-feature", command="ship", session="cc-a-feature", step="build")
        self.assertEqual(self.verdict()["decision"], "block")
        self.assertEqual(self.closed, [])

    def test_a_handed_over_run_does_not_hide_another_of_the_same_session(self):
        """A handoff means *no opinion about that run*, not *no opinion about this session*. The
        loop used to return on the first one it saw, alphabetically."""
        self.run_file("a-handed-over", command="ship", session="cc-a-feature", step="build",
                      handoff="stopped after task 2")
        self.run_file("b-still-going", command="ship", session="cc-a-feature", step="deliver")
        said = self.verdict()
        self.assertEqual(said["decision"], "block")
        self.assertIn("b-still-going", said["reason"])

    def test_a_close_that_failed_is_said_out_loud(self):
        stop.close_myself = lambda name: "tmux is not installed"
        self.run_file("an-epic", command="epic", session="cc-a-feature", step="done")
        said = self.verdict()
        self.assertIn("could not close this session", said["systemMessage"])
        self.assertIn("tmux is not installed", said["systemMessage"])
        self.assertNotIn("decision", said)

    def test_a_broken_hook_says_so_rather_than_going_quiet(self):
        stop.my_session = lambda: (_ for _ in ()).throw(RuntimeError("tmux exploded"))
        said = self.verdict()
        self.assertIn("could not judge", said["systemMessage"])
        self.assertNotIn("decision", said)


class ClosingCase(unittest.TestCase):
    """`close_myself`, which is where the defect this whole change exists for actually lived.

    The line that used to be in `epic/SKILL.md` was `tmux kill-session` and nothing else. It killed
    the session and left it registered with the helper that started it, and a watchdog restored it
    a minute later with *Continue from where you left off* typed into it.
    """

    def setUp(self):
        self.calls = []
        self._which, self._run = stop.shutil.which, stop.subprocess.run

    def tearDown(self):
        stop.shutil.which, stop.subprocess.run = self._which, self._run

    def arrange(self, helper: str | None, code: int = 0, stderr: str = "", stdout: str = ""):
        stop.shutil.which = lambda name: helper if name == "claude-close" else None

        def fake(args, **_kwargs):
            self.calls.append(tuple(args))
            return subprocess.CompletedProcess(args, code, stdout, stderr)

        stop.subprocess.run = fake

    def test_the_helper_is_asked_first_and_tmux_is_not_a_second_opinion(self):
        """It unregisters, then kills on its own clock. A tmux kill on top buys nothing and would
        run against a session the helper has already accounted for."""
        self.arrange("/usr/bin/claude-close")
        self.assertEqual(stop.close_myself("cc-e-advance"), "")
        self.assertEqual(self.calls, [("/usr/bin/claude-close",)])

    def test_a_helper_that_refused_is_reported_and_nothing_is_killed(self):
        """Non-zero means *do not kill this* — it protects the machine's control sessions, and it
        also means the unregistering did not happen, which is the exact state where a bare kill
        brings the session back."""
        self.arrange("/usr/bin/claude-close", code=1, stderr="Основную управляющую закрывать нельзя.")
        said = stop.close_myself("cc-e-advance")
        self.assertIn("закрывать нельзя", said)
        self.assertEqual(len(self.calls), 1)

    def test_a_helper_that_said_nothing_at_all_still_reports(self):
        self.arrange("/usr/bin/claude-close", code=3)
        self.assertIn("exited 3", stop.close_myself("cc-e-advance"))

    def test_without_a_helper_tmux_is_the_whole_answer(self):
        self.arrange(None)
        self.assertEqual(stop.close_myself("cc-e-advance"), "")
        self.assertEqual(self.calls, [("tmux", "kill-session", "-t", "cc-e-advance")])

    def test_a_tmux_that_refused_says_so(self):
        self.arrange(None, code=1, stderr="no server running")
        self.assertIn("no server running", stop.close_myself("cc-e-advance"))

    def test_a_call_that_never_returns_is_not_a_hung_session(self):
        stop.shutil.which = lambda name: "/usr/bin/claude-close"

        def hang(args, **_kwargs):
            raise subprocess.TimeoutExpired(args, 20)

        stop.subprocess.run = hang
        self.assertIn("did not finish", stop.close_myself("cc-e-advance"))


if __name__ == "__main__":
    unittest.main()
