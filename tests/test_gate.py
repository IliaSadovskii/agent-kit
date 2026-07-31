#!/usr/bin/env python3
"""Tests for the step gate: pipeline definitions, run state, the checks, and the CLI.

A step is closed by the gate and by nothing else, so everything the gate refuses is a guarantee the
rest of the kit rests on. These tests are written against that promise rather than against the
implementation: each one asserts what the agent is allowed to get away with.

Layers, and why each one is here:

* **unit** — the definition parser, the branch slug, and the summary cap. String and dict work,
  asserted directly, including every declaration the schema names and the gate refuses to guess at.
* **integration** — the checks, against a real git repository in a temporary directory, a real bare
  remote, and real shell exit codes. A mocked `git` would only restate what the test already
  assumed, and `commits_on_branch` counting the wrong span is exactly the bug a mock would hide.
* **contract** — the CLI driven as a subprocess: exit codes, what lands on stderr, and the state
  file that results. That triple is what the skills, the hooks and the agent all read.
* **contract, definition against prose** — the shipped `pipelines.default.yml` loads, and its step
  names are the ones `skills/ship` and `skills/fix` tell the agent to ask for. The two files are
  edited a commit apart, and a name that drifts makes every `step start` in the skill fail.
* **property-based** (fixed seeds, stdlib `random`) — pseudo-random walks of `start` / `settle` /
  `skip` against the invariants the design names. The walk drives the real command functions, so a
  transition the unit tests did not think of is still judged by the same rules.

Two layers are deliberately absent. There is no end-to-end layer: the plugin runs from an installed
copy under `~/.claude/plugins/`, so nothing here can exercise Claude Code invoking the gate — the
hook tests in `tests/test_gate_hooks.py` are that verification, per the design. And there is no
performance layer: the only stated budget is `CHECK_TIMEOUT`, and a test that waits 1,800 seconds to
prove a timeout is a slow test, not a fast guarantee.

Run directly (`python3 tests/test_gate.py`); `scripts/validate.sh` runs it the same way.
"""
import contextlib
import io
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir))
PLUGIN = os.path.join(REPO, "plugins", "agent-kit")
sys.path.insert(0, os.path.join(PLUGIN, "scripts"))

import gate  # noqa: E402  — the path above is what makes this importable from any cwd
import kit_gate  # noqa: E402
import kit_yaml  # noqa: E402

GATE_SCRIPT = os.path.join(PLUGIN, "scripts", "gate.py")
SHIPPED_PIPELINES = os.path.join(PLUGIN, "pipelines.default.yml")

BRANCH = "claude/gate-run"

# A failure has to be reproducible from the report alone, so the seeds are fixed and printed.
SEEDS = (1, 2026073, 17, 424242, 99991, 5, 20260731, 8675309)

# ----------------------------------------------------------------------------------------------
# Fixture pipelines. They live here rather than under tests/fixtures/ because two of them declare a
# check that fails on purpose, which the shipped file has no business containing — `KIT_PIPELINES`
# is the documented seam for exactly that, and a definition read a screen away from the assertion
# that depends on it is a definition nobody re-reads.

DEMO = """
version: 1
pipelines:
  demo:
    steps:
      - name: Design
        done_when: []
        max_attempts: 1
        on_exhausted: block

      - name: Build
        requires:
          - Design
        done_when:
          - run: exit 0
        max_attempts: 2
        on_exhausted: block

      - name: Extra
        requires:
          - Build
        done_when: []
        max_attempts: 1
        optional: true

      - name: PR
        requires:
          - Build
        done_when: []
        max_attempts: 2
        on_exhausted: block
        skippable_when:
          - no_remote
  other:
    steps:
      - name: Only
        done_when: []
        max_attempts: 1
"""

HARD = """
version: 1
pipelines:
  hard:
    steps:
      - name: Build
        done_when:
          - run: echo BOOM_MARKER; exit 3
        max_attempts: 2
        on_exhausted: block

      - name: After
        requires:
          - Build
        done_when: []
        max_attempts: 1
  soft:
    steps:
      - name: Build
        done_when:
          - run: exit 5
        max_attempts: 2
        on_exhausted: continue

      - name: After
        requires:
          - Build
        done_when: []
        max_attempts: 1
"""

WALK = """
version: 1
pipelines:
  walk:
    steps:
      - name: Alpha
        done_when: []
        max_attempts: 1
        on_exhausted: block

      - name: Beta
        requires:
          - Alpha
        done_when:
          - run: exit 7
        max_attempts: 2
        on_exhausted: continue

      - name: Gamma
        requires:
          - Beta
        done_when: []
        max_attempts: 2
        on_exhausted: block
        optional: true

      - name: Delta
        requires:
          - Gamma
        done_when:
          - exists: README.md
        max_attempts: 2
        on_exhausted: block

      - name: Epsilon
        requires:
          - Delta
        done_when:
          - run: exit 3
        max_attempts: 1
        on_exhausted: block
        skippable_when:
          - no_remote

      - name: Zeta
        requires:
          - Epsilon
        done_when: []
        max_attempts: 1
        on_exhausted: block
  other:
    steps:
      - name: Alpha
        done_when: []
        max_attempts: 1
"""


def one_check(kind_and_value, **step_fields):
    """A one-step pipeline carrying a single check, for the check-kind tests."""
    lines = ["version: 1", "pipelines:", "  probe:", "    steps:", "      - name: Only",
             "        done_when:", f"        - {kind_and_value}"]
    for key, value in step_fields.items():
        lines.append(f"        {key}: {value}")
    return "\n".join(lines) + "\n"


