"""The guard, against the commands it exists to refuse.

    python3 -m unittest discover -s tests

A guard nobody tests is the previous version of this idea: the `Stop` hook checked that a step had
a line in a log the agent wrote itself, so it guaranteed nothing while looking like protection.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "plugins" / "agent-kit" / "hooks" / "guard.py"
SPEC = importlib.util.spec_from_file_location("guard", GUARD)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class VerdictCase(unittest.TestCase):
    """What the guard refuses, and — as important — what it lets past."""

    def refused(self, command, branch="claude/feature", default="main"):
        return guard.verdict(command, branch, default)

    def test_merging_a_pull_request(self):
        self.assertIn("Merging is the owner's", self.refused("gh pr merge 42 --squash"))

    def test_merging_hidden_behind_another_command(self):
        self.assertIsNotNone(self.refused("cd /srv/app && gh pr merge 42"))

    def test_a_force_push(self):
        self.assertIn("rewrites history", self.refused("git push --force origin claude/feature"))
        self.assertIsNotNone(self.refused("git push -f origin claude/feature"))
        self.assertIsNotNone(self.refused("git push --force-with-lease"))

    def test_pushing_the_default_branch_by_name(self):
        self.assertIsNotNone(self.refused("git push origin main"))
        self.assertIsNotNone(self.refused("git push origin HEAD:main"))

    def test_a_bare_push_while_standing_on_the_default_branch(self):
        self.assertIsNotNone(self.refused("git push", branch="main"))

    def test_the_push_a_run_is_supposed_to_make(self):
        self.assertIsNone(self.refused("git push -u origin claude/feature"))
        self.assertIsNone(self.refused("git push origin sprint/2026-08-06-scenarios"))

    def test_the_commands_a_run_lives_on(self):
        for command in ("git commit -m 'feat: x'", "gh pr create --base main --head claude/x",
                        "make test", "git fetch origin", "gh pr checks", "git log --oneline -5"):
            self.assertIsNone(self.refused(command), command)

    def test_a_branch_named_after_the_default_one_is_not_the_default_one(self):
        self.assertIsNone(self.refused("git push -u origin claude/mainline-fix"))


class EventCase(unittest.TestCase):
    """End to end, the way Claude Code calls it: JSON on stdin, JSON on stdout."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / ".agent-kit" / "runs" / "x").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_guard(self, command, step="build", tool="Bash"):
        (self.tmp / ".agent-kit" / "runs" / "x" / "run.json").write_text(
            json.dumps({"slug": "x", "step": step}), encoding="utf-8")
        done = subprocess.run(
            [sys.executable, str(GUARD)], input=json.dumps(
                {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(self.tmp)}),
            capture_output=True, text=True, timeout=30)
        return done.returncode, done.stdout

    def test_a_run_in_flight_is_refused(self):
        code, out = self.run_guard("gh pr merge 42")
        self.assertEqual(code, 0)                  # the hook itself succeeded
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_a_finished_run_leaves_the_owner_alone(self):
        """The whole point of keying on the run file: outside a run this must not exist."""
        code, out = self.run_guard("gh pr merge 42", step="done")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_another_tool_is_none_of_its_business(self):
        _code, out = self.run_guard("gh pr merge 42", tool="Read")
        self.assertEqual(out.strip(), "")

    def test_a_project_the_kit_never_touched(self):
        shutil.rmtree(self.tmp / ".agent-kit")
        done = subprocess.run(
            [sys.executable, str(GUARD)], input=json.dumps(
                {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"},
                 "cwd": str(self.tmp)}), capture_output=True, text=True, timeout=30)
        self.assertEqual(done.stdout.strip(), "")

    def test_nonsense_on_stdin_allows_and_says_nothing(self):
        done = subprocess.run([sys.executable, str(GUARD)], input="not json",
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
