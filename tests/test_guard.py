#!/usr/bin/env python3
"""Tests for the never-rules in `guard.py`.

The hook has had no tests: it was one file with its decision inline, and the only way to exercise
it was to feed it a hook event on stdin. The decision is now `refusal()`, because a second caller
needs it — `blueprint_check.py` runs the commands a project's knowledge contract declares, and a
`PreToolUse` hook never sees a subprocess a script starts.

Two things are asserted here. That the rules still say what they said, so extracting them changed
nothing; and that the hook still speaks the protocol Claude Code expects, since that half is what
no test could reach before.

Run directly (`python3 tests/test_guard.py`); `scripts/validate.sh` runs it the same way.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir))
sys.path.insert(0, os.path.join(REPO, "plugins", "agent-kit", "scripts"))

import guard  # noqa: E402  — the path above is what makes this importable from any cwd

SCRIPT = os.path.join(REPO, "plugins", "agent-kit", "scripts", "guard.py")


class NeverRulesTest(unittest.TestCase):
    def assertRefused(self, command, fragment, decision=guard.ASK):
        refused = guard.refusal(command)
        self.assertIsNotNone(refused, f"{command!r} was allowed")
        self.assertIn(fragment, refused.reason)
        self.assertEqual(refused.decision, decision, command)

    def test_merging_a_pull_request(self):
        self.assertRefused("gh pr merge 7", "never merges pull requests")
        self.assertRefused("gh pr merge --squash --admin 7", "never merges pull requests")

    def test_force_push(self):
        self.assertRefused("git push --force origin claude/x", "force push")
        self.assertRefused("git push -f origin claude/x", "force push")
        self.assertRefused("git push --force-with-lease origin claude/x", "force push")

    def test_pushing_the_default_branch_by_refspec(self):
        self.assertRefused("git push origin main", "default branch")
        self.assertRefused("git push origin HEAD:main", "default branch")
        self.assertRefused("git push origin HEAD:refs/heads/main", "default branch")

    def test_a_rule_fires_from_any_segment_of_a_pipeline(self):
        """The whole point of splitting on separators: the second command counts too."""
        self.assertRefused("make test && gh pr merge 7", "never merges pull requests")
        self.assertRefused("true; git push --force origin x", "force push")

    def test_ordinary_commands_pass(self):
        for command in ("make test", "git push origin claude/knowledge-contract",
                        "git push --set-upstream origin claude/x", "gh pr create --fill",
                        "gh pr view 12 --json url", "pytest -q && ruff check ."):
            with self.subTest(command=command):
                self.assertIsNone(guard.refusal(command), command)

    def test_a_rule_named_inside_a_quoted_string_is_not_a_command(self):
        """A guard that cries wolf teaches everyone to click through it."""
        self.assertIsNone(guard.refusal('echo "git push --force origin main"'))
        self.assertIsNone(guard.refusal("printf '%s' 'gh pr merge'"))

    def test_a_leading_environment_assignment_does_not_hide_a_rule(self):
        self.assertRefused("CI=1 gh pr merge 7", "never merges pull requests")

    def test_an_unparsable_segment_is_still_judged(self):
        """`shlex` raises on an unbalanced quote; the words are still there to read."""
        self.assertRefused('gh pr merge "unbalanced', "never merges pull requests")


class RunStateRuleTest(unittest.TestCase):
    """The step gate's construction is that the agent cannot write run state. This is half of it."""

    def assertDenied(self, command):
        refused = guard.refusal(command)
        self.assertIsNotNone(refused, f"{command!r} was allowed")
        self.assertEqual(refused.decision, guard.DENY, command)
        self.assertIn(".agent-kit/runs/", refused.reason)

    def test_a_shell_command_naming_run_state_is_denied(self):
        """Blunt on purpose: a precise rule about redirects, `tee` and `cp` targets would leak."""
        for command in ("echo done > .agent-kit/runs/claude-x.yml",
                        "sed -i s/open/verified/ .agent-kit/runs/claude-x.yml",
                        "cp /tmp/forged.yml .agent-kit/runs/claude-x.yml",
                        "rm -rf .agent-kit/runs",
                        "cat .agent-kit/runs/claude-x.yml",
                        "make test && echo x >> .agent-kit/runs/claude-x.yml",
                        "printf verified | tee /repo/.agent-kit/runs/claude-x.yml"):
            with self.subTest(command=command):
                self.assertDenied(command)

    def test_the_decision_is_deny_not_ask(self):
        """A headless sprint child has nobody to answer an `ask`, and a hanging child is worse."""
        self.assertEqual(guard.refusal("rm .agent-kit/runs/x.yml").decision, guard.DENY)
        self.assertEqual(guard.refusal("gh pr merge 7").decision, guard.ASK)

    def test_the_gate_itself_passes(self):
        for command in ('python3 "/plugins/agent-kit/scripts/gate.py" step settle Test',
                        "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gate.py step skip PR "
                        "--reason no_remote",
                        "python3 /x/scripts/gate.py state"):
            with self.subTest(command=command):
                self.assertIsNone(guard.refusal(command), command)

    def test_an_unrelated_command_passes(self):
        for command in ("ls .agent-kit/project", "cat .agent-kit/knowledge/contract.yml",
                        "grep -rn runs docs/"):
            with self.subTest(command=command):
                self.assertIsNone(guard.refusal(command), command)


class HookProtocolTest(unittest.TestCase):
    """The half of the hook that is not the decision: what Claude Code reads back."""

    def run_hook(self, payload):
        return subprocess.run([sys.executable, SCRIPT], input=json.dumps(payload),
                              capture_output=True, text=True, cwd=REPO)

    def test_a_refused_command_asks_rather_than_denies(self):
        done = self.run_hook({"tool_input": {"command": "gh pr merge 7"}})
        self.assertEqual(done.returncode, 0)
        decision = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["hookEventName"], "PreToolUse")
        self.assertEqual(decision["permissionDecision"], "ask")
        self.assertIn("never merges pull requests", decision["permissionDecisionReason"])

    def test_an_ordinary_command_passes_through_silently(self):
        done = self.run_hook({"tool_input": {"command": "make test"}})
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stdout.strip(), "")

    def test_a_malformed_event_fails_open(self):
        """A wedged hook is worse than no hook: anything unreadable lets the tool call through."""
        for payload in ("not json at all", "", "[]"):
            with self.subTest(payload=payload):
                done = subprocess.run([sys.executable, SCRIPT], input=payload, capture_output=True,
                                      text=True, cwd=REPO)
                self.assertEqual(done.returncode, 0)
                self.assertEqual(done.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