@contextlib.contextmanager
def environment(**values):
    """Set environment variables for a block and put the old ones back. `None` unsets."""
    saved = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class GateMixin:
    """A temporary git repository, a pipeline definition beside it, and the CLI over both."""

    def make_repo(self, branch=BRANCH):
        root = tempfile.mkdtemp(prefix="kit-gate-")
        self.addCleanup(shutil.rmtree, root, True)
        self.git(root, "init", "-q")
        self.git(root, "config", "user.email", "gate@example.test")
        self.git(root, "config", "user.name", "Gate Test")
        self.git(root, "config", "commit.gpgsign", "false")
        self.write(root, "README.md", "a fixture project\n")
        self.write(root, "docs/handbook.md", "# Handbook\n")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "initial")
        self.git(root, "checkout", "-qb", branch)
        return root

    def git(self, root, *args):
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, f"git {' '.join(args)}: {done.stderr}")
        return done.stdout.strip()

    def write(self, root, relative, text):
        path = os.path.join(root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def write_pipelines(self, text):
        """The definition file, in a directory of its own so it never dirties the repository."""
        directory = tempfile.mkdtemp(prefix="kit-pipelines-")
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, "pipelines.test.yml")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def project(self, text=DEMO, branch=BRANCH):
        return self.make_repo(branch), self.write_pipelines(text)

    def gate(self, root, pipelines, *argv, session=None, cwd=None):
        env = dict(os.environ)
        for name in ("KIT_PIPELINES", "AGENT_KIT_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
            env.pop(name, None)
        env["CLAUDE_PROJECT_DIR"] = root
        if pipelines:
            env["KIT_PIPELINES"] = pipelines
        if session:
            env["AGENT_KIT_SESSION_ID"] = session
        return subprocess.run([sys.executable, GATE_SCRIPT, *argv], cwd=cwd or root, env=env,
                              capture_output=True, text=True)

    # -- reading what the gate wrote -----------------------------------------------------------

    def state_file(self, root, branch=BRANCH):
        return os.path.join(root, kit_gate.RUNS_DIR, kit_gate.slug(branch) + ".yml")

    def document(self, root, branch=BRANCH):
        return kit_yaml.load_path(self.state_file(root, branch))

    def step(self, root, name, branch=BRANCH):
        entry = kit_gate.step_state(self.document(root, branch), name)
        self.assertIsNotNone(entry, f"{name} is not in the state file")
        return entry

    def assertOk(self, done, fragment=None):
        self.assertEqual(done.returncode, 0, f"stdout: {done.stdout}\nstderr: {done.stderr}")
        if fragment:
            self.assertIn(fragment, done.stdout)
        return done

    def assertRefused(self, done, fragment, code=None):
        self.assertNotEqual(done.returncode, 0, f"the gate allowed it: {done.stdout}")
        if code is not None:
            self.assertEqual(done.returncode, code, done.stderr)
        self.assertIn(fragment, done.stdout + done.stderr)
        return done


# ----------------------------------------------------------------------------------------------
# unit — the definition parser


class DefinitionTest(unittest.TestCase, GateMixin):
    """What the gate will not guess at. Every one of these is a line in the design's schema."""

    def parse(self, text):
        return kit_gate.parse_pipelines(kit_yaml.load(text), "fixture.yml")

    def assertStructural(self, text, fragment):
        with self.assertRaises(kit_gate.GateError) as caught:
            self.parse(text)
        self.assertIn(fragment, str(caught.exception))
        self.assertTrue(caught.exception.structural,
                        "a declaration the gate cannot read is structural — exit 2, not exit 1")

    def test_a_pipeline_parses_into_ordered_steps(self):
        parsed = self.parse(DEMO)
        self.assertEqual([s.name for s in parsed["demo"]], ["Design", "Build", "Extra", "PR"])
        build = parsed["demo"][1]
        self.assertEqual(build.checks, [("run", "exit 0")])
        self.assertEqual(build.requires, ["Design"])
        self.assertEqual(build.max_attempts, 2)
        self.assertEqual(parsed["demo"][3].skippable_when, ["no_remote"])
        self.assertTrue(parsed["demo"][2].optional)

    def test_the_unsupported_check_kinds_are_named_rather_than_passed(self):
        """Silently ignoring `approved_by_owner:` would close a step nobody approved."""
        self.assertStructural(one_check("approved_by_owner: the owner said yes"),
                              "declared in the schema and not supported")
        self.assertStructural(one_check("agent: judge the diff"),
                              "declared in the schema and not supported")

    def test_an_unknown_check_kind_is_refused(self):
        self.assertStructural(one_check("smells_right: yes"), "unknown check kind")

    def test_escalate_is_declared_and_refused(self):
        """`escalate` needs a push channel this version has not got; passing it would drop the run."""
        self.assertStructural(one_check("run: exit 0", on_exhausted="escalate"),
                              "declared in the schema and not supported")
        self.assertStructural(one_check("run: exit 0", on_exhausted="shrug"),
                              "`on_exhausted` is one of")

    def test_a_malformed_step_is_refused(self):
        cases = [
            ("version: 1\npipelines:\n  p:\n    steps:\n      - done_when: []\n",
             "a step needs a `name`"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n      - name: A\n",
             "two steps are called"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n        requires:\n"
             "          - Z\n", "names a step that does not come before"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n        done_when: nope\n",
             "`done_when` is a list of checks"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n        max_attempts: 0\n",
             "`max_attempts` is a positive integer"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n        optional: sure\n",
             "`optional` is true or false"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n"
             "        skippable_when: no_remote\n", "`skippable_when` is a list"),
            ("version: 1\npipelines:\n  p:\n    steps: []\n", "`steps` is a non-empty list"),
            ("version: 1\npipelines: {}\n", "no pipelines are declared"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n        done_when:\n"
             "          - git: is_lovely\n", "is not one of"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n        done_when:\n"
             "          - run:\n", "needs a non-empty value"),
            ("version: 1\npipelines:\n  p:\n    steps:\n      - name: A\n        done_when:\n"
             "          - run: exit 0\n            exists: x\n", "a check is one `kind: value` pair"),
        ]
        for text, fragment in cases:
            with self.subTest(fragment=fragment):
                self.assertStructural(text, fragment)

    def test_a_malformed_definition_exits_two_through_the_cli(self):
        """The split the whole batch uses: 1 is a finding, 2 is a file that cannot be read."""
        root = self.make_repo()
        pipes = self.write_pipelines(one_check("agent: judge the diff"))
        self.assertRefused(self.gate(root, pipes, "step", "start", "Only", "--pipeline", "probe"),
                           "not supported", code=2)
        self.assertFalse(os.path.exists(self.state_file(root)),
                         "a definition that does not parse must not open a run")

    def test_a_pipeline_nobody_declared_is_named_not_guessed(self):
        root, pipes = self.project()
        self.assertRefused(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "nope"),
                           "no pipeline named 'nope'", code=2)

    def test_the_slug_keeps_a_branch_name_to_one_file(self):
        """A branch name is a path a person chose, and it becomes a file name the kit owns."""
        self.assertEqual(kit_gate.slug("claude/step-gate"), "claude-step-gate")
        self.assertEqual(kit_gate.slug("///"), "detached")

        root = self.make_repo()
        traversing = "feature/../../etc/passwd"
        path = kit_gate.state_path(root, traversing)
        self.assertEqual(os.path.dirname(path), os.path.join(root, kit_gate.RUNS_DIR),
                         f"{traversing!r} escaped the run directory as {path}")


