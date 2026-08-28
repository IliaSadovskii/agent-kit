"""S4 — deliver: the branch, the commit, the pull request, composed by the program.

A pull request body assembled from what was already recorded cannot describe
work that did not happen. That is why this step is not a role.

It is also where open question 6 finally has a reader: a `blocking` finding
makes delivery refuse. The vocabulary for it existed since S2; what was missing
was the step that refuses.
"""

import json
import subprocess

import pytest

from agent_kit.programs import build_program
from agent_kit.providers.base import ExecutorFailed, StepRequest
from agent_kit.steps import builtin_registry
from agent_kit.steps.contract import parse_output

DESIGN = {
    "title": "Money learns a VAT rate",
    "summary": "Money learns a VAT rate, so a price can be quoted with tax.",
    "changes": ["money.py — a with_vat method"],
    "seams": ["Money is frozen, so with_vat returns a new one"],
    "proves": [{"kind": "suite", "command": "pytest tests/test_money.py"}],
    "asks": [],
    "assumptions": [
        {"what": "the rate is a whole percent", "expensive": True, "because": "nothing in the sandbox uses fractions"}
    ],
}

BUILD = {
    "complete": True,
    "summary": "with_vat, and the test that was decided before it.",
    "files": ["money.py"],
    "tests": ["test_vat_is_added_to_the_amount"],
    "deviations": [{"what": "a free function, not a method", "because": "Money is frozen"}],
    "remaining": None,
}

VERIFY = {"commands": [{"name": "test", "command": "pytest", "exit_code": 0, "passed": True, "output": "4 passed"}],
          "passed": True}

REVIEW_PASSED = {"verdict": "pass", "findings": [{"severity": "note", "what": "the docstring could say more"}]}
REVIEW_BLOCKED = {
    "verdict": "blocked",
    "findings": [{"severity": "blocking", "what": "a negative rate is not refused", "where": "money.py:40"}],
}


def git(root, *argv, check=True):
    return subprocess.run(["git", *argv], cwd=root, check=check, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A project with a real origin and a `gh` that answers without a network."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)

    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "kit@example.com")
    git(root, "config", "user.name", "kit")
    git(root, "remote", "add", "origin", str(origin))
    (root / "money.py").write_text("amount = 1000\n")
    declare(root, '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "true"\n')
    git(root, "add", "-A")
    git(root, "commit", "-m", "first")
    git(root, "push", "-u", "origin", "main")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" >> "{tmp_path}/gh-argv"\n'
        # `pr view` answers only once a pull request has been created, exactly
        # as the real one does; otherwise deliver could never tell the two apart.
        f'if [ "$2" = "view" ]; then [ -f "{tmp_path}/gh-opened" ] || exit 1; fi\n'
        f'touch "{tmp_path}/gh-opened"\n'
        "echo https://github.com/owner/project/pull/7\n"
    )
    fake_gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{__import__('os').environ['PATH']}")
    return root


def declare(root, text):
    """What the project says, and what it says about being described.

    A project that declares a description owes `record` the step that writes
    one, so every project here that is not about knowledge says out loud that
    nobody is describing it — the state, not the missing directory.
    """
    path = root / ".agent-kit/v3/project.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if "knowledge" not in text:
        text = text.replace("[project]\n", '[project]\nknowledge = ""\n', 1) \
            if text.startswith("[project]") else '[project]\nknowledge = ""\n\n' + text
    path.write_text(text, encoding="utf-8")


def request(root, prior):
    return StepRequest(
        slug="add-vat",
        step_name="deliver",
        attempt=1,
        provider="program:deliver",
        input_text="",
        workdir=root,
        project=root,
        branch="kit/add-vat",
        brief="Money should know about VAT",
        prior=prior,
    )


def whole(prior=None):
    return {"design": DESIGN, "build": BUILD, "verify": VERIFY, "review": REVIEW_PASSED, **(prior or {})}


