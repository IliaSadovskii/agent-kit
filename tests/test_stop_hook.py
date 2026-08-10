"""The stop hook, against the one thing it exists to catch and the many it must not.

    python3 -m unittest discover -s tests

A child ended its turn with `step: "deliver"` in its run file and the driver took thirty minutes to
notice. Blocking that is easy; blocking only that is the design — a hook that fired on the owner's
own session would trap them for most of a night, so the whole test set is about who is *not* judged.
"""

import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stop_hook", ROOT / "plugins" / "agent-kit" / "hooks" / "stop.py")
stop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stop)


class StopHookCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.runs = self.tmp / ".agent-kit" / "runs"
        self.runs.mkdir(parents=True)
        self._session = stop.my_session
        stop.my_session = lambda: "cc-a-feature"

    def tearDown(self):
        stop.my_session = self._session
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

    def test_a_broken_hook_says_so_rather_than_going_quiet(self):
        stop.my_session = lambda: (_ for _ in ()).throw(RuntimeError("tmux exploded"))
        said = self.verdict()
        self.assertIn("could not judge", said["systemMessage"])
        self.assertNotIn("decision", said)


if __name__ == "__main__":
    unittest.main()