class ShippedDefinitionTest(unittest.TestCase, GateMixin):
    """The file the plugin actually ships, against the prose that tells the agent what to ask for."""

    def setUp(self):
        self.declared = kit_gate.load_pipelines(SHIPPED_PIPELINES)

    def test_every_shipped_step_validates(self):
        self.assertEqual(sorted(self.declared), ["fix", "ship"],
                         "`sprint` is deliberately absent — see the design's deviation")
        for name, steps in self.declared.items():
            for step in steps:
                with self.subTest(pipeline=name, step=step.name):
                    self.assertGreaterEqual(step.max_attempts, 1)
                    self.assertIn(step.on_exhausted, kit_gate.ON_EXHAUSTED)
                    self.assertTrue(step.describe())

    def test_the_step_names_are_the_ones_the_skills_document(self):
        """The definition and the skill are edited a commit apart; a drifted name fails every ask."""
        self.assertEqual([s.name for s in self.declared["ship"]],
                         ["Design", "Plan", "Build", "Test", "Review", "Security", "PR", "Docs"])
        self.assertEqual([s.name for s in self.declared["fix"]],
                         ["Change", "Test", "Review", "PR"])

        ship = self.read_skill("ship")
        for step in self.declared["ship"]:
            self.assertIn(f"- **{step.name}**", ship,
                          f"ship declares {step.name} and the skill never names it")
        fix = self.read_skill("fix")
        for step in self.declared["fix"]:
            self.assertIn(f"`{step.name}`", fix,
                          f"fix declares {step.name} and the skill never names it")

    def test_the_default_path_finds_the_shipped_file(self):
        """`KIT_PIPELINES` is the tests' seam; with it unset the gate must find its own file."""
        with environment(KIT_PIPELINES=None):
            self.assertEqual(os.path.realpath(kit_gate.pipelines_path()),
                             os.path.realpath(SHIPPED_PIPELINES))

    def test_pr_is_the_only_skippable_step(self):
        """A named skip replaced free text; the shipped file must not hand back a universal exit."""
        for name, steps in self.declared.items():
            for step in steps:
                with self.subTest(pipeline=name, step=step.name):
                    self.assertFalse(step.optional, "`optional` closes any step with any reason")
                    if step.skippable_when:
                        self.assertEqual((step.name, step.skippable_when), ("PR", ["no_remote"]))

    def read_skill(self, name):
        with open(os.path.join(PLUGIN, "skills", name, "SKILL.md"), encoding="utf-8") as handle:
            return handle.read()


# ----------------------------------------------------------------------------------------------
# integration — the three check kinds, against a real repository