def deliver(root, prior=None):
    return build_program("program:deliver", root).execute(request(root, whole(prior)))


def worked_on(root):
    (root / "money.py").write_text("amount = 1200\n")


# --- what it does when everything is well -----------------------------------


def test_it_puts_the_work_on_a_branch_and_opens_a_pull_request(repo):
    worked_on(repo)

    said = json.loads(deliver(repo).raw)

    assert said["branch"] == "kit/add-vat"
    assert said["pull_request"] == "https://github.com/owner/project/pull/7"
    assert said["commit"]
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "kit/add-vat"
    assert git(repo, "status", "--porcelain").stdout.strip() == ""


def test_what_it_returns_satisfies_the_step_it_belongs_to(repo):
    worked_on(repo)

    raw = deliver(repo).raw

    assert builtin_registry().get("deliver").contract.check(parse_output(raw))["branch"] == "kit/add-vat"


def test_the_branch_reaches_the_remote(repo):
    worked_on(repo)

    deliver(repo)

    assert "kit/add-vat" in git(repo, "ls-remote", "--heads", "origin").stdout


def test_the_body_is_composed_from_what_was_recorded_not_written_afresh(repo, tmp_path):
    worked_on(repo)

    deliver(repo)

    argv = (tmp_path / "gh-argv").read_text().splitlines()
    body = (repo / ".agent-kit/v3/runs/add-vat/pull-request.md")
    assert "pr" in argv and "create" in argv
    assert "main" in argv  # opened against the branch the project declared
    assert body.is_file()

    text = body.read_text()
    assert "Money learns a VAT rate" in text  # the design's own words
    assert "the rate is a whole percent" in text  # and its expensive assumption
    assert "a free function, not a method" in text  # the departure, with its cause
    assert "the docstring could say more" in text  # the findings that did not block
    assert "4 passed" not in text or "test" in text  # what verify actually ran


def test_the_run_state_is_not_committed_with_the_feature(repo):
    worked_on(repo)

    deliver(repo)

    assert ".agent-kit/v3/runs" not in git(repo, "show", "--name-only", "--format=").stdout


# --- what it refuses ---------------------------------------------------------


def test_a_blocking_finding_refuses_delivery(repo):
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"review": REVIEW_BLOCKED})

    assert refused.value.code == "blocked-by-review"
    assert "a negative rate is not refused" in refused.value.detail
    assert refused.value.retryable is False
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"


def test_a_verify_that_did_not_pass_refuses_delivery(repo):
    worked_on(repo)
    failed = {"commands": [{"name": "test", "command": "pytest", "exit_code": 1, "passed": False, "output": "1 failed"}],
              "passed": False}

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"verify": failed})

    assert refused.value.code == "not-verified"
    assert refused.value.retryable is False


def test_a_build_that_never_finished_is_not_delivered(repo):
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"build": {**BUILD, "complete": False, "remaining": ["the negative rate"]}})

    assert refused.value.code == "build-unfinished"


def test_a_tree_with_nothing_in_it_is_not_delivered(repo):
    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo)

    assert refused.value.code == "nothing-to-deliver"


def test_it_refuses_when_the_steps_it_reads_never_ran(repo):
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        build_program("program:deliver", repo).execute(request(repo, {"design": DESIGN}))

    assert refused.value.code == "nothing-to-read"


# --- what the live run found ------------------------------------------------


def test_the_commit_subject_is_the_line_the_design_wrote_for_it(repo):
    worked_on(repo)

    deliver(repo)

    subject = git(repo, "log", "-1", "--format=%s").stdout.strip()
    assert subject == "Money learns a VAT rate"
    assert "…" not in subject


def test_a_subject_line_too_long_for_a_commit_is_cut_at_a_word(repo):
    worked_on(repo)
    long = "Money learns a VAT rate and every other tax this sandbox will ever plausibly need"

    deliver(repo, {"design": {**DESIGN, "title": long}})

    subject = git(repo, "log", "-1", "--format=%s").stdout.strip()
    assert len(subject) <= 72
    assert not subject.rstrip("…").endswith(" ")
    assert subject.startswith("Money learns a VAT rate and every")


