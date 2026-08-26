"""The pre-push hook the plan promised and the code did not hold.

The plan says a git `pre-push` hook replaces three of the second version's
refusals: no `gh pr merge`, no force push, no push to the default branch. Two of
the three are pushes, so a hook can hold them; the third is not a push at all,
and what holds it is a sentence in the method that reaches every role.

These cases drive real `git push` against a real remote. Asserting the file's
contents would say the hook was written, not that it refuses anything.
"""

import subprocess

import pytest

from agent_kit.hook import LEFT_ALONE, WRITTEN, hooks_dir, write_pre_push


def git(root, *argv, check=True):
    return subprocess.run(["git", *argv], cwd=root, check=check, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    """A project with a remote, laid out the way `driver/tree.py` lays one out."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))

    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "kit@example.com")
    git(root, "config", "user.name", "kit")
    (root / "money.py").write_text("amount = 1000\n")
    git(root, "add", "-A")
    git(root, "commit", "-m", "first")
    git(root, "remote", "add", "origin", str(origin))
    git(root, "push", "-u", "origin", "main")
    return root


def commit(root, text, message):
    (root / "money.py").write_text(text)
    git(root, "add", "-A")
    git(root, "commit", "-m", message)
    return git(root, "rev-parse", "HEAD").stdout.strip()


def worktree_of(repo, slug="add-vat"):
    where = repo / ".agent-kit/v3/trees" / slug
    git(repo, "worktree", "add", "-b", f"kit/{slug}", str(where), "main")
    return where


# --- where it goes ----------------------------------------------------------


def test_it_is_written_where_git_looks_for_hooks(repo):
    hook = write_pre_push(repo, trunk="main")

    assert hook.what == WRITTEN
    assert hook.path == hooks_dir(repo) / "pre-push"
    assert hook.path.stat().st_mode & 0o111


def test_a_worktree_shares_the_one_hook(repo):
    write_pre_push(repo, trunk="main")
    tree = worktree_of(repo)

    assert hooks_dir(tree) == hooks_dir(repo)


def test_a_directory_that_is_not_a_repository_gets_nothing(tmp_path):
    hook = write_pre_push(tmp_path, trunk="main")

    assert hook.path is None
    assert hook.what != WRITTEN


# --- what it refuses --------------------------------------------------------


def test_it_refuses_a_push_to_the_trunk(repo):
    write_pre_push(repo, trunk="main")
    before = git(repo, "rev-parse", "origin/main").stdout.strip()
    commit(repo, "amount = 2000\n", "second")

    pushed = git(repo, "push", "origin", "HEAD:main", check=False)

    assert pushed.returncode != 0
    assert "agent-kit" in pushed.stderr
    assert git(repo, "rev-parse", "origin/main").stdout.strip() == before


def test_it_refuses_a_push_that_would_lose_commits(repo):
    write_pre_push(repo, trunk="main")
    git(repo, "checkout", "-b", "side")
    theirs = commit(repo, "amount = 2000\n", "theirs")
    git(repo, "push", "origin", "side")
    git(repo, "reset", "--hard", "HEAD~1")
    commit(repo, "amount = 3000\n", "mine")

    pushed = git(repo, "push", "--force", "origin", "side", check=False)

    assert pushed.returncode != 0
    assert git(repo, "rev-parse", "origin/side").stdout.strip() == theirs


def test_it_lets_an_ordinary_branch_through(repo):
    write_pre_push(repo, trunk="main")
    git(repo, "checkout", "-b", "kit/add-vat")
    made = commit(repo, "amount = 2000\n", "the work")

    pushed = git(repo, "push", "--set-upstream", "origin", "kit/add-vat", check=False)

    assert pushed.returncode == 0, pushed.stderr
    assert git(repo, "rev-parse", "origin/kit/add-vat").stdout.strip() == made


def test_it_lets_a_branch_it_already_pushed_go_on(repo):
    write_pre_push(repo, trunk="main")
    git(repo, "checkout", "-b", "kit/add-vat")
    commit(repo, "amount = 2000\n", "the work")
    git(repo, "push", "--set-upstream", "origin", "kit/add-vat")
    again = commit(repo, "amount = 3000\n", "more of it")

    pushed = git(repo, "push", "origin", "kit/add-vat", check=False)

    assert pushed.returncode == 0, pushed.stderr
    assert git(repo, "rev-parse", "origin/kit/add-vat").stdout.strip() == again


def test_the_trunk_is_the_one_the_project_declared(repo):
    """A project whose trunk is not `main` is held on the branch it named."""
    write_pre_push(repo, trunk="trunk")
    git(repo, "checkout", "-b", "trunk")
    commit(repo, "amount = 2000\n", "on the trunk")

    pushed = git(repo, "push", "origin", "HEAD:trunk", check=False)

    assert pushed.returncode != 0
    assert "agent-kit" in pushed.stderr


# --- and it reaches the tree a run builds in --------------------------------


def test_a_run_in_its_own_tree_is_refused_the_trunk(repo):
    write_pre_push(repo, trunk="main")
    tree = worktree_of(repo)
    commit(tree, "amount = 2000\n", "the feature")

    pushed = git(tree, "push", "origin", "HEAD:main", check=False)

    assert pushed.returncode != 0
    assert "agent-kit" in pushed.stderr


def test_a_run_in_its_own_tree_may_push_its_own_branch(repo):
    write_pre_push(repo, trunk="main")
    tree = worktree_of(repo)
    made = commit(tree, "amount = 2000\n", "the feature")

    pushed = git(tree, "push", "--set-upstream", "origin", "kit/add-vat", check=False)

    assert pushed.returncode == 0, pushed.stderr
    assert git(repo, "rev-parse", "origin/kit/add-vat").stdout.strip() == made


# --- somebody else's hook ---------------------------------------------------


def test_a_hook_the_project_already_had_is_left_alone(repo):
    theirs = hooks_dir(repo) / "pre-push"
    theirs.write_text("#!/bin/sh\nexit 0\n")

    hook = write_pre_push(repo, trunk="main")

    assert hook.what == LEFT_ALONE
    assert theirs.read_text() == "#!/bin/sh\nexit 0\n"


def test_its_own_hook_is_written_again_when_the_trunk_changes(repo):
    write_pre_push(repo, trunk="main")

    hook = write_pre_push(repo, trunk="trunk")

    assert hook.what == WRITTEN
    git(repo, "checkout", "-b", "trunk")
    commit(repo, "amount = 2000\n", "on the trunk")
    assert git(repo, "push", "origin", "HEAD:trunk", check=False).returncode != 0


# --- and every run gets it, whoever made the checkout -----------------------


def test_a_run_writes_the_hook_into_a_project_that_never_had_one(repo):
    """`.git/hooks` is not repository content: a fresh clone brings no hook."""
    from agent_kit.driver import StepRunner, create_run
    from agent_kit.providers.fake import FakeExecutor
    from agent_kit.state import RunStore
    from agent_kit.steps import builtin_registry

    store = RunStore(repo)
    create_run(store, builtin_registry(), "add-vat", steps=["probe"], project=str(repo))
    reply = '```json\n{"branch": "kit/add-vat", "can_write": true, "notes": []}\n```'
    StepRunner(
        store=store, registry=builtin_registry(),
        executors={"fake": FakeExecutor(name="fake", replies=[reply])},
        default_provider="fake",
    ).run_next("add-vat")

    assert (hooks_dir(repo) / "pre-push").is_file()


def test_a_declaration_the_kit_cannot_read_does_not_stop_the_run(repo):
    """The step that needs the file refuses it and names the field. Not this."""
    from agent_kit.driver import StepRunner, create_run
    from agent_kit.providers.fake import FakeExecutor
    from agent_kit.state import RunStore
    from agent_kit.steps import builtin_registry

    declared = repo / ".agent-kit/v3/project.toml"
    declared.parent.mkdir(parents=True, exist_ok=True)
    declared.write_text("[project]\nwhat_is_this = 1\n", encoding="utf-8")

    store = RunStore(repo)
    create_run(store, builtin_registry(), "add-vat", steps=["probe"], project=str(repo))
    reply = '```json\n{"branch": "kit/add-vat", "can_write": true, "notes": []}\n```'
    outcome = StepRunner(
        store=store, registry=builtin_registry(),
        executors={"fake": FakeExecutor(name="fake", replies=[reply])},
        default_provider="fake",
    ).run_next("add-vat")

    assert outcome.passed
    assert "trunk='main'" in (hooks_dir(repo) / "pre-push").read_text()


def test_a_hook_the_project_owns_is_named_in_the_log_and_not_on_every_step(repo, caplog):
    theirs = hooks_dir(repo) / "pre-push"
    theirs.write_text("#!/bin/sh\nexit 0\n")
    said = []

    from agent_kit.driver import StepRunner, create_run
    from agent_kit.providers.fake import FakeExecutor
    from agent_kit.state import RunStore
    from agent_kit.steps import builtin_registry

    store = RunStore(repo)
    create_run(store, builtin_registry(), "add-vat", steps=["probe"], project=str(repo))
    reply = '```json\n{"branch": "kit/add-vat", "can_write": true, "notes": []}\n```'
    StepRunner(
        store=store, registry=builtin_registry(),
        executors={"fake": FakeExecutor(name="fake", replies=[reply])},
        default_provider="fake", say=said.append,
    ).run_next("add-vat")

    assert theirs.read_text() == "#!/bin/sh\nexit 0\n"
    assert not [line for line in said if "pre-push" in line]