class CheckTest(unittest.TestCase, GateMixin):
    """The checks run real commands against real git. A mock here would prove only the mock."""

    def settle(self, root, pipes, name="Only", pipeline="probe"):
        self.assertOk(self.gate(root, pipes, "step", "start", name, "--pipeline", pipeline))
        return self.gate(root, pipes, "step", "settle", name)

    def test_a_run_check_passes_on_exit_zero_and_fails_otherwise(self):
        root = self.make_repo()
        self.assertOk(self.settle(root, self.write_pipelines(one_check("run: exit 0"))), "verified")

        other = self.make_repo()
        failed = self.settle(other, self.write_pipelines(one_check("run: exit 9")))
        self.assertEqual(failed.returncode, 1)
        self.assertIn("exit 9", failed.stderr)

    def test_a_failing_run_check_keeps_the_tail_of_its_output(self):
        """The tail is what a resumed session acts on, so it is the end of the output, not the start."""
        root = self.make_repo()
        pipes = self.write_pipelines(one_check(
            "run: sh -c \"printf HEAD_MARKER; printf '%01500d' 0; echo TAIL_MARKER; exit 9\""))
        self.assertEqual(self.settle(root, pipes).returncode, 1)
        record = self.step(root, "Only")["history"][-1]
        self.assertEqual(record["exit"], 9)
        self.assertTrue(record["output"].endswith("TAIL_MARKER"), record["output"][-40:])
        self.assertNotIn("HEAD_MARKER", record["output"],
                         "the head of the output was kept, not the tail")
        # 1,000 characters is the design's recorded default, not whatever the constant says today:
        # a test that reads the number it is checking cannot notice the number changing.
        self.assertLessEqual(len(record["output"]), 1000)
        self.assertLessEqual(len(record["output"]), kit_gate.OUTPUT_TAIL)

    def test_a_run_check_the_never_rules_cover_is_refused_without_running(self):
        """Stage 4 hands the definition file to the project; a smuggled never-rule must not run."""
        root = self.make_repo()
        pipes = self.write_pipelines(one_check("run: touch smuggled.txt && gh pr merge 7"))
        done = self.settle(root, pipes)
        self.assertEqual(done.returncode, 1)
        self.assertIn("refused without running", done.stderr)
        self.assertIn("never merges pull requests", done.stderr)
        self.assertFalse(os.path.exists(os.path.join(root, "smuggled.txt")),
                         "the refused command ran anyway — the refusal is after the fact")
        self.assertEqual(self.step(root, "Only")["history"][-1]["exit"], 125)

    def test_a_run_check_naming_run_state_is_refused(self):
        root = self.make_repo()
        pipes = self.write_pipelines(one_check("run: echo verified > .agent-kit/runs/x.yml"))
        done = self.settle(root, pipes)
        self.assertEqual(done.returncode, 1)
        self.assertIn("refused without running", done.stderr)

    def test_exists_matches_a_glob_inside_the_project(self):
        root = self.make_repo()
        self.assertOk(self.settle(root, self.write_pipelines(one_check("exists: docs/*.md"))))

        other = self.make_repo()
        missing = self.settle(other, self.write_pipelines(one_check("exists: docs/nothing-*.md")))
        self.assertEqual(missing.returncode, 1)
        self.assertIn("no file matches", missing.stderr)

    def test_exists_refuses_a_path_that_leaves_the_project(self):
        """A definition is repository content; a glob out of the tree would answer about elsewhere."""
        for pattern in ("/etc/*", "../*.md", "docs/../../*.md"):
            with self.subTest(pattern=pattern):
                root = self.make_repo()
                pipes = self.write_pipelines(one_check(f"exists: {pattern}"))
                self.assertRefused(self.settle(root, pipes), "must be a path inside the project",
                                   code=2)

    def test_tree_clean_reads_the_working_tree(self):
        root = self.make_repo()
        pipes = self.write_pipelines(one_check("git: tree_clean"))
        self.assertOk(self.settle(root, pipes))

        other = self.make_repo()
        self.write(other, "scratch.txt", "uncommitted\n")
        dirty = self.settle(other, self.write_pipelines(one_check("git: tree_clean")))
        self.assertEqual(dirty.returncode, 1)
        self.assertIn("scratch.txt", dirty.stderr)

    def test_commits_on_branch_counts_since_the_run_opened(self):
        """A stacked branch carries its parent's commits. Counting those passes a step that made
        nothing, which is the whole reason this is not compared against the default branch."""
        root = self.make_repo(branch="claude/parent")
        self.write(root, "parent.txt", "the parent feature's work\n")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "parent work")
        self.git(root, "checkout", "-qb", BRANCH)
        pipes = self.write_pipelines(one_check("git: commits_on_branch", max_attempts=3))

        # The branch is one commit ahead of the default branch and zero commits into its own run.
        self.assertEqual(self.git(root, "rev-list", "--count", "master..HEAD")
                         if self.has_branch(root, "master")
                         else self.git(root, "rev-list", "--count", "main..HEAD"), "1")
        empty = self.settle(root, pipes)
        self.assertEqual(empty.returncode, 1, "the parent's commit was counted as this run's work")
        self.assertIn("0 commit(s) since the run opened", empty.stderr)

        self.write(root, "mine.txt", "this run's work\n")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "this run's work")
        self.assertOk(self.gate(root, pipes, "step", "settle", "Only"))
        self.assertIn("1 commit(s) since the run opened",
                      str(self.step(root, "Only")["evidence"]))

    def test_commits_on_branch_falls_back_when_the_opening_commit_is_gone(self):
        """A rebase can take the opening commit away; the gate answers about the branch, and says so,
        rather than letting git fail the step for a reason that is not the agent's doing."""
        root = self.make_repo()
        pipes = self.write_pipelines(one_check("git: commits_on_branch"))
        self.assertOk(self.gate(root, pipes, "step", "start", "Only", "--pipeline", "probe"))
        state = kit_gate.load_state(root, BRANCH)
        state["opened_at_commit"] = "0" * 40
        kit_gate.write_state(root, state)
        self.assertOk(self.gate(root, pipes, "step", "settle", "Only"))
        self.assertIn("on this branch", str(self.step(root, "Only")["evidence"]))

    def test_pushed_reads_the_upstream_in_both_directions(self):
        root = self.make_repo()
        pipes = self.write_pipelines(one_check("git: pushed", max_attempts=4))
        unpushed = self.settle(root, pipes)
        self.assertEqual(unpushed.returncode, 1)
        self.assertIn("never been pushed", unpushed.stderr)

        remote = tempfile.mkdtemp(prefix="kit-remote-")
        self.addCleanup(shutil.rmtree, remote, True)
        subprocess.run(["git", "init", "-q", "--bare", remote], check=True, capture_output=True)
        self.git(root, "remote", "add", "origin", remote)
        self.git(root, "push", "-q", "--set-upstream", "origin", BRANCH)
        self.assertOk(self.gate(root, pipes, "step", "settle", "Only"))

        ahead = self.make_repo()
        self.git(ahead, "remote", "add", "origin", remote)
        self.git(ahead, "push", "-q", "--set-upstream", "origin", f"{BRANCH}:other-branch")
        self.write(ahead, "unpushed.txt", "not on the remote\n")
        self.git(ahead, "add", "-A")
        self.git(ahead, "commit", "-qm", "local only")
        behind = self.settle(ahead, self.write_pipelines(one_check("git: pushed")))
        self.assertEqual(behind.returncode, 1)
        self.assertIn("1 commit(s) not on", behind.stderr)

    def has_branch(self, root, name):
        done = subprocess.run(["git", "rev-parse", "--verify", "--quiet", name], cwd=root,
                              capture_output=True, text=True)
        return done.returncode == 0


# ----------------------------------------------------------------------------------------------
# contract — the CLI