def test_the_owner_reads_the_gist_and_what_is_wanted_of_them_before_anything_else(repo):
    """A pull request is a report to the owner: three things open, the rest folded away."""
    worked_on(repo)

    deliver(repo)

    text = (repo / ".agent-kit/v3/runs/add-vat/pull-request.md").read_text()
    open_part, _, folded = text.partition("<details>")

    assert "Что сделано" in open_part
    assert "the rate is a whole percent" in open_part  # an expensive assumption is asked about
    assert "Money is frozen" not in open_part  # the seams are detail
    assert "Money is frozen" in folded
    assert "pytest tests/test_money.py" in folded


def test_a_blocking_finding_would_be_open_and_not_folded_away(repo):
    """It cannot reach a pull request, but the body must be written as if it could."""
    from agent_kit.programs.deliver import compose_body

    text = compose_body(
        request(repo, whole()), DESIGN, BUILD, VERIFY,
        {"verdict": "blocked", "findings": [{"severity": "blocking", "what": "a negative rate is not refused"}]},
    )
    open_part, _, _ = text.partition("<details>")

    assert "a negative rate is not refused" in open_part


def test_a_program_does_not_pretend_to_be_a_model(repo):
    worked_on(repo)

    meta = deliver(repo).meta

    assert "model" not in meta
    assert meta["pull_request"].startswith("http")


# --- what the review found: the outside world is not friendly ---------------


def commit_on(repo, branch, name):
    git(repo, "checkout", "-q", "-b", branch)
    (repo / name).write_text("someone else was here\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", f"{name} by somebody else")
    tip = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "checkout", "-q", "main")
    return tip


def test_a_branch_that_already_exists_is_refused_before_anything_is_touched(repo):
    tip = commit_on(repo, "kit/add-vat", "other.py")
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo)

    assert refused.value.code == "branch-exists"
    assert refused.value.retryable is False
    assert git(repo, "rev-parse", "kit/add-vat").stdout.strip() == tip  # not overwritten
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"
    assert (repo / "other.py").exists() is False  # we never left main


def test_only_what_the_build_says_it_changed_is_committed(repo):
    worked_on(repo)
    (repo / ".env").write_text("TOKEN=hunter2\n")
    (repo / "scratch.log").write_text("noise\n")

    deliver(repo)

    committed = git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
    assert committed == ["money.py"]
    assert (repo / ".env").read_text() == "TOKEN=hunter2\n"  # left where it was


def test_a_build_that_names_a_file_it_never_wrote_is_refused(repo):
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"build": {**BUILD, "files": ["money.py", "nowhere/at/all.py"]}})

    assert refused.value.code == "no-such-file"
    assert "nowhere/at/all.py" in refused.value.detail
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"


def test_a_delivery_that_died_after_its_commit_is_carried_on_not_started_again(repo, tmp_path, monkeypatch):
    """gh was not authenticated. The work is committed and pushed; running it again finishes."""
    worked_on(repo)
    broken = tmp_path / "bin/gh"
    broken.write_text("#!/bin/sh\necho 'gh: not logged in' >&2\nexit 4\n")
    broken.chmod(0o755)

    with pytest.raises(ExecutorFailed) as first:
        deliver(repo)
    assert first.value.code == "gh-failed"

    broken.write_text("#!/bin/sh\necho https://github.com/owner/project/pull/9\n")
    broken.chmod(0o755)
    said = json.loads(deliver(repo).raw)

    assert said["pull_request"].endswith("/9")
    assert git(repo, "log", "--oneline", "main..kit/add-vat").stdout.strip().count("\n") == 0  # one commit, not two


def test_a_pull_request_that_is_already_open_is_not_opened_twice(repo, tmp_path):
    worked_on(repo)
    deliver(repo)
    first = json.loads(deliver.__globals__["build_program"]("program:deliver", repo)
                       .execute(request(repo, whole())).raw)

    assert first["pull_request"].startswith("http")


