"""A run that has no tree builds in the project itself, and only one may.

The batch driver gives every child a worktree. `run new` never did, so two runs
started by hand on one project both edited the owner's checkout: the first to
reach `deliver` committed the other's half-written files, and the second was
refused `nothing-to-deliver` for a change that had already been swallowed.

A working copy has one writer. A run with a worktree of its own holds that; a
run without one holds the project's checkout, and the second is refused by name.
"""

import subprocess

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.driver.tree import make_tree
from agent_kit.errors import StateError
from agent_kit.machine import Ledger
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStore, StepStatus
from agent_kit.steps import builtin_registry

PROBE = '```json\n{"branch": "kit/add-vat", "can_write": true, "notes": []}\n```'


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
    git(root, "add", "-A")
    git(root, "commit", "-m", "first")
    return root


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "daemon.sqlite")


def runner(store, ledger):
    return StepRunner(
        store=store, registry=builtin_registry(),
        executors={"fake": FakeExecutor(name="fake", replies=[PROBE])},
        default_provider="fake", ledger=ledger,
    )


def a_run(store, slug, repo, tree=None):
    return create_run(
        store, builtin_registry(), slug, steps=["probe"], project=str(repo),
        **({"tree": str(tree)} if tree else {}),
    )


# --- the refusal ------------------------------------------------------------


def test_a_second_lone_run_is_refused_by_name(repo, ledger):
    store = RunStore(repo)
    a_run(store, "quote", repo)
    a_run(store, "add-vat", repo)
    ledger.hold_checkout(str(repo), "quote", pid=1)

    with pytest.raises(StateError) as refused:
        runner(store, ledger).run_next("add-vat")

    assert refused.value.code == "checkout-held-elsewhere"
    assert "quote" in refused.value.detail


def test_the_refused_run_has_not_been_started(repo, ledger):
    store = RunStore(repo)
    a_run(store, "quote", repo)
    a_run(store, "add-vat", repo)
    ledger.hold_checkout(str(repo), "quote", pid=1)

    with pytest.raises(StateError):
        runner(store, ledger).run_next("add-vat")

    run = store.load("add-vat")
    assert run.steps[0].status is StepStatus.PENDING
    assert not (store.run_root("add-vat") / "steps").exists()


def test_a_run_with_its_own_tree_does_not_want_the_project(repo, ledger):
    """The batch's children never touch the checkout, so they never queue for it."""
    store = RunStore(repo)
    ledger.hold_checkout(str(repo), "quote", pid=1)
    tree = make_tree(repo, "add-vat", branch="kit/add-vat", base="main")
    a_run(store, "add-vat", repo, tree=tree)

    outcome = runner(store, ledger).run_next("add-vat")

    assert outcome.passed


def test_the_checkout_is_given_back_when_the_run_ends(repo, ledger):
    store = RunStore(repo)
    a_run(store, "add-vat", repo)
    runner(store, ledger).run_next("add-vat")

    assert store.load("add-vat").finished
    assert ledger.checkouts() == []


def test_another_project_s_lone_run_is_no_business_of_this_one(repo, ledger, tmp_path):
    store = RunStore(repo)
    a_run(store, "add-vat", repo)
    ledger.hold_checkout(str(tmp_path / "elsewhere"), "quote", pid=1)

    assert runner(store, ledger).run_next("add-vat").passed