class StartTest(unittest.TestCase, GateMixin):
    """Order is the failure the whole feature exists for."""

    def test_the_first_start_has_to_name_a_pipeline(self):
        root, pipes = self.project()
        done = self.assertRefused(self.gate(root, pipes, "step", "start", "Design"),
                                  "which pipeline it opens")
        self.assertIn("demo", done.stderr)
        self.assertIn("other", done.stderr)
        self.assertFalse(os.path.exists(self.state_file(root)))

    def test_a_step_does_not_open_before_its_predecessor_settles(self):
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        done = self.assertRefused(self.gate(root, pipes, "step", "start", "PR"),
                                  "does not open yet", code=1)
        self.assertIn("Design", done.stderr)
        self.assertIn("Build", done.stderr)
        self.assertIsNone(kit_gate.verdict_of(self.document(root), "PR"),
                          "a refused start must not leave the step in state")

    def test_a_required_predecessor_is_named_in_the_refusal(self):
        """`requires:` states the dependency the list order also carries — a project reading this
        file in stage 4 must be able to see it, and the gate must judge both."""
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "designed"))
        self.assertOk(self.gate(root, pipes, "step", "start", "Build"))
        # PR requires Build, which is open rather than terminal, and Extra sits between them.
        done = self.assertRefused(self.gate(root, pipes, "step", "start", "PR"),
                                  "does not open yet", code=1)
        self.assertIn("Build", done.stderr)
        self.assertEqual(kit_gate.load_pipelines(pipes)["demo"][3].requires, ["Build"])

    def test_start_prints_what_will_close_the_step(self):
        root, pipes = self.project()
        opened = self.assertOk(self.gate(root, pipes, "step", "start", "Design",
                                         "--pipeline", "demo"))
        self.assertIn("closes when:", opened.stdout)
        self.assertIn("--evidence", opened.stdout)
        self.assertOk(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "designed"))
        build = self.assertOk(self.gate(root, pipes, "step", "start", "Build"))
        self.assertIn("run: exit 0", build.stdout)
        self.assertIn("attempt limit 2", build.stdout)

    def test_one_run_is_one_pipeline(self):
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertRefused(self.gate(root, pipes, "step", "start", "Design",
                                     "--pipeline", "other"), "One run, one pipeline")

    def test_a_step_no_pipeline_declares_is_named(self):
        root, pipes = self.project()
        self.assertRefused(self.gate(root, pipes, "step", "start", "Deploy", "--pipeline", "demo"),
                           "no step named 'Deploy'")

    def test_a_detached_head_has_no_run(self):
        root, pipes = self.project()
        self.git(root, "checkout", "-q", "--detach", "HEAD")
        self.assertRefused(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"),
                           "no branch is checked out")


class SettleTest(unittest.TestCase, GateMixin):
    """`settle` is the loop: it is where a verdict is written and where attempts run out."""

    def test_a_failing_check_names_itself_its_exit_code_and_its_output(self):
        root, pipes = self.project(HARD)
        self.assertOk(self.gate(root, pipes, "step", "start", "Build", "--pipeline", "hard"))
        done = self.gate(root, pipes, "step", "settle", "Build")
        self.assertEqual(done.returncode, 1)
        self.assertIn("run: echo BOOM_MARKER; exit 3", done.stderr)
        self.assertIn("exit 3", done.stderr)
        self.assertIn("BOOM_MARKER", done.stderr)
        self.assertIn("attempt 1 of 2", done.stderr)

        entry = self.step(root, "Build")
        self.assertEqual(entry["verdict"], kit_gate.OPEN)
        self.assertEqual(entry["attempts"], 1)
        self.assertEqual(len(entry["history"]), 1)
        self.assertEqual(entry["history"][0]["exit"], 3)
        self.assertEqual(entry["history"][0]["attempt"], 1)
        self.assertIn("BOOM_MARKER", entry["history"][0]["output"])

    def test_attempts_run_out_into_a_blocked_step_and_a_blocked_run(self):
        """A gate that can deadlock a run is worse than none, so exhaustion is a verdict, not a hang."""
        root, pipes = self.project(HARD)
        self.assertOk(self.gate(root, pipes, "step", "start", "Build", "--pipeline", "hard"))
        self.assertEqual(self.gate(root, pipes, "step", "settle", "Build").returncode, 1)
        second = self.gate(root, pipes, "step", "settle", "Build")
        self.assertEqual(second.returncode, 1)
        self.assertIn("blocked: attempts exhausted", second.stderr)
        self.assertIn("report this step as the blocker", second.stderr)

        entry = self.step(root, "Build")
        self.assertEqual(entry["verdict"], kit_gate.BLOCKED)
        self.assertEqual(entry["attempts"], 2)
        self.assertEqual([record["attempt"] for record in entry["history"]], [1, 2],
                         "every attempt is kept — the history is what the blocker is reported from")
        self.assertEqual(self.document(root)["state"], kit_gate.RUN_BLOCKED)
        self.assertRefused(self.gate(root, pipes, "step", "start", "After"),
                           "no further step opens")

    def test_on_exhausted_continue_leaves_the_run_open(self):
        root, pipes = self.project(HARD)
        self.assertOk(self.gate(root, pipes, "step", "start", "Build", "--pipeline", "soft"))
        for _ in range(2):
            self.assertEqual(self.gate(root, pipes, "step", "settle", "Build").returncode, 1)
        self.assertEqual(self.step(root, "Build")["verdict"], kit_gate.BLOCKED)
        self.assertEqual(self.document(root)["state"], kit_gate.RUN_OPEN,
                         "`continue` says the run carries on and reports the step in the PR")

        self.assertOk(self.gate(root, pipes, "step", "start", "After"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "After", "--evidence", "did it"))
        self.assertEqual(self.document(root)["state"], kit_gate.RUN_FINISHED)

    def test_a_check_less_step_needs_real_evidence(self):
        """`attested` is the gate being honest about what it did not prove; an empty one proves less."""
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertRefused(self.gate(root, pipes, "step", "settle", "Design"),
                           "An empty attestation is not evidence", code=1)
        self.assertRefused(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "  \t "),
                           "An empty attestation is not evidence", code=1)
        self.assertEqual(self.step(root, "Design")["verdict"], kit_gate.OPEN)
        self.assertEqual(self.step(root, "Design")["attempts"], 0,
                         "a refused settle is not an attempt")

        self.assertOk(self.gate(root, pipes, "step", "settle", "Design",
                                "--evidence", " expanded the brief "))
        entry = self.step(root, "Design")
        self.assertEqual(entry["verdict"], kit_gate.ATTESTED)
        self.assertEqual(entry["evidence"], "expanded the brief")
        self.assertTrue(entry["settled_at"])

    def test_a_passing_check_records_the_evidence_it_ran(self):
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "designed"))
        self.assertOk(self.gate(root, pipes, "step", "start", "Build"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "Build"), "verified")
        entry = self.step(root, "Build")
        self.assertEqual(entry["verdict"], kit_gate.VERIFIED)
        self.assertEqual(entry["evidence"][0]["check"], "run: exit 0")
        self.assertEqual(entry["evidence"][0]["exit"], 0)

    def test_a_step_that_was_never_opened_cannot_be_settled(self):
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertRefused(self.gate(root, pipes, "step", "settle", "Build"), "was never opened",
                           code=1)

    def test_there_is_nothing_to_settle_before_a_run_opens(self):
        root, pipes = self.project()
        self.assertRefused(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "x"),
                           "there is no run on")

    def test_a_terminal_verdict_is_never_reopened(self):
        """Every terminal verdict is final, whichever door the agent tries."""
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "designed"))
        settled = self.document(root)["steps"][0]

        for argv in (("step", "start", "Design"),
                     ("step", "settle", "Design", "--evidence", "again"),
                     ("step", "skip", "Design", "--reason", "no_remote")):
            with self.subTest(argv=argv):
                self.assertRefused(self.gate(root, pipes, *argv), "already settled", code=1)
                self.assertEqual(self.document(root)["steps"][0], settled,
                                 "the refused call rewrote the settled step")