def test_a_command_that_hangs_takes_its_children_with_it(repo, tmp_path):
    """A tool that outlives the session it belongs to keeps editing and keeps spending."""
    from agent_kit.programs.deliver import Deliver

    mark = tmp_path / "still-alive"
    slow = tmp_path / "bin/git"
    slow.write_text(
        "#!/bin/sh\n"
        f'(while true; do echo x >> "{mark}"; sleep 0.2; done) &\n'
        "sleep 30\n"
    )
    slow.chmod(0o755)

    with pytest.raises(ExecutorFailed) as stopped:
        Deliver(repo, timeout=2).execute(request(repo, whole()))
    assert "said nothing" in stopped.value.detail

    grew = mark.stat().st_size if mark.exists() else 0
    __import__("time").sleep(1.5)
    assert (mark.stat().st_size if mark.exists() else 0) == grew


# --- the verdict, which nothing read ----------------------------------------


def test_a_blocked_verdict_refuses_even_when_no_finding_says_blocking(repo):
    worked_on(repo)
    said_no = {"verdict": "blocked", "findings": [{"severity": "note", "what": "something is off"}]}

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"review": said_no})

    assert refused.value.code == "blocked-by-review"
    assert refused.value.expected is True


def test_a_blocking_finding_under_a_passing_verdict_is_refused_as_a_disagreement(repo):
    worked_on(repo)
    disagreed = {"verdict": "pass", "findings": [{"severity": "blocking", "what": "a negative rate is not refused"}]}

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"review": disagreed})

    assert refused.value.code == "review-disagrees-with-itself"


def test_a_refusal_of_the_method_is_not_a_breakage_of_the_kit(repo):
    """A blocked review, a red suite and an unfinished build are outcomes, not faults."""
    worked_on(repo)

    for prior, code in (
        ({"review": REVIEW_BLOCKED}, "blocked-by-review"),
        ({"build": {**BUILD, "complete": False, "remaining": ["the rest"]}}, "build-unfinished"),
    ):
        with pytest.raises(ExecutorFailed) as refused:
            deliver(repo, prior)
        assert refused.value.code == code
        assert refused.value.expected is True
        assert refused.value.retryable is False


def test_a_question_only_the_owner_can_answer_is_not_folded_away(repo):
    from agent_kit.programs.deliver import compose_body

    asked = {
        **DESIGN,
        "asks": [
            {
                "question": "Should VAT be added on top, or extracted from a gross amount?",
                "default": "added on top",
                "because": "every price in this project is net today",
            }
        ],
    }

    text = compose_body(request(repo, whole()), asked, BUILD, VERIFY, REVIEW_PASSED)
    open_part, _, _ = text.partition("<details>")

    assert "extracted from a gross amount" in open_part


def test_a_design_that_wants_nothing_from_the_owner_says_so_and_asks_nothing(repo):
    from agent_kit.programs.deliver import compose_body

    plain = {**DESIGN, "assumptions": [], "asks": None}

    open_part, _, _ = compose_body(
        request(repo, whole()), plain, BUILD, VERIFY, {"verdict": "pass", "findings": []}
    ).partition("<details>")

    assert "Ничего" in open_part


def test_a_branch_the_session_made_and_left_empty_is_ours_to_use(repo):
    """The composed input names the branch, and a session will helpfully create it."""
    git(repo, "checkout", "-q", "-b", "kit/add-vat")  # no commit on it: it holds no work
    worked_on(repo)

    said = json.loads(deliver(repo).raw)

    assert said["branch"] == "kit/add-vat"
    assert git(repo, "log", "--oneline", "main..kit/add-vat").stdout.strip().count("\n") == 0


def test_a_branch_that_holds_somebody_else_s_commit_is_still_refused(repo):
    commit_on(repo, "kit/other", "other.py")
    git(repo, "branch", "-m", "kit/other", "kit/add-vat")
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo)

    assert refused.value.code == "branch-exists"


