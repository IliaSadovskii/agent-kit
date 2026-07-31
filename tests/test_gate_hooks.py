#!/usr/bin/env python3
"""Tests for the four hooks the step gate rests on, driven by crafted events on stdin.

The plugin runs from an installed copy under `~/.claude/plugins/cache/`, never from this working
tree, so nothing here can make Claude Code call these scripts — that is what makes it safe to
rewrite the `Stop` hook mid-sprint, and it is also why an end-to-end layer does not exist for them.
The design names this as the verification rather than as a substitute for one: a hook is a program
that reads JSON on stdin and answers on stdout, so the event is crafted, the process is run, and the
answer is asserted.

Layers, and why each one is here:

* **contract** — the JSON protocol Claude Code reads back: `hookSpecificOutput.hookEventName`,
  `permissionDecision`, and the `{"decision": "block"}` shape of a `Stop` answer. A hook that
  decides correctly and speaks the wrong shape decides nothing at all.
* **integration** — `stop-guard.py` against real run state in a real git repository, because what
  it answers depends on the checked-out branch and on a file the gate wrote.
* **unit** — the path rule behind the `Write|Edit` hook, exercised through the hook itself.
* **regression** — the sprint-orchestrator case: a headless child checks the shared working tree
  out onto its own branch, and the old `Stop` guard read the child's plan as the orchestrator's
  unfinished run, demanding every turn the exact action the sprint contract forbids it to take.
  `test_another_session_s_run_never_holds_this_one` is that defect, kept failing-able.

Not covered here, deliberately: the `.sh` wrappers are two lines of `exec python3` and are already
syntax-checked and permission-checked by `scripts/validate.sh`; and there is no snapshot layer,
because this repository has no snapshot machinery and reason text that nobody may edit is worse
than reason text nobody tests.

Run directly (`python3 tests/test_gate_hooks.py`); `scripts/validate.sh` runs it the same way.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir))
PLUGIN = os.path.join(REPO, "plugins", "agent-kit")
SCRIPTS = os.path.join(PLUGIN, "scripts")
sys.path.insert(0, SCRIPTS)

import kit_gate  # noqa: E402  — the path above is what makes this importable from any cwd
import kit_yaml  # noqa: E402

WRITE_GUARD = os.path.join(SCRIPTS, "write-guard.py")
BASH_GUARD = os.path.join(SCRIPTS, "guard.py")
STOP_GUARD = os.path.join(SCRIPTS, "stop-guard.py")
SESSION_START = os.path.join(SCRIPTS, "session-start.sh")

BRANCH = "claude/gate-run"
SESSION = "44608e54-ff5f-41b5-9ef6-0ae14aeb96ef"
OTHER_SESSION = "0f0d9b21-1111-2222-3333-444444444444"

# Claude Code caps a hook's whole output at 10,000 characters; past it the output is written to a
# file and replaced with a preview, and always-on governance silently stops being on.
HOOK_OUTPUT_CAP = 10000


class HookMixin:
    def run_hook(self, script, payload, cwd=REPO, env=None):
        """One hook process, fed a crafted event. `payload` is a str when it is not valid JSON."""
        text = payload if isinstance(payload, str) else json.dumps(payload)
        environment = dict(os.environ)
        environment.pop("CLAUDE_PROJECT_DIR", None)
        environment.update(env or {})
        return subprocess.run([sys.executable, script], input=text, capture_output=True, text=True,
                              cwd=cwd, env=environment)

    def assertSilent(self, done, why=""):
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "", why or done.stdout)

    def decision(self, done):
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.strip(), "the hook said nothing")
        return json.loads(done.stdout)


class WriteGuardTest(unittest.TestCase, HookMixin):
    """The `Write|Edit` half of keeping run state out of the agent's reach.

    The Bash guard covers a shell command. Without this one, a single `Write` walks around it and
    the gate's whole construction — a step the agent cannot close by hand — is paper.
    """

    def event(self, tool, path):
        return {"hook_event_name": "PreToolUse", "tool_name": tool,
                "tool_input": {"file_path": path}}

    def assertDenied(self, tool, path):
        answer = self.decision(self.run_hook(WRITE_GUARD, self.event(tool, path)))
        specific = answer["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PreToolUse")
        self.assertEqual(specific["permissionDecision"], "deny",
                         "a headless sprint child has nobody to answer an `ask`")
        self.assertIn("only the gate writes it", specific["permissionDecisionReason"])
        self.assertIn(path, specific["permissionDecisionReason"])

    def test_a_write_to_run_state_is_denied(self):
        for tool in ("Write", "Edit"):
            for path in (".agent-kit/runs/claude-gate-run.yml",
                         "/home/dev/projects/kit/.agent-kit/runs/claude-x.yml",
                         "/somewhere/else/checked/out/.agent-kit/runs/claude-x.yml",
                         ".agent-kit/runs/.gitignore"):
                with self.subTest(tool=tool, path=path):
                    self.assertDenied(tool, path)

    def test_an_ordinary_file_is_not_the_hook_s_business(self):
        for path in ("docs/plans/2026-07-31-step-gate.md", ".agent-kit/project/manifest.yml",
                     ".agent-kit/knowledge/contract.yml", "runs/notes.md"):
            with self.subTest(path=path):
                self.assertSilent(self.run_hook(WRITE_GUARD, self.event("Write", path)))

    def test_every_field_a_tool_names_its_target_by_is_read(self):
        """A matcher that grows a tool this hook does not know about should still be read."""
        for field in ("file_path", "filePath", "path", "notebook_path"):
            with self.subTest(field=field):
                event = {"tool_name": "Write", "tool_input": {field: ".agent-kit/runs/x.yml"}}
                answer = self.decision(self.run_hook(WRITE_GUARD, event))
                self.assertEqual(answer["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_an_unreadable_event_fails_open(self):
        """A wedged hook is worse than no hook: anything it cannot read lets the tool call through."""
        for payload in ("not json at all", "", "[]", '{"tool_name": "Write"}',
                        '{"tool_input": null}', '{"tool_input": {"file_path": 12}}'):
            with self.subTest(payload=payload):
                self.assertSilent(self.run_hook(WRITE_GUARD, payload))


class BashGuardTest(unittest.TestCase, HookMixin):
    """The same rule on the other door. `test_guard.py` covers the decision; this is the protocol."""

    def event(self, command):
        return {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                "tool_input": {"command": command}}

    def test_a_command_naming_run_state_is_denied_through_the_hook(self):
        answer = self.decision(self.run_hook(
            BASH_GUARD, self.event("sed -i s/open/verified/ .agent-kit/runs/claude-x.yml")))
        specific = answer["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PreToolUse")
        self.assertEqual(specific["permissionDecision"], "deny")
        self.assertIn("run reset", specific["permissionDecisionReason"],
                      "the refusal has to name the sanctioned way out of an abandoned run — "
                      "otherwise the only way past it is a spelling the rule failed to model")

    def test_the_never_rules_still_ask_rather_than_deny(self):
        """Two strengths on purpose: a human confirms a merge in one click; nobody writes state."""
        answer = self.decision(self.run_hook(BASH_GUARD, self.event("gh pr merge 7")))
        self.assertEqual(answer["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_the_gate_s_own_invocation_passes(self):
        """The rule has no exemption, and the gate needs none.

        The gate derives the state file's path from the branch and takes no path argument, so it
        never names the directory. An exemption for it would therefore only ever have covered
        `gate.py state > .agent-kit/runs/<branch>.yml` — a redirect in the same segment, which is
        the precise write the rule exists to refuse. The last case below is that redirect, and it
        must be denied like any other.
        """
        for command in ('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" step settle Test',
                        "python3 /plugins/agent-kit/scripts/gate.py step skip PR "
                        "--reason no_remote",
                        "python3 /x/scripts/gate.py state"):
            with self.subTest(command=command):
                self.assertSilent(self.run_hook(BASH_GUARD, self.event(command)))

        answer = self.decision(self.run_hook(
            BASH_GUARD, self.event("python3 /x/scripts/gate.py state > .agent-kit/runs/x.yml")))
        self.assertEqual(answer["hookSpecificOutput"]["permissionDecision"], "deny")


class StopGuardTest(unittest.TestCase, HookMixin):
    """The turn is held while a declared step has no verdict — and only then.

    Every case below is a way the guard could hold a session that has nothing to do with the run.
    A guard that cannot be satisfied is worse than no guard, so silence is the default and the block
    is the exception that has to be earned.
    """

    def setUp(self):
        self.root = self.make_repo()

    def make_repo(self, branch=BRANCH):
        root = tempfile.mkdtemp(prefix="kit-stop-")
        self.addCleanup(shutil.rmtree, root, True)
        self.git(root, "init", "-q")
        self.git(root, "config", "user.email", "gate@example.test")
        self.git(root, "config", "user.name", "Gate Test")
        self.git(root, "config", "commit.gpgsign", "false")
        with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as handle:
            handle.write("a fixture project\n")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "initial")
        self.git(root, "checkout", "-qb", branch)
        return root

    def git(self, root, *args):
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, f"git {' '.join(args)}: {done.stderr}")
        return done.stdout.strip()

    def state(self, root=None, branch=BRANCH, pipeline="ship", run_state=kit_gate.RUN_OPEN,
              session=SESSION, settled=("Design",), at=None):
        """A run written the way the gate writes it, with `settled` steps already attested.

        `at` puts the file where a *different* branch's run would live, which is the only way to
        stage the case the branch field exists for: the file the guard opens saying it belongs to
        somebody else.
        """
        root = root or self.root
        document = {
            "version": 1, "branch": branch, "pipeline": pipeline, "session": session,
            "state": run_state, "opened_at": kit_gate.now(), "opened_at_commit": "",
            "steps": [{"name": name, "verdict": kit_gate.ATTESTED, "attempts": 1,
                       "evidence": "done"} for name in settled],
        }
        path = kit_gate.state_path(root, at if at is not None else branch)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(kit_yaml.dump(document))
        return document

    def stop(self, root=None, session=SESSION, active=False):
        return self.run_hook(STOP_GUARD, {"hook_event_name": "Stop", "cwd": root or self.root,
                                          "session_id": session, "stop_hook_active": active})

    # -- the one case that holds -------------------------------------------------------------

    def test_an_open_run_with_an_unsettled_step_holds_the_turn(self):
        self.state()
        answer = self.decision(self.stop())
        self.assertEqual(answer["decision"], "block")
        reason = answer["reason"]
        listed = reason.splitlines()[1].split(", ")
        self.assertEqual(listed, ["Plan", "Build", "Test", "Review", "Security", "PR", "Docs"],
                         "the reason names what is left, in order, and nothing that is settled")
        self.assertIn("step settle", reason, "the agent has to be told to ask the gate")
        self.assertIn("do not write the verdict yourself", reason)

    def test_a_run_with_no_owner_holds_whoever_is_here(self):
        """Unset is legal and means a repository with one session in it, which is most of them."""
        self.state(session=None)
        self.assertEqual(self.decision(self.stop(session=OTHER_SESSION))["decision"], "block")

    # -- every way it lets go ----------------------------------------------------------------

    def test_no_state_file_means_no_run(self):
        """An ordinary conversation, and every repository that never ran a pipeline."""
        self.assertSilent(self.stop())

    def test_the_second_nudge_of_a_turn_is_silence(self):
        """`stop_hook_active` is the hook firing on the turn it forced open. Nudge once."""
        self.state()
        self.assertSilent(self.stop(active=True))

    def test_another_branch_s_run_is_not_this_one(self):
        """Two branch names can slug to one file name, so the file the guard opens has to say
        which branch it belongs to — and be believed over the name it was found under."""
        self.state(branch="claude/somebody-else", at=BRANCH)
        self.assertSilent(self.stop())

    def test_another_session_s_run_never_holds_this_one(self):
        """The sprint-orchestrator defect this feature exists to absorb.

        The orchestrator and its headless child share one working tree, and the child checks that
        tree out onto its own branch. Keyed by branch alone, the orchestrator reads the child's run
        as its own and is told every turn to carry on a pipeline the sprint contract forbids it to
        touch. The run therefore records the session that opened it, and holds only that session.
        """
        self.state(session=SESSION)
        self.assertSilent(self.stop(session=OTHER_SESSION),
                          "the orchestrator is being held for its child's run")
        self.assertEqual(self.decision(self.stop(session=SESSION))["decision"], "block",
                         "and the child itself is still held")

    def test_a_finished_run_lets_go(self):
        self.state(run_state=kit_gate.RUN_FINISHED)
        self.assertSilent(self.stop())

    def test_a_blocked_run_lets_go(self):
        """A gate that can deadlock a run has replaced one failure mode with a worse one."""
        self.state(run_state=kit_gate.RUN_BLOCKED)
        self.assertSilent(self.stop())

    def test_a_run_with_every_step_settled_lets_go(self):
        steps = [step.name for step in kit_gate.load_pipelines(
            os.path.join(PLUGIN, "pipelines.default.yml"))["ship"]]
        self.state(settled=tuple(steps))
        self.assertSilent(self.stop())

    def test_unreadable_state_fails_open(self):
        for text in ("", "steps:\n  - name: Design\n     verdict: attested\n",
                     "- not\n- a\n- run\n", "version: 1\nbranch: " + BRANCH + "\n",
                     "version: 1\nsteps: []\nbranch: [\n"):
            with self.subTest(text=text.strip()[:24]):
                path = kit_gate.state_path(self.root, BRANCH)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
                self.assertSilent(self.stop())

    def test_a_pipeline_the_definitions_no_longer_declare_fails_open(self):
        """A run opened by an older release must not wedge every turn of the session that finds it."""
        self.state(pipeline="retired")
        self.assertSilent(self.stop())

    def test_a_detached_head_has_no_run_to_hold(self):
        """No branch means no run — including the file a nameless branch would key to, which is
        what the guard would otherwise pick up while the session is on no branch at all."""
        self.state()
        self.state(branch="", at="")
        self.git(self.root, "checkout", "-q", "--detach", "HEAD")
        self.assertSilent(self.stop())

    def test_an_unreadable_event_fails_open(self):
        for payload in ("not json at all", "", "[]"):
            with self.subTest(payload=payload):
                self.state()
                self.assertSilent(self.run_hook(STOP_GUARD, payload))


class SessionStartTest(unittest.TestCase, HookMixin):
    """`engine.md`, and after it the run this branch is in the middle of.

    A resumed or compacted session is the one that most needs the second half: it has lost the run's
    working memory. It is also the half that can break the first one, so the hook is written to
    survive a gate that fails, and this is where that is proved.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="kit-session-")
        self.addCleanup(shutil.rmtree, self.root, True)
        for args in (("init", "-q"), ("config", "user.email", "gate@example.test"),
                     ("config", "user.name", "Gate Test"), ("config", "commit.gpgsign", "false")):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        with open(os.path.join(self.root, "README.md"), "w", encoding="utf-8") as handle:
            handle.write("a fixture project\n")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "initial"], cwd=self.root, check=True,
                       capture_output=True)
        subprocess.run(["git", "checkout", "-qb", BRANCH], cwd=self.root, check=True,
                       capture_output=True)

    def engine(self):
        with open(os.path.join(PLUGIN, "engine.md"), encoding="utf-8") as handle:
            return handle.read()

    def hook(self, plugin_root=PLUGIN):
        environment = dict(os.environ)
        environment.pop("CLAUDE_PROJECT_DIR", None)
        environment["CLAUDE_PLUGIN_ROOT"] = plugin_root
        return subprocess.run(["bash", os.path.join(plugin_root, "scripts", "session-start.sh")],
                              cwd=self.root, capture_output=True, text=True, env=environment)

    def open_run(self, **fields):
        document = {"version": 1, "branch": BRANCH, "pipeline": "ship", "session": SESSION,
                    "state": kit_gate.RUN_OPEN, "opened_at": kit_gate.now(),
                    "opened_at_commit": "", "steps": [{"name": "Design",
                                                       "verdict": kit_gate.ATTESTED,
                                                       "attempts": 1, "evidence": "designed"}]}
        document.update(fields)
        kit_gate.write_state(self.root, document)
        return document

    def test_with_no_run_the_hook_is_engine_md_and_nothing_else(self):
        done = self.hook()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, self.engine())

    def test_an_unfinished_run_is_appended_after_engine_md(self):
        self.open_run()
        done = self.hook()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.startswith(self.engine()),
                        "the governance must come first and whole")
        appended = done.stdout[len(self.engine()):]
        self.assertIn(f"unfinished run on {BRANCH}", appended)
        self.assertIn("**Next: Plan**", appended)
        self.assertLessEqual(len(appended), kit_gate.STATE_CAP)

    def test_the_whole_hook_stays_inside_the_output_cap(self):
        """Past 10,000 characters Claude Code files the output away and shows a preview instead."""
        self.open_run()
        done = self.hook()
        self.assertLess(len(done.stdout), HOOK_OUTPUT_CAP,
                        "engine.md plus the gate's share no longer fits the SessionStart budget")

    def test_a_gate_that_fails_does_not_fail_the_hook(self):
        """The governance is the load-bearing half; a broken gate must not take it down."""
        broken = tempfile.mkdtemp(prefix="kit-broken-plugin-")
        self.addCleanup(shutil.rmtree, broken, True)
        shutil.copy(os.path.join(PLUGIN, "engine.md"), os.path.join(broken, "engine.md"))
        shutil.copytree(SCRIPTS, os.path.join(broken, "scripts"))
        with open(os.path.join(broken, "scripts", "gate.py"), "w", encoding="utf-8") as handle:
            handle.write("this is not python(\n")

        self.open_run()
        done = self.hook(plugin_root=broken)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, self.engine())

    def test_a_corrupt_state_file_does_not_fail_the_hook(self):
        path = kit_gate.state_path(self.root, BRANCH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("steps:\n  - name: Design\n     verdict: attested\n")
        done = self.hook()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, self.engine())

    def test_the_state_the_hook_prints_is_the_state_on_disk(self):
        """The hook is the only always-on reader of run state, so it must not paraphrase it."""
        document = self.open_run()
        self.assertEqual(kit_yaml.load_path(kit_gate.state_path(self.root, BRANCH)), document)


if __name__ == "__main__":
    unittest.main()
