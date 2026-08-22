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
    "summary": "Money learns a VAT rate, so a price can be quoted with tax.",
    "changes": ["src/kit_sandbox/money.py — a with_vat method"],
    "seams": ["Money is frozen, so with_vat returns a new one"],
    "verification": ["a test that 1000 at 20% is 1200"],
    "assumptions": [
        {"what": "the rate is a whole percent", "expensive": True, "because": "nothing in the sandbox uses fractions"}
    ],
}

BUILD = {
    "complete": True,
    "summary": "with_vat, and the test that was decided before it.",
    "files": ["src/kit_sandbox/money.py"],
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
        f'printf "%s\\n" "$@" > "{tmp_path}/gh-argv"\n'
        'cat "${5:-/dev/null}" >/dev/null 2>&1\n'
        "echo https://github.com/owner/project/pull/7\n"
    )
    fake_gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{__import__('os').environ['PATH']}")
    return root


def declare(root, text):
    path = root / ".agent-kit/v3/project.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
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