# --- S6: the knowledge rides in the same commit as the code -----------------
#
# A block written into the owner's knowledge and left out of the commit is a
# block nobody but this machine ever sees. `record` says which files it changed
# and delivery commits them beside the ones the build named — still only what
# was named, and now the program named half of it.

ENTITIES = "# Сущности\n\n### Деньги\n`key: money`\n\n**Что это:** сумма в копейках\n"

RECORD = {
    "blocks": [{"id": "k7f3q2", "at": "entities.md#money", "what": "the rate is a whole percent"}],
    "closed": [],
    "files": ["docs/knowledge/entities.md"],
}


def with_knowledge(root):
    # The declaration is what says a project keeps knowledge, so a project that
    # keeps one takes back the `knowledge = ""` the fixture writes for the rest.
    declare(root, '[project]\ndefault_branch = "main"\nknowledge = "docs/knowledge"\n'
                  '\n[commands]\ntest = "true"\n')
    (root / "docs/knowledge").mkdir(parents=True, exist_ok=True)
    (root / "docs/knowledge/entities.md").write_text(ENTITIES, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-m", "the knowledge as it stood")
    git(root, "push", "origin", "main")
    return root


def wrote_a_block(root):
    path = root / "docs/knowledge/entities.md"
    path.write_text(path.read_text() + "\n> **[assumed 2026-08-22 · kit/add-vat · id: k7f3q2]** так\n")


def test_the_knowledge_a_run_wrote_is_committed_beside_the_code(repo):
    with_knowledge(repo)
    worked_on(repo)
    wrote_a_block(repo)

    deliver(repo, {"record": RECORD})

    changed = git(repo, "show", "--name-only", "--format=").stdout
    assert "money.py" in changed
    assert "docs/knowledge/entities.md" in changed
    assert git(repo, "status", "--porcelain").stdout.strip() == ""


def test_a_block_that_never_reached_this_working_copy_is_not_delivered_as_though_it_had(repo):
    """The knowledge the program says it wrote, staged and not there.

    It is what made S8's defect silent: `record` wrote into the project's own
    checkout while the commit was made in the run's tree, `git add` staged
    nothing, and the code file beside it made the commit look complete.
    """
    with_knowledge(repo)
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"record": RECORD})

    assert refused.value.code == "knowledge-not-in-the-commit"
    assert "docs/knowledge/entities.md" in refused.value.detail
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"


def test_a_project_that_keeps_knowledge_cannot_close_a_feature_with_a_naked_assumption(repo):
    with_knowledge(repo)
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"record": {"blocks": [], "closed": [], "files": []}})

    assert refused.value.code == "assumption-with-no-block"
    assert "the rate is a whole percent" in refused.value.detail
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"


def test_a_project_that_keeps_knowledge_cannot_close_a_feature_that_skipped_the_step(repo):
    with_knowledge(repo)
    worked_on(repo)

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo)

    assert refused.value.code == "nothing-to-read"
    assert "record" in refused.value.detail


def test_a_project_that_keeps_no_knowledge_delivers_without_the_step(repo):
    worked_on(repo)

    assert json.loads(deliver(repo).raw)["commit"]


def test_what_was_written_into_the_knowledge_is_in_the_report(repo):
    with_knowledge(repo)
    worked_on(repo)
    wrote_a_block(repo)

    deliver(repo, {"record": RECORD})

    body = (repo / ".agent-kit/v3/runs/add-vat/pull-request.md").read_text()
    assert "entities.md#money" in body
    assert "k7f3q2" in body


def test_two_assumptions_worded_the_same_owe_two_blocks_not_one(repo):
    """The join counted distinct wordings, so one block answered for two.

    A set of `what` cannot see that the second block is missing, and the whole
    point of the join is that it can.
    """
    with_knowledge(repo)
    worked_on(repo)
    wrote_a_block(repo)
    twice = dict(DESIGN, assumptions=[DESIGN["assumptions"][0], dict(DESIGN["assumptions"][0])])

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"design": twice, "record": RECORD})

    assert refused.value.code == "assumption-with-no-block"


