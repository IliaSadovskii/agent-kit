"""S8 — a worktree per run: two children cannot build in one working copy.

The collision S4 wrote down as the reason S8 exists: `deliver` checks a branch
out in the project itself, so a second run moves HEAD under a session that is
still editing files for a different feature.
"""

import subprocess

import pytest

from agent_kit.driver.tree import make_tree, remove_tree, tree_for, trees, trees_dir
from agent_kit.errors import StateError


def git(root, *argv, check=True):
    return subprocess.run(["git", *argv], cwd=root, check=check, capture_output=True, text=True)


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


def branch_of(tree):
    return git(tree, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def test_a_run_gets_its_own_checkout_on_its_own_branch(repo):
    tree = make_tree(repo, "add-vat", branch="kit/add-vat", base="main")

    assert tree == tree_for(repo, "add-vat")
    assert (tree / "money.py").read_text() == "amount = 1000\n"
    assert branch_of(tree) == "kit/add-vat"
    assert branch_of(repo) == "main"


def test_two_runs_do_not_share_a_head_or_an_index(repo):
    one = make_tree(repo, "rates", branch="kit/rates", base="main")
    two = make_tree(repo, "quote", branch="kit/quote", base="main")

    (one / "money.py").write_text("rates\n")
    (two / "money.py").write_text("quote\n")

    assert (one / "money.py").read_text() == "rates\n"
    assert (two / "money.py").read_text() == "quote\n"
    assert (repo / "money.py").read_text() == "amount = 1000\n"


def test_a_tree_is_based_on_what_the_run_builds_on(repo):
    one = make_tree(repo, "rates", branch="kit/rates", base="main")
    (one / "rates.py").write_text("VAT = 20\n")
    git(one, "add", "-A")
    git(one, "commit", "-m", "rates")

    two = make_tree(repo, "quote", branch="kit/quote", base="kit/rates")

    assert (two / "rates.py").read_text() == "VAT = 20\n"


def test_the_project_is_not_dirtied_by_a_tree(repo):
    make_tree(repo, "add-vat", branch="kit/add-vat", base="main")

    assert git(repo, "status", "--porcelain").stdout.strip() == ""
    assert (trees_dir(repo) / ".gitignore").is_file()


def test_making_it_again_reclaims_what_a_dead_driver_left(repo):
    tree = make_tree(repo, "add-vat", branch="kit/add-vat", base="main")
    (tree / "half-written.py").write_text("what the session got to\n")

    again = make_tree(repo, "add-vat", branch="kit/add-vat", base="main")

    assert again == tree
    assert (again / "half-written.py").read_text() == "what the session got to\n"


def test_a_branch_somebody_else_has_checked_out_is_refused_not_taken(repo):
    git(repo, "checkout", "-b", "kit/add-vat")

    with pytest.raises(StateError) as refused:
        make_tree(repo, "add-vat", branch="kit/add-vat", base="main")

    assert refused.value.code == "tree-held"


def test_a_directory_git_knows_nothing_about_is_refused_by_name(repo):
    where = tree_for(repo, "add-vat")
    where.mkdir(parents=True)
    (where / "somebody-elses.txt").write_text("not ours to delete\n")

    with pytest.raises(StateError) as refused:
        make_tree(repo, "add-vat", branch="kit/add-vat", base="main")

    assert refused.value.code == "tree-in-the-way"
    assert (where / "somebody-elses.txt").is_file()


def test_a_tree_is_taken_away_whole(repo):
    tree = make_tree(repo, "add-vat", branch="kit/add-vat", base="main")
    (tree / "left-over.py").write_text("uncommitted\n")

    assert remove_tree(repo, "add-vat") is True
    assert not tree.exists()
    assert [slug for slug, _, _ in trees(repo)] == []
    assert "kit/add-vat" in git(repo, "branch", "--list").stdout


def test_taking_away_what_is_not_there_is_the_same_as_taking_it_away(repo):
    assert remove_tree(repo, "add-vat") is False


def test_what_stands_can_be_listed(repo):
    make_tree(repo, "rates", branch="kit/rates", base="main")
    make_tree(repo, "quote", branch="kit/quote", base="main")

    standing = {slug: branch for slug, _, branch in trees(repo)}

    assert standing == {"rates": "kit/rates", "quote": "kit/quote"}


def test_a_tree_of_a_project_that_is_not_a_repository_says_so(tmp_path):
    with pytest.raises(StateError) as refused:
        make_tree(tmp_path, "add-vat", branch="kit/add-vat", base="main")

    assert refused.value.code == "not-a-repository"