class SkipTest(unittest.TestCase, GateMixin):
    """`skipped: <any reason>` used to close any step. A skip now names a declared condition."""

    def test_a_reason_the_definition_does_not_name_is_refused(self):
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "designed"))
        self.assertOk(self.gate(root, pipes, "step", "start", "Build"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "Build"))
        self.assertOk(self.gate(root, pipes, "step", "skip", "Extra", "--reason", "not needed"))

        self.assertRefused(self.gate(root, pipes, "step", "skip", "PR", "--reason", "ran out of time"),
                           "is skippable when no_remote", code=1)
        self.assertRefused(self.gate(root, pipes, "step", "skip", "PR"), "needs `--reason", code=1)
        self.assertIsNone(kit_gate.verdict_of(self.document(root), "PR"))

        self.assertOk(self.gate(root, pipes, "step", "skip", "PR", "--reason", "no_remote"))
        entry = self.step(root, "PR")
        self.assertEqual(entry["verdict"], kit_gate.SKIPPED)
        self.assertEqual(entry["reason"], "no_remote")
        self.assertEqual(self.document(root)["state"], kit_gate.RUN_FINISHED)

    def test_a_step_that_is_neither_optional_nor_skippable_cannot_be_skipped(self):
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertRefused(self.gate(root, pipes, "step", "skip", "Design", "--reason", "no_remote"),
                           "neither optional nor skippable under any named condition", code=1)
        self.assertEqual(self.step(root, "Design")["verdict"], kit_gate.OPEN)

    def test_a_skip_keeps_the_pipeline_in_order(self):
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertRefused(self.gate(root, pipes, "step", "skip", "PR", "--reason", "no_remote"),
                           "came first", code=1)


# ----------------------------------------------------------------------------------------------
# integration — run state on disk


class RunStateTest(unittest.TestCase, GateMixin):
    """Where the verdict lives. Everything here is a way the file could lie about whose run it is."""

    def open_run(self, root, pipes, **kwargs):
        return self.assertOk(self.gate(root, pipes, "step", "start", "Design",
                                       "--pipeline", "demo", **kwargs))

    def test_the_branch_is_recorded_inside_the_file(self):
        root, pipes = self.project()
        self.open_run(root, pipes)
        document = self.document(root)
        self.assertEqual(document["branch"], BRANCH)
        self.assertEqual(document["pipeline"], "demo")
        self.assertEqual(document["state"], kit_gate.RUN_OPEN)
        self.assertTrue(document["opened_at_commit"])

    def test_a_state_file_naming_another_branch_is_not_this_branch_s_run(self):
        """Two branch names can slug to one file. Sharing a run between them is the worst answer."""
        root, pipes = self.project()
        self.open_run(root, pipes)
        document = self.document(root)
        document["branch"] = "claude/somebody-else"
        with open(self.state_file(root), "w", encoding="utf-8") as handle:
            handle.write(kit_yaml.dump(document))

        self.assertIsNone(kit_gate.load_state(root, BRANCH))
        self.assertEqual(self.gate(root, pipes, "state").stdout, "")
        self.assertRefused(self.gate(root, pipes, "step", "start", "Design"),
                           "there is no run on")

    def test_two_branches_that_slug_alike_do_not_share_a_run(self):
        root, pipes = self.project(branch="claude/foo-bar")
        self.assertEqual(kit_gate.slug("claude/foo-bar"), kit_gate.slug("claude-foo/bar"))
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        self.assertOk(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "designed"))

        self.git(root, "checkout", "-qb", "claude-foo/bar")
        self.assertRefused(self.gate(root, pipes, "step", "start", "Build"),
                           "there is no run on claude-foo/bar")
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        document = self.document(root, "claude-foo/bar")
        self.assertEqual(document["branch"], "claude-foo/bar")
        self.assertEqual(kit_gate.verdict_of(document, "Design"), kit_gate.OPEN,
                         "the other branch's settled Design leaked into this run")

    def test_the_session_that_opened_the_run_is_recorded(self):
        """Keyed by branch alone, a sprint orchestrator reads its child's run as its own."""
        root, pipes = self.project()
        self.open_run(root, pipes, session="44608e54-ff5f")
        self.assertEqual(self.document(root)["session"], "44608e54-ff5f")

        other, other_pipes = self.project()
        self.open_run(other, other_pipes)
        self.assertIsNone(self.document(other)["session"],
                          "unset holds any session, which is a single-session repository")

    def test_state_is_replaced_atomically(self):
        """Two sessions share a working tree; a half-written file is indistinguishable from a
        corrupt one, and every hook reads a corrupt one as `there is no run`."""
        root, pipes = self.project()
        self.open_run(root, pipes)
        self.assertOk(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "designed"))
        self.assertEqual(sorted(os.listdir(os.path.join(root, kit_gate.RUNS_DIR))),
                         [".gitignore", kit_gate.slug(BRANCH) + ".yml"])

    def test_the_run_directory_ignores_itself(self):
        """Without it the PR step's `tree_clean` check could never pass in a fresh project."""
        root, pipes = self.project()
        self.assertEqual(self.git(root, "status", "--porcelain"), "")
        self.open_run(root, pipes)
        self.assertEqual(self.git(root, "status", "--porcelain"), "",
                         "the gate's own state file dirtied the tree")
        with open(os.path.join(root, kit_gate.RUNS_DIR, ".gitignore"), encoding="utf-8") as handle:
            self.assertIn("*", handle.read())

    def test_a_symlink_where_the_kit_owns_the_name_is_refused(self):
        """Git checks symlinks out: a pull request can point run state at somebody's home directory."""
        elsewhere = tempfile.mkdtemp(prefix="kit-elsewhere-")
        self.addCleanup(shutil.rmtree, elsewhere, True)

        root, pipes = self.project()
        os.makedirs(os.path.join(root, ".agent-kit"))
        os.symlink(elsewhere, os.path.join(root, kit_gate.RUNS_DIR))
        self.assertRefused(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"),
                           "is a symlink", code=2)
        self.assertEqual(os.listdir(elsewhere), [], "the gate wrote through the link")

        other, other_pipes = self.project()
        os.makedirs(os.path.join(other, kit_gate.RUNS_DIR))
        os.symlink(os.path.join(elsewhere, "stolen.yml"),
                   self.state_file(other))
        self.assertRefused(self.gate(other, other_pipes, "step", "start", "Design",
                                     "--pipeline", "demo"), "is a symlink", code=2)
        self.assertFalse(os.path.exists(os.path.join(elsewhere, "stolen.yml")))

    def test_unreadable_state_is_named_rather_than_guessed_at(self):
        root, pipes = self.project()
        self.open_run(root, pipes)
        with open(self.state_file(root), "w", encoding="utf-8") as handle:
            handle.write("steps:\n  - name: Design\n     verdict: attested\n")
        self.assertRefused(self.gate(root, pipes, "step", "settle", "Design", "--evidence", "x"),
                           "run state", code=2)

    def test_the_gate_reads_the_project_directory_the_hooks_hand_it(self):
        """`CLAUDE_PROJECT_DIR` is what a hook or a skill passes; cwd is only the fallback."""
        root, pipes = self.project()
        self.open_run(root, pipes)
        elsewhere = tempfile.mkdtemp(prefix="kit-cwd-")
        self.addCleanup(shutil.rmtree, elsewhere, True)
        done = self.assertOk(self.gate(root, pipes, "state", cwd=elsewhere))
        self.assertIn(BRANCH, done.stdout)