# --- what was verified, and what is being delivered -------------------------
#
# `verify` records the commit its commands stood on and every change the tree
# held that the commit did not. Delivery refuses a commit carrying what those
# commands never ran over, and a tree that has moved since. The other direction
# — measured, and not in the commit — is a line in the pull request instead: a
# build that changed six files and named four leaves a branch missing two of
# them, and nothing anywhere used to say so.


def verified(root):
    """The verify output a real run leaves behind: measured over this tree."""
    from agent_kit.programs.proved import stood_on

    head, held = stood_on(root)
    return {**VERIFY, "proved_at": head, "proved_over": held}


def tracked(root, name, text):
    (root / name).write_text(text)
    git(root, "add", "-A")
    git(root, "commit", "-m", f"{name}, as it stood")


def test_a_commit_that_is_what_the_commands_ran_over_is_delivered(repo):
    worked_on(repo)

    said = json.loads(deliver(repo, {"verify": verified(repo)}).raw)

    assert said["commit"]


def test_a_change_the_commands_ran_over_and_the_build_did_not_name_is_in_the_report(repo):
    """The six files the build changed and the four it named, where the owner reads.

    Not a refusal: a working copy holds what the feature is not about — an
    `init --force` nobody committed, a suite the owner repaired before carrying
    the run on — and a night is worth more than the sentence one would save.
    """
    tracked(repo, "check.sh", "#!/bin/sh\nexit 0\n")
    worked_on(repo)
    (repo / "check.sh").write_text("#!/bin/sh\nexit 1\n")

    said = json.loads(deliver(repo, {"verify": verified(repo)}).raw)

    body = (repo / ".agent-kit/v3/runs/add-vat/pull-request.md").read_text()
    assert said["commit"]
    assert "check.sh" in body.split("<details>")[0]  # open, not folded away
    assert "check.sh" not in git(repo, "show", "--name-only", "--format=").stdout


def test_a_working_copy_dirty_with_what_the_feature_is_not_about_still_delivers(repo):
    """`agent-kit init --force` rewrites a tracked file and commits nothing."""
    declare(repo, '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "true"\nlint = "true"\n')
    worked_on(repo)

    said = json.loads(deliver(repo, {"verify": verified(repo)}).raw)

    assert said["commit"]


def test_a_file_the_commands_never_ran_over_is_not_delivered_as_verified(repo):
    worked_on(repo)
    measured = verified(repo)
    (repo / "late.py").write_text("late = True\n")  # written after the commands ran

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"verify": measured, "build": {**BUILD, "files": ["money.py", "late.py"]}})

    assert refused.value.code == "not-what-was-verified"
    assert "late.py" in refused.value.detail
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"


def test_a_file_edited_after_the_commands_ran_is_not_delivered_as_verified(repo):
    worked_on(repo)
    measured = verified(repo)
    (repo / "money.py").write_text("amount = 1300\n")  # the same file, another content

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"verify": measured})

    assert refused.value.code == "not-what-was-verified"
    assert "money.py" in refused.value.detail


def test_a_tree_that_moved_since_the_commands_ran_is_not_delivered(repo):
    worked_on(repo)
    measured = verified(repo)
    tracked(repo, "elsewhere.py", "elsewhere = True\n")  # a commit landed underneath

    with pytest.raises(ExecutorFailed) as refused:
        deliver(repo, {"verify": measured})

    assert refused.value.code == "tree-moved-since-verify"
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"


def test_the_knowledge_written_after_the_commands_ran_is_not_a_change_they_never_saw(repo):
    """The one move the tree makes between the two steps, and the program names it."""
    with_knowledge(repo)
    worked_on(repo)
    measured = verified(repo)
    wrote_a_block(repo)

    said = json.loads(deliver(repo, {"verify": measured, "record": RECORD}).raw)

    assert said["commit"]
    assert "docs/knowledge/entities.md" in git(repo, "show", "--name-only", "--format=").stdout


