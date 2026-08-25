"""S8 — a run that has a tree works in it, and everything downstream agrees.

The tree is where the code is; the project is where the paperwork is. Getting
that wrong in either direction is the collision S8 exists to delete: a session
editing the project while another run holds it, or a record written onto a
branch nobody reviews.
"""

import json
import subprocess

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.driver.compose import compose_input
from agent_kit.driver.tree import make_tree
from agent_kit.programs import build_program
from agent_kit.providers.base import StepRequest
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStore
from agent_kit.steps import builtin_registry

PROBE = '```json\n{"branch": "kit/rates", "can_write": true, "notes": ["nothing odd"]}\n```'


def git(root, *argv):
    return subprocess.run(["git", *argv], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "kit@example.com")
    git(root, "config", "user.name", "kit")
    (root / "money.py").write_text("amount = 1000\n")
    declared = root / ".agent-kit/v3/project.toml"
    declared.parent.mkdir(parents=True, exist_ok=True)
    declared.write_text(
        '[project]\ndefault_branch = "main"\ncommand_timeout = 20\n\n'
        '[commands]\ntest = "sh -c \'pwd > where-the-suite-ran\'"\n',
        encoding="utf-8",
    )
    git(root, "add", "-A")
    git(root, "commit", "-m", "first")
    return root


def test_a_session_works_in_the_tree_and_not_in_the_project(repo, tmp_path):
    tree = make_tree(repo, "rates", branch="kit/rates", base="main")
    store = RunStore(repo)
    create_run(
        store, builtin_registry(), "rates", steps=["probe"], project=str(repo),
        tree=str(tree), base="main",
    )
    acted = tmp_path / "acted.sh"
    acted.write_text("#!/bin/sh\npwd > where-the-session-ran\n")
    fake = FakeExecutor(name="fake", replies=[(PROBE, acted)])
    StepRunner(
        store=store, registry=builtin_registry(), executors={"fake": fake}, default_provider="fake",
    ).run_next("rates")

    assert (tree / "where-the-session-ran").read_text().strip() == str(tree)
    assert not (repo / "where-the-session-ran").exists()


def test_the_paperwork_stays_in_the_project(repo, tmp_path):
    tree = make_tree(repo, "rates", branch="kit/rates", base="main")
    store = RunStore(repo)
    create_run(
        store, builtin_registry(), "rates", steps=["probe"], project=str(repo), tree=str(tree),
    )
    fake = FakeExecutor(name="fake", replies=[PROBE])
    StepRunner(
        store=store, registry=builtin_registry(), executors={"fake": fake}, default_provider="fake",
    ).run_next("rates")

    assert (repo / ".agent-kit/v3/runs/rates/run.json").is_file()
    assert not (tree / ".agent-kit/v3/runs").exists()


def test_the_project_s_commands_run_in_the_tree(repo):
    tree = make_tree(repo, "rates", branch="kit/rates", base="main")
    request = StepRequest(
        slug="rates", step_name="verify", attempt=1, provider="program:verify",
        input_text="", workdir=tree, project=repo, tree=tree, branch="kit/rates", prior={},
    )

    build_program("program:verify", repo).execute(request)

    assert (tree / "where-the-suite-ran").read_text().strip() == str(tree)
    assert not (repo / "where-the-suite-ran").exists()


def test_the_input_names_the_working_copy_the_session_is_in(repo):
    store = RunStore(repo)
    run = create_run(
        store, builtin_registry(), "quote", steps=["probe"], project=str(repo),
        tree="/somewhere/trees/quote", base="kit/rates", needs=["rates"],
    )

    text = compose_input(
        run=run, definition=builtin_registry().get("probe"), attempt=1, provider="fake",
    )

    assert "/somewhere/trees/quote" in text
    assert "kit/rates" in text


def test_what_this_run_needs_is_enclosed_rather_than_gone_looking_for(repo, tmp_path):
    store = RunStore(repo)
    create_run(store, builtin_registry(), "rates", steps=["probe"], project=str(repo))
    done = repo / ".agent-kit/v3/runs/rates/steps/0-probe"
    done.mkdir(parents=True)
    (done / "output.json").write_text(json.dumps({"notes": ["a table of rates, one row per country"]}))

    create_run(
        store, builtin_registry(), "quote", steps=["probe"], project=str(repo), needs=["rates"],
    )
    fake = FakeExecutor(name="fake", replies=['```json\n{"branch": "kit/quote", "can_write": true, "notes": []}\n```'])
    StepRunner(
        store=store, registry=builtin_registry(), executors={"fake": fake}, default_provider="fake",
    ).run_next("quote")

    written = (repo / ".agent-kit/v3/runs/quote/steps/0-probe/attempt-1/input.md").read_text()

    assert "rates" in written
    assert "a table of rates, one row per country" in written