# ----------------------------------------------------------------------------------------------
# contract — what SessionStart is allowed to print


class SummaryTest(unittest.TestCase, GateMixin):
    """`gate.py state` is appended to `engine.md` inside a 10,000-character hook budget."""

    def test_there_is_nothing_to_say_when_there_is_no_run(self):
        root, pipes = self.project()
        self.assertEqual(self.assertOk(self.gate(root, pipes, "state")).stdout, "")

    def test_an_open_run_names_the_next_step_and_its_attempts(self):
        root, pipes = self.project(HARD)
        self.assertOk(self.gate(root, pipes, "step", "start", "Build", "--pipeline", "hard"))
        self.assertEqual(self.gate(root, pipes, "step", "settle", "Build").returncode, 1)
        printed = self.assertOk(self.gate(root, pipes, "state")).stdout
        self.assertIn(f"unfinished run on {BRANCH}", printed)
        self.assertIn("**Next: Build** — attempt 2 of 2", printed)
        self.assertIn("attempt 1:", printed)
        self.assertIn("exit 3", printed)

    def test_a_finished_or_blocked_run_says_nothing(self):
        """A blocked run releases the Stop hook, and a hook that keeps talking about it is noise."""
        for verdict in (kit_gate.RUN_FINISHED, kit_gate.RUN_BLOCKED):
            with self.subTest(state=verdict):
                root, pipes = self.project()
                self.assertOk(self.gate(root, pipes, "step", "start", "Design",
                                        "--pipeline", "demo"))
                state = kit_gate.load_state(root, BRANCH)
                state["state"] = verdict
                kit_gate.write_state(root, state)
                self.assertEqual(self.assertOk(self.gate(root, pipes, "state")).stdout, "")

    def test_a_pipeline_the_definition_no_longer_declares_says_nothing(self):
        """A run opened before the definition changed must not fail the SessionStart hook."""
        root, pipes = self.project()
        self.assertOk(self.gate(root, pipes, "step", "start", "Design", "--pipeline", "demo"))
        state = kit_gate.load_state(root, BRANCH)
        state["pipeline"] = "retired"
        kit_gate.write_state(root, state)
        self.assertEqual(self.assertOk(self.gate(root, pipes, "state")).stdout, "")

    def test_an_enormous_state_is_capped(self):
        """Past 10,000 characters Claude Code writes the hook's output to a file and shows a
        preview, so the governance would silently stop being always-on."""
        lines = ["version: 1", "pipelines:", "  big:", "    steps:"]
        for index in range(40):
            lines += [f"      - name: Step{index:02d}", "        done_when: []",
                      "        max_attempts: 3"]
        root = self.make_repo()
        pipes = self.write_pipelines("\n".join(lines) + "\n")

        state = kit_gate.new_state(root, BRANCH, "big")
        for index in range(39):
            state["steps"].append({"name": f"Step{index:02d}", "verdict": kit_gate.ATTESTED,
                                   "attempts": 1, "evidence": "e" * 500})
        state["steps"].append({
            "name": "Step39", "verdict": kit_gate.OPEN, "attempts": 2,
            "history": [{"attempt": n, "check": "run: " + "c" * 400, "exit": 1,
                         "output": "o" * 900} for n in range(1, 3)]})
        kit_gate.write_state(root, state)

        printed = self.assertOk(self.gate(root, pipes, "state")).stdout
        self.assertLessEqual(len(printed), kit_gate.STATE_CAP,
                             "the gate's share of the SessionStart budget was exceeded")
        # The design records 2,000 characters, and `validate.sh` reserves exactly that much of the
        # hook's 10,000 for the gate. A test that only reads the constant cannot see it move.
        self.assertLessEqual(len(printed), 2000)
        self.assertIn("(state truncated)", printed)


# ----------------------------------------------------------------------------------------------
# property-based — pseudo-random walks over the state machine