def test_a_stray_file_beside_the_work_is_not_a_change_left_out_of_the_commit(repo):
    """Untracked is not measured work: it is a .env, a log, a half-written experiment."""
    worked_on(repo)
    (repo / ".env").write_text("TOKEN=hunter2\n")

    said = json.loads(deliver(repo, {"verify": verified(repo)}).raw)

    assert said["commit"]
    assert (repo / ".env").read_text() == "TOKEN=hunter2\n"


def test_a_verify_that_said_nothing_about_where_it_stood_is_delivered_as_before(repo):
    """A run from an older kit, or one whose steps hold no verify at all."""
    worked_on(repo)

    said = json.loads(deliver(repo).raw)

    assert said["commit"]


# --- открытая половина не бесконечна ----------------------------------------
#
# Отчёт — единственный выход ночи, а непрочитанный отчёт это несмёрженная
# ветка. Вторая версия намеряла 4000 знаков на всю открытую половину; здесь то
# же число делится между её разделами, и режется, а не отказывается: работа
# ночи не выбрасывается из-за длины своего описания.

def an_essay(words: str = "слово", times: int = 4000) -> str:
    return " ".join([words] * times)


def test_a_summary_longer_than_the_ceiling_is_cut_and_the_whole_of_it_is_folded(repo):
    from agent_kit.programs.deliver import OPEN, compose_body

    essay = an_essay()
    text = compose_body(request(repo, whole()), DESIGN, {**BUILD, "summary": essay}, VERIFY, REVIEW_PASSED)
    open_part, _, folded = text.partition("<details>")

    assert len(open_part) < OPEN * 5  # открытая половина ограничена, а не «как получится»
    assert essay[:200] in open_part  # начало читается там же, где читалось всегда
    assert essay in folded  # и ни одного знака не потеряно
    assert essay not in open_part


def test_an_essay_in_one_section_does_not_push_the_others_out(repo):
    """Потолок у каждого раздела свой: иначе проза съедает то, ради чего отчёт открыт."""
    from agent_kit.programs.deliver import compose_body

    asked = {
        **DESIGN,
        "asks": [{"question": "Ставка одна на всё или своя на страну?", "default": "одна на всё"}],
    }
    blocked = {"verdict": "blocked", "findings": [{"severity": "blocking", "what": "отрицательная ставка"}]}

    text = compose_body(request(repo, whole()), asked, {**BUILD, "summary": an_essay()}, VERIFY, blocked)
    open_part, _, _ = text.partition("<details>")

    assert "отрицательная ставка" in open_part
    assert "Ставка одна на всё" in open_part
    assert "одна на всё" in open_part


def test_a_list_longer_than_the_ceiling_is_folded_the_same_way(repo):
    from agent_kit.programs.deliver import compose_body

    many = {
        **DESIGN,
        "assumptions": [
            {"what": f"допущение номер {number}", "expensive": True, "because": an_essay(times=20)}
            for number in range(40)
        ],
    }

    text = compose_body(request(repo, whole()), many, BUILD, VERIFY, REVIEW_PASSED)
    open_part, _, folded = text.partition("<details>")

    assert "допущение номер 0" in open_part
    assert "допущение номер 39" not in open_part
    assert "допущение номер 39" in folded


def test_a_report_that_fits_is_left_exactly_as_it_was(repo):
    """Потолок, который режет короткий отчёт, — это потолок, который врёт про длину."""
    from agent_kit.programs.deliver import compose_body

    text = compose_body(request(repo, whole()), DESIGN, BUILD, VERIFY, REVIEW_PASSED)
    open_part, _, _ = text.partition("<details>")

    assert "…" not in open_part
    assert "не поместилось" not in text
    assert BUILD["summary"] in open_part
