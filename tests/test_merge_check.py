"""S8 — will these branches merge, asked at 03:00 rather than in the morning.

The kit merges nothing: it finds out, in a tree it throws away, and says so.
"""

import subprocess

import pytest

from agent_kit.batch.merge import check_merges


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


def feature(root, name, path, text):
    git(root, "checkout", "-b", f"kit/{name}", "main")
    (root / path).write_text(text)
    git(root, "add", "-A")
    git(root, "commit", "-m", name)
    git(root, "checkout", "main")


def test_branches_that_touch_different_files_merge(repo):
    feature(repo, "rates", "rates.py", "VAT = 20\n")
    feature(repo, "receipt", "receipt.py", "def line(): ...\n")

    assert check_merges(repo, "main", [("rates", "kit/rates"), ("receipt", "kit/receipt")]) == []


def test_two_features_that_rewrote_one_line_are_named_with_the_file(repo):
    feature(repo, "rates", "money.py", "amount = 1200  # rates\n")
    feature(repo, "quote", "money.py", "amount = 1500  # quote\n")

    found = check_merges(repo, "main", [("rates", "kit/rates"), ("quote", "kit/quote")])

    assert [conflict.slug for conflict in found] == ["quote"]
    assert found[0].files == ["money.py"]
    assert "money.py" in found[0].said()


def test_it_changes_no_branch_and_leaves_no_tree(repo):
    feature(repo, "rates", "money.py", "amount = 1200\n")
    feature(repo, "quote", "money.py", "amount = 1500\n")
    before = git(repo, "log", "--all", "--format=%H").stdout

    check_merges(repo, "main", [("rates", "kit/rates"), ("quote", "kit/quote")])

    assert git(repo, "log", "--all", "--format=%H").stdout == before
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"
    assert git(repo, "status", "--porcelain").stdout.strip() == ""
    assert "merge-check" not in git(repo, "worktree", "list").stdout


def test_one_branch_is_nothing_to_check(repo):
    feature(repo, "rates", "money.py", "amount = 1200\n")

    assert check_merges(repo, "main", [("rates", "kit/rates")]) == []


def test_a_feature_that_never_delivered_is_left_out_rather_than_blamed(repo):
    feature(repo, "rates", "rates.py", "VAT = 20\n")

    assert check_merges(repo, "main", [("rates", "kit/rates"), ("quote", "kit/quote")]) == []


def test_a_conflict_does_not_stop_the_branches_after_it_being_checked(repo):
    feature(repo, "rates", "money.py", "amount = 1200\n")
    feature(repo, "quote", "money.py", "amount = 1500\n")
    feature(repo, "receipt", "money.py", "amount = 1900\n")

    found = check_merges(
        repo, "main", [("rates", "kit/rates"), ("quote", "kit/quote"), ("receipt", "kit/receipt")]
    )

    assert [conflict.slug for conflict in found] == ["quote", "receipt"]