class WalkTest(unittest.TestCase, GateMixin):
    """Sequences of start / settle / skip no test author thought to write down.

    The invariants are the design's own promises, and they are checked after *every* call, so the
    walk reports the first transition that broke one rather than the state at the end. The commands
    are the real ones — `gate.cmd_start`, `cmd_settle`, `cmd_skip` through `gate.main` — because a
    walk over a re-implementation of the transitions would only prove the re-implementation.
    """

    ACTIONS = ("start", "settle", "skip")
    NAMES = ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Omega")
    REASONS = ("no_remote", "because", "", None)
    EVIDENCE = ("did the thing", "  ", None)
    PIPELINES = ("walk", "other", None)

    def call(self, argv):
        """One CLI invocation in-process, so 200 of them cost what one subprocess does."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gate.main(argv)
        return code, out.getvalue() + err.getvalue()

    def test_the_invariants_hold_over_random_walks(self):
        reached = set()
        for seed in SEEDS:
            with self.subTest(seed=seed):
                reached |= self.walk(seed)
        # Every verdict the gate can write, and both ways a run ends. Without this the walks could
        # quietly stop reaching past the first step and every invariant above would still hold.
        self.assertEqual(reached, {kit_gate.OPEN, kit_gate.VERIFIED, kit_gate.ATTESTED,
                                   kit_gate.SKIPPED, kit_gate.BLOCKED,
                                   "run:" + kit_gate.RUN_OPEN, "run:" + kit_gate.RUN_FINISHED,
                                   "run:" + kit_gate.RUN_BLOCKED},
                         f"the walks over seeds {SEEDS} never got that far")

    def walk(self, seed, turns=45):
        rng = random.Random(seed)
        root = self.make_repo()
        pipes = self.write_pipelines(WALK)
        declared = kit_gate.load_pipelines(pipes)["walk"]
        limits = {step.name: step.max_attempts for step in declared}
        blocking = {step.name: step.on_exhausted == "block" for step in declared}
        terminal_seen = {}
        reached = set()

        with environment(KIT_PIPELINES=pipes, CLAUDE_PROJECT_DIR=root,
                         AGENT_KIT_SESSION_ID=None, CLAUDE_CODE_SESSION_ID=None):
            document = None
            for turn in range(1, turns + 1):
                argv = self.argv(rng, document, declared)
                code, output = self.call(argv)
                where = f"seed {seed}, turn {turn}: gate {' '.join(argv)} -> {code}\n{output}"
                self.assertIn(code, (0, 1, 2), where)

                document = kit_gate.load_state(root, BRANCH)
                if document is None:
                    self.assertFalse(terminal_seen, where)
                    continue
                self.assertEqual(kit_yaml.load_path(self.state_file(root)), document,
                                 f"the state file does not reload into what was written — {where}")
                self.check_invariants(document, declared, limits, blocking, terminal_seen, where)
                reached.update(entry["verdict"] for entry in document["steps"])
                reached.add("run:" + document["state"])

        # A walk that refused everything would satisfy every invariant above and prove nothing, so
        # the walk says how far it actually got.
        return reached

    def argv(self, rng, document, declared):
        """One call. Mostly the move a working agent would make, sometimes one it should not.

        Purely random names walk into a refusal every time and the run never leaves its first step,
        so the target is usually the step the pipeline is actually on — and one turn in three is
        something out of order, out of pipeline, or missing the argument that closes the step.
        """
        left = ([step.name for step in declared
                 if document is not None and not kit_gate.is_terminal(document, step.name)]
                or [declared[0].name])
        name = left[0] if rng.random() < 0.7 else rng.choice(self.NAMES)
        entry = kit_gate.step_state(document, name) if document is not None else None
        action = (("start" if entry is None else rng.choice(("settle", "settle", "skip")))
                  if rng.random() < 0.6 else rng.choice(self.ACTIONS))
        if action == "start":
            # Which pipeline the run is is decided by the first `start` and never again, so a walk
            # that opened `other` would be a walk over a one-step pipeline. `other` is offered only
            # once there is a run to refuse it against.
            pipeline = (rng.choice(("walk", "walk", "walk", None)) if document is None
                        else rng.choice(self.PIPELINES))
            return ["step", "start", name] + (["--pipeline", pipeline] if pipeline else [])
        if action == "settle":
            evidence = "did the thing" if rng.random() < 0.7 else rng.choice(self.EVIDENCE)
            return ["step", "settle", name] + (["--evidence", evidence] if evidence else [])
        reason = "no_remote" if rng.random() < 0.5 else rng.choice(self.REASONS)
        return ["step", "skip", name] + (["--reason", reason] if reason else [])

    def check_invariants(self, document, declared, limits, blocking, terminal_seen, where):
        names = [step.name for step in declared]
        for entry in document["steps"]:
            self.assertIn(entry["name"], names, f"a step nobody declared is in state — {where}")

        for position, step in enumerate(declared):
            entry = kit_gate.step_state(document, step.name)
            if entry is None:
                continue
            verdict = entry.get("verdict")

            # A terminal verdict is terminal: the gate is the only writer, and it never takes one
            # back. This is the guarantee every other one rests on.
            if step.name in terminal_seen:
                self.assertEqual(verdict, terminal_seen[step.name],
                                 f"{step.name} left a terminal verdict — {where}")
            elif verdict in kit_gate.TERMINAL:
                terminal_seen[step.name] = verdict

            self.assertLessEqual(entry.get("attempts", 0), limits[step.name],
                                 f"{step.name} was tried past its limit — {where}")

            # Order: a step is in state only because it opened, and it opens only behind terminal
            # predecessors.
            for earlier in declared[:position]:
                self.assertIn(kit_gate.verdict_of(document, earlier.name), kit_gate.TERMINAL,
                              f"{step.name} is in state while {earlier.name} is not settled "
                              f"— {where}")

        left = kit_gate.unsettled(document, declared)
        if document["state"] == kit_gate.RUN_FINISHED:
            self.assertEqual(left, [], f"the run finished with steps open — {where}")
        if document["state"] == kit_gate.RUN_BLOCKED:
            self.assertTrue(
                any(kit_gate.verdict_of(document, name) == kit_gate.BLOCKED
                    and kit_gate.step_state(document, name)["attempts"] >= limits[name]
                    and blocking[name] for name in limits),
                f"the run is blocked with nothing to block it — {where}")
        if not left:
            self.assertIn(document["state"], (kit_gate.RUN_FINISHED, kit_gate.RUN_BLOCKED),
                          f"every step is settled and the run is still open — {where}")


if __name__ == "__main__":
    unittest.main()
