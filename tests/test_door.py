"""S8d — the door: where this project stands, and the one thing to do next.

Every case here asks the same question the bench asks from the outside: what
code does the door name, and what command does it print. The prose between
them is never asserted — it is the kit's own screen and it will be rewritten,
and a test that measures a sentence measures nothing.
"""

import json
import os
import subprocess

import pytest

from agent_kit.cli.main import main
from agent_kit.errors import ExitCode
from agent_kit.state import RunStore
from agent_kit.steps import builtin_registry

DECLARED = '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "sh check.sh"\n'
DESCRIBED = "# Продукт\n\n## Части\n\n- деньги — сумма и ставка — `key: money` · `walked: 2026-08-20`\n"


def git(root, *argv, check=True):
    return subprocess.run(
        ["git", *argv], cwd=root, check=check, capture_output=True, text=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e"},
    )


@pytest.fixture
def project(tmp_path, monkeypatch, machine_home):
    """An ordinary described project with one command, in a repository."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "project"
    (root / ".agent-kit/v3").mkdir(parents=True)
    (root / "docs/knowledge").mkdir(parents=True)
    (root / ".agent-kit/v3/project.toml").write_text(DECLARED, encoding="utf-8")
    (root / "docs/knowledge/product.md").write_text(DESCRIBED, encoding="utf-8")
    (root / "check.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    git(root, "init", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-m", "the baseline")
    return root


def door(root, capsys):
    code = main(["-C", str(root), "next"])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def answered(out):
    """The code the door named, which is the first token of its first line."""
    return out.strip().splitlines()[0].split(":")[0].strip()


def a_run(root, slug, steps=("design", "build"), **kw):
    store = RunStore(root)
    return store.create(slug, steps=list(steps), project=str(root), **kw)


def failed(root, slug, reason="contract-not-satisfied: build said nothing", **kw):
    store = RunStore(root)
    a_run(root, slug, **kw)
    store.start_step(slug, provider="fake")
    store.fail_step(slug, reason)
    return store.load(slug)


def delivered(root, slug, branch=None, commit=None, base="main",
              url="https://github.com/o/p/pull/7"):
    """A run that got all the way through, with the papers `deliver` leaves."""
    store = RunStore(root)
    run = a_run(root, slug, steps=("design", "deliver"), branch=branch,
                base="" if base == "main" else base)
    for _ in run.steps:
        store.start_step(slug, provider="fake")
        store.pass_step(slug)
    where = store.run_root(slug) / "steps/1-deliver"
    where.mkdir(parents=True, exist_ok=True)
    (where / "output.json").write_text(
        json.dumps({"branch": run.branch, "base": base, "commit": commit or "", "pull_request": url}),
        encoding="utf-8",
    )
    return store.load(slug)


# --- a project with nothing in it -------------------------------------------


def test_a_bare_directory_gets_an_answer_rather_than_a_stack_trace(tmp_path, capsys):
    bare = tmp_path / "nothing"
    bare.mkdir()

    code, out, _ = door(bare, capsys)

    assert code == ExitCode.OK
    assert answered(out) == "no-description"
    assert "agent-kit knowledge tell" in out


def test_a_path_that_is_not_a_directory_is_the_one_refusal_the_door_has(tmp_path, capsys):
    code, _, err = door(tmp_path / "nowhere", capsys)

    assert code == ExitCode.USAGE
    assert "not-a-directory" in err


def test_a_project_that_says_nobody_describes_it_goes_past_the_description(tmp_path, capsys, monkeypatch, machine_home):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "quiet"
    (root / ".agent-kit/v3").mkdir(parents=True)
    (root / ".agent-kit/v3/project.toml").write_text(
        '[project]\nknowledge = ""\n\n[commands]\ntest = "sh check.sh"\n', encoding="utf-8"
    )

    code, out, _ = door(root, capsys)

    assert code == ExitCode.OK
    assert answered(out) == "nothing-is-due"


def test_a_project_with_nothing_to_check_it_with_is_named_before_a_night(tmp_path, capsys, monkeypatch, machine_home):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "p"
    (root / ".agent-kit/v3").mkdir(parents=True)
    (root / "docs/knowledge").mkdir(parents=True)
    (root / ".agent-kit/v3/project.toml").write_text('[project]\ndefault_branch = "main"\n', encoding="utf-8")
    (root / "docs/knowledge/product.md").write_text(DESCRIBED, encoding="utf-8")

    code, out, _ = door(root, capsys)

    assert code == ExitCode.OK
    assert answered(out) == "no-commands"
    assert "agent-kit init" in out


def test_a_command_this_machine_cannot_start_is_named_with_its_first_word(project, capsys):
    (project / ".agent-kit/v3/project.toml").write_text(
        '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "flibbertigibbet run"\n', encoding="utf-8"
    )

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert answered(out) == "no-such-command"
    assert "flibbertigibbet" in out


def test_a_declaration_that_cannot_be_read_is_a_state_and_not_a_crash(project, capsys):
    (project / ".agent-kit/v3/project.toml").write_text("this is not toml = = =\n", encoding="utf-8")

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert answered(out) == "unreadable-project"


# --- the rungs about work ----------------------------------------------------


def test_a_failed_run_carries_the_code_out_of_its_own_record(project, capsys):
    tree = project / ".agent-kit/v3/trees/add-vat"
    tree.mkdir(parents=True)
    failed(project, "add-vat", tree=str(tree))

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert answered(out) == "run-failed"
    assert "add-vat" in out
    assert "contract-not-satisfied" in out
    assert "agent-kit run show add-vat" in out


def test_a_failed_run_whose_tree_was_taken_away_stops_being_due(project, capsys):
    tree = project / ".agent-kit/v3/trees/add-vat"
    tree.mkdir(parents=True)
    failed(project, "add-vat", tree=str(tree))
    tree.rmdir()

    _, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"


def test_a_failed_run_made_by_hand_stands_while_its_branch_does(project, capsys):
    failed(project, "add-vat")
    git(project, "branch", "kit/add-vat")

    _, out, _ = door(project, capsys)
    assert answered(out) == "run-failed"

    git(project, "branch", "-D", "kit/add-vat")
    _, out, _ = door(project, capsys)
    assert answered(out) == "nothing-is-due"


def test_a_stopped_run_is_carried_on_and_says_why_it_stopped(project, capsys):
    store = RunStore(project)
    a_run(project, "add-vat")
    store.start_step("add-vat", provider="fake")
    store.stop("add-vat", "the owner typed run stop")

    _, out, _ = door(project, capsys)

    assert answered(out) == "run-stopped"
    assert "agent-kit run reopen add-vat" in out
    assert "the owner typed run stop" in out


def test_a_run_nobody_started_is_named_by_its_status(project, capsys):
    a_run(project, "add-vat")

    _, out, _ = door(project, capsys)

    assert answered(out) == "run-created"
    assert "agent-kit run go add-vat" in out


def test_a_run_whose_driver_is_gone_is_work_to_carry_on(project, capsys):
    store = RunStore(project)
    a_run(project, "add-vat")
    store.start_step("add-vat", provider="fake")

    _, out, _ = door(project, capsys)

    assert answered(out) == "run-running"
    assert "agent-kit run go add-vat" in out


def test_a_live_driver_stands_above_everything_else(project, capsys):
    from agent_kit.machine import Ledger, ledger_path
    from agent_kit.paths import Paths

    store = RunStore(project)
    a_run(project, "add-vat")
    store.start_step("add-vat", provider="fake")
    failed(project, "old-one")
    Ledger(ledger_path(Paths.from_env())).hold_run(str(project.resolve()), "add-vat")

    _, out, _ = door(project, capsys)

    assert answered(out) == "a-night-is-running"
    assert "agent-kit machine" in out
    # And nothing below names the same run again with a command the lease would
    # refuse: `run go` on a run somebody is driving is `run-held-elsewhere`.
    assert "agent-kit run go add-vat" not in out
    assert "run-running" not in out
    # One line for one run, though a run with no tree holds two leases.
    assert out.count("a-night-is-running") == 1


def test_a_batch_somebody_is_driving_is_not_offered_to_be_started(project, capsys):
    from agent_kit.machine import Ledger, ledger_path
    from agent_kit.paths import Paths

    batch_of(project, rates="A table of rates", quote="Money quotes a price")
    Ledger(ledger_path(Paths.from_env())).hold_batch(str(project.resolve()), "vat")

    _, out, _ = door(project, capsys)

    assert answered(out) == "a-night-is-running"
    assert "agent-kit batch go vat" not in out
    assert "batch-unfinished" not in out


def test_a_lease_of_another_project_is_not_this_project_running(project, capsys):
    from agent_kit.machine import Ledger, ledger_path
    from agent_kit.paths import Paths

    a_run(project, "add-vat")
    Ledger(ledger_path(Paths.from_env())).hold_run(f"{project.resolve()}-elsewhere", "add-vat")

    _, out, _ = door(project, capsys)

    assert answered(out) == "run-created"


# --- what a broken source may and may not do ---------------------------------


def test_a_record_nobody_can_read_is_named_and_hides_nothing(project, capsys):
    failed(project, "add-vat")
    git(project, "branch", "kit/add-vat")
    broken = project / ".agent-kit/v3/runs/last-summer"
    broken.mkdir(parents=True)
    (broken / "run.json").write_text("{not json", encoding="utf-8")

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert "unreadable-run" in out and "last-summer" in out
    assert answered(out) == "run-failed" and "add-vat" in out


def test_a_ledger_that_cannot_be_read_is_never_an_exit_code_of_its_own(project, capsys, monkeypatch):
    from agent_kit.machine import ledger_path
    from agent_kit.paths import Paths

    where = ledger_path(Paths.from_env())
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text("this is not a database", encoding="utf-8")
    a_run(project, "add-vat")

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert "unreadable-ledger" in out


def test_a_step_output_that_will_not_parse_is_said_out_loud(project, capsys):
    delivered(project, "add-vat")
    (project / ".agent-kit/v3/runs/add-vat/steps/1-deliver/output.json").write_text("{", encoding="utf-8")

    _, out, _ = door(project, capsys)

    assert "unreadable-step-output" in out


# --- the batch ---------------------------------------------------------------


def batch_of(root, **features):
    from agent_kit.batch import BatchStore
    from agent_kit.batch.declaration import read_declaration

    lines = ['name = "vat"', "", "[mvp]", 'inside = ["a price"]', 'outside = ["nothing"]', "",
             "[[scenarios]]", 'what = "a customer is quoted"', 'ends = "the command is green"']
    for slug, brief in features.items():
        lines += ["", f"[features.{slug}]", f'brief = "{brief}"']
    declared = root / "batch.toml"
    declared.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return BatchStore(root).create(read_declaration(declared))


def test_a_batch_nobody_started_is_the_batchs_own_line(project, capsys):
    batch_of(project, rates="A table of rates", quote="Money quotes a price")

    _, out, _ = door(project, capsys)

    assert answered(out) == "batch-unfinished"
    assert "agent-kit batch go vat" in out


def test_a_batch_owns_the_name_of_its_features_not_their_rank(project, capsys):
    from agent_kit.batch import BatchStore, FeatureStatus

    batch = batch_of(project, rates="A table of rates", quote="Money quotes a price")
    store = BatchStore(project)
    batch.ended("rates", FeatureStatus.FAILED, reason="build: contract-not-satisfied")
    batch.ended("quote", FeatureStatus.SKIPPED, reason="it needed rates")
    store.save(batch)
    failed(project, "rates")
    git(project, "branch", "kit/rates")

    _, out, _ = door(project, capsys)

    assert answered(out) == "run-failed"
    assert "vat" in out and "rates" in out


def test_a_batch_that_cannot_be_read_does_not_turn_into_its_runs(project, capsys):
    batch_of(project, rates="A table of rates")
    (project / ".agent-kit/v3/batches/vat/batch.json").write_text("{no", encoding="utf-8")
    a_run(project, "rates")

    _, out, _ = door(project, capsys)

    assert "unreadable-batch" in out and "vat" in out
    assert answered(out) != "run-created"


# --- the report that is waiting ----------------------------------------------


def test_a_delivered_run_names_its_pull_request(project, capsys):
    git(project, "checkout", "-b", "kit/add-vat")
    (project / "money.py").write_text("RATE = 20\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the rate")
    head = git(project, "rev-parse", "HEAD").stdout.strip()
    git(project, "checkout", "main")
    delivered(project, "add-vat", commit=head)

    _, out, _ = door(project, capsys)

    assert answered(out) == "pull-request-waiting"
    assert "https://github.com/o/p/pull/7" in out


def test_a_pull_request_whose_commit_is_in_the_trunk_is_no_longer_waiting(project, capsys):
    git(project, "checkout", "-b", "kit/add-vat")
    (project / "money.py").write_text("RATE = 20\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the rate")
    head = git(project, "rev-parse", "HEAD").stdout.strip()
    git(project, "checkout", "main")
    git(project, "merge", "--no-ff", "-m", "merged", "kit/add-vat")
    delivered(project, "add-vat", commit=head)

    _, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"


def test_a_pull_request_squashed_into_the_trunk_is_no_longer_waiting(project, capsys):
    git(project, "checkout", "-b", "kit/add-vat")
    (project / "money.py").write_text("RATE = 20\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the rate")
    head = git(project, "rev-parse", "HEAD").stdout.strip()
    git(project, "checkout", "main")
    git(project, "merge", "--squash", "kit/add-vat")
    git(project, "commit", "-m", "the rate, squashed")
    delivered(project, "add-vat", commit=head)

    _, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"


def test_a_pull_request_git_cannot_answer_about_keeps_standing(project, capsys):
    delivered(project, "add-vat", commit="0" * 40)

    _, out, _ = door(project, capsys)

    assert answered(out) == "pull-request-waiting"


# --- the order, and what happens when nothing is due -------------------------


def test_the_first_rung_with_anything_on_it_is_the_answer(project, capsys):
    delivered(project, "shipped")
    store = RunStore(project)
    a_run(project, "stopped-one")
    store.start_step("stopped-one", provider="fake")
    store.stop("stopped-one", "the owner typed run stop")
    failed(project, "broken-one")
    git(project, "branch", "kit/broken-one")

    _, out, _ = door(project, capsys)

    assert answered(out) == "run-failed"
    # and the rest of the ladder is still printed, because the view and the
    # answer are one pass over one set of data.
    assert "run-stopped" in out and "pull-request-waiting" in out


def test_inside_one_rung_the_newest_record_goes_first(project, capsys):
    failed(project, "older")
    git(project, "branch", "kit/older")
    failed(project, "newer")
    git(project, "branch", "kit/newer")
    store = RunStore(project)
    newer = store.load("newer")
    newer.updated_at = "2099-01-01T00:00:00+00:00"
    store.save(newer)

    _, out, _ = door(project, capsys)

    assert out.strip().splitlines()[0].split(":")[1].strip().startswith("newer")


def test_a_quiet_project_is_told_where_the_evening_is_composed(project, capsys):
    _, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"
    assert "agent-kit batch compose" in out


def test_a_candidate_list_standing_from_an_audit_is_named(project, capsys):
    room = project / ".agent-kit/v3/audits/dependencies-2026-08-27"
    room.mkdir(parents=True)
    (room / "candidates.md").write_text("# что можно сделать\n\n1. убрать requests\n", encoding="utf-8")

    _, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"
    assert "candidates.md" in out


def test_the_standing_blocks_are_counted_beside_the_hour_that_settles_them(project, capsys):
    (project / "docs/knowledge/product.md").write_text(
        DESCRIBED
        + "\n## Допущения\n\n> **[assumed 2026-08-20 · add-vat · id: k7f3q2]** ставка целая\n",
        encoding="utf-8",
    )

    _, out, _ = door(project, capsys)

    assert "assumed" in out and "agent-kit knowledge tell" in out


def test_the_door_always_leaves_zero_behind_it(project, capsys):
    failed(project, "add-vat")
    git(project, "branch", "kit/add-vat")

    code, _, _ = door(project, capsys)

    assert code == ExitCode.OK


def test_a_checkout_git_cannot_answer_in_says_so_rather_than_no(tmp_path, capsys, monkeypatch, machine_home):
    """git could not be asked, and that is not the same answer as *not yet*.

    A directory that is no repository answers 128 to both questions, and 128 is
    not a *no*. The pull request keeps standing and the sentence says which of
    the three answers this is.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "loose"
    (root / ".agent-kit/v3").mkdir(parents=True)
    (root / "docs/knowledge").mkdir(parents=True)
    (root / ".agent-kit/v3/project.toml").write_text(DECLARED, encoding="utf-8")
    (root / "docs/knowledge/product.md").write_text(DESCRIBED, encoding="utf-8")
    delivered(root, "add-vat", commit="0" * 40)

    _, out, _ = door(root, capsys)

    assert answered(out) == "pull-request-waiting"
    assert "could not be asked" in out


def test_a_report_that_is_not_in_the_trunk_says_that_and_not_the_other(project, capsys):
    """And the *no* is a no, said in different words from the *do not know*."""
    git(project, "checkout", "-b", "kit/add-vat")
    (project / "money.py").write_text("RATE = 20\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the rate")
    head = git(project, "rev-parse", "HEAD").stdout.strip()
    git(project, "checkout", "main")
    delivered(project, "add-vat", commit=head)

    _, out, _ = door(project, capsys)

    assert answered(out) == "pull-request-waiting"
    assert "does not have it in main" in out
    assert "could not be asked" not in out


# --- a feature in a stack, and the trunk it really lands in ------------------


def test_a_stacked_feature_stops_waiting_when_the_stack_reaches_the_trunk(project, capsys):
    """A feature that needs another is based on that one's branch, and that branch
    never receives the merge: the owner merges the stack into the trunk. Asking
    only against the base would keep naming the report for ever.
    """
    git(project, "checkout", "-b", "kit/rates")
    (project / "rates.py").write_text("RATES = {}\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the rates")
    git(project, "checkout", "-b", "kit/quote")
    (project / "quote.py").write_text("QUOTE = 1\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the quote")
    head = git(project, "rev-parse", "HEAD").stdout.strip()
    git(project, "checkout", "main")
    git(project, "merge", "--no-ff", "-m", "the stack", "kit/quote")

    delivered(project, "quote", branch="kit/quote", commit=head, base="kit/rates")

    _, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"


def test_a_stacked_feature_still_waiting_is_still_named(project, capsys):
    """The other direction, so the question above is not merely never asked."""
    git(project, "checkout", "-b", "kit/rates")
    (project / "rates.py").write_text("RATES = {}\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the rates")
    git(project, "checkout", "-b", "kit/quote")
    (project / "quote.py").write_text("QUOTE = 1\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the quote")
    head = git(project, "rev-parse", "HEAD").stdout.strip()
    git(project, "checkout", "main")

    delivered(project, "quote", branch="kit/quote", commit=head, base="kit/rates")

    _, out, _ = door(project, capsys)

    assert answered(out) == "pull-request-waiting"


def test_a_report_whose_branches_are_gone_is_answered_by_the_trunk(project, capsys):
    """Merged and tidied up: both branches deleted, the commit still in the trunk."""
    git(project, "checkout", "-b", "kit/add-vat")
    (project / "money.py").write_text("RATE = 20\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-m", "the rate")
    head = git(project, "rev-parse", "HEAD").stdout.strip()
    git(project, "checkout", "main")
    git(project, "merge", "--no-ff", "-m", "merged", "kit/add-vat")
    delivered(project, "add-vat", commit=head)
    git(project, "branch", "-D", "kit/add-vat")

    _, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"


# --- what a batch carries on, and what it does not --------------------------


def test_a_feature_of_a_batch_that_is_over_is_carried_on_by_its_batch(project, capsys):
    """`run reopen` is not what continues a feature; `batch reopen` is.

    A feature of a batch that is still going is left to `batch go` and gets no
    line of its own. This is the other case: the batch is over — nothing
    running and nothing that may start — and the feature it stopped is a real
    thing to carry on, by the name its batch knows it under.
    """
    from agent_kit.batch import BatchStore, FeatureStatus

    batch = batch_of(project, rates="A table of rates", quote="Money quotes a price")
    store = BatchStore(project)
    batch.ended("rates", FeatureStatus.STOPPED, reason="a gate closed on verify")
    batch.ended("quote", FeatureStatus.SKIPPED, reason="it is not for tonight")
    store.save(batch)
    assert batch.finished

    runs = RunStore(project)
    a_run(project, "rates")
    runs.start_step("rates", provider="fake")
    runs.stop("rates", "a gate closed on verify")

    _, out, _ = door(project, capsys)

    assert "agent-kit run reopen rates" not in out
    assert "agent-kit batch reopen vat rates" in out


def test_a_batch_that_cannot_be_read_hides_no_run_but_its_own(project, capsys):
    """One unreadable source hides none of the rest — including the runs beside it."""
    batch_of(project, rates="A table of rates")
    (project / ".agent-kit/v3/batches/vat/batch.json").write_text("{no", encoding="utf-8")
    a_run(project, "somebody-elses")

    _, out, _ = door(project, capsys)

    assert answered(out) == "unreadable-batch"
    assert "run-created" in out and "somebody-elses" in out


# --- the ledger's two codes -------------------------------------------------


def test_a_ledger_from_a_newer_kit_is_named_by_its_own_code(project, capsys):
    import sqlite3

    from agent_kit.machine import ledger_path
    from agent_kit.paths import Paths

    where = ledger_path(Paths.from_env())
    where.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(where))
    db.execute("PRAGMA user_version=9999")
    db.close()
    a_run(project, "add-vat")

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert "ledger-too-new" in out
    assert "unreadable-ledger" not in out


def test_the_door_does_not_bring_a_ledger_into_being(project, capsys):
    """It reads what is true right now; a machine nothing has run on has no ledger."""
    from agent_kit.machine import ledger_path
    from agent_kit.paths import Paths

    where = ledger_path(Paths.from_env())
    assert not where.exists()

    door(project, capsys)

    assert not where.exists()


# --- S8e: the kinds of verification, in the view and never on the ladder ----


def test_a_kind_nobody_answered_is_reported_and_never_stands_in_the_way(project, capsys):
    """The one thing rung 1 may hold is what a night would be refused for.

    Nothing refuses an unanswered kind — the catalogue is the kit's and every
    project in the world starts with none of it answered — so a rung for it
    would be one the door could never descend, which is the defect S8d was
    built against.
    """
    main(["-C", str(project), "next"])

    said = capsys.readouterr().out
    answer, _, rest = said.partition("\n")
    assert "kind-unanswered" not in answer
    assert "verification" in rest
    assert "suite" in rest and "types" in rest


def test_what_a_project_answered_about_a_kind_is_printed_beside_the_kind(project, capsys):
    (project / ".agent-kit/v3/project.toml").write_text(
        DECLARED + '\n[verification.suite]\ncommand = "sh check.sh"\n'
        '\n[verification.types]\nwhy = "ничего здесь не типизировано"\nsince = "2026-08-28"\n',
        encoding="utf-8",
    )

    main(["-C", str(project), "next"])

    said = capsys.readouterr().out
    assert "sh check.sh" in said
    assert "2026-08-28" in said


def test_an_answer_that_could_never_fail_is_named_where_the_answers_are(project, capsys):
    (project / ".agent-kit/v3/project.toml").write_text(
        DECLARED + '\n[verification.suite]\ncommand = "true"\n', encoding="utf-8"
    )

    main(["-C", str(project), "next"])

    assert "command-that-proves-nothing" in capsys.readouterr().out


def test_the_command_that_prints_the_catalogue_names_every_kind(project, capsys):
    assert main(["-C", str(project), "verification"]) == 0

    said = capsys.readouterr().out
    for kind in ("suite", "types", "end-to-end"):
        assert kind in said


def test_the_catalogue_says_what_a_kind_catches_and_never_a_tool(project, capsys):
    main(["-C", str(project), "verification"])

    said = capsys.readouterr().out
    assert "code that worked and stopped working" in said
    for tool in ("pytest", "mypy", "eslint"):
        assert tool not in said


def test_the_door_counts_the_ledger_and_names_no_command_for_it(project, capsys):
    """A counter in the view and never a rung: no command closes a line of debt —
    the work does — and a rung nothing can take away is a rung the door stops
    descending at."""
    from agent_kit.knowledge import Knowledge

    Knowledge(project / "docs/knowledge").write_debt("отчёт считает вручную", "badly")

    _, out, _ = door(project, capsys)

    assert "1 in the ledger" in out
    assert "долг" not in out.splitlines()[0]


def test_a_ledger_that_cannot_be_read_does_not_take_the_door_down(project, capsys):
    """The door does not refuse about a project, and that includes its ledger."""
    (project / "docs/knowledge/debt.md").write_text(
        "- одна · `key: aaaaaa`\n- две · `key: aaaaaa`\n", encoding="utf-8"
    )

    code, out, _ = door(project, capsys)

    assert code == 0
    assert "two-lines-one-key" in out


# --- S8g: the chores a person owes ------------------------------------------
#
# The seam §10 of this note named: a rung between *work unfinished* and *a
# report is waiting*, reading a file that had no writer then. Only a line the
# kit can take away stands on it — a `by-hand` line can be closed by nobody but
# a person, and a rung nothing can remove is a rung the door stops descending
# at, which is the defect the review found in `run-failed`.


def a_manual_holding(root, *lines):
    path = root / ".agent-kit/v3/manual.md"
    path.write_text("# Сделать руками\n\n" + "".join(f"- {line}\n" for line in lines), encoding="utf-8")
    return path


def test_a_chore_with_a_proof_is_what_the_door_names(project, capsys):
    a_manual_holding(project, "положить STRIPE_KEY · `key: aaaaaa` · `proof: sh ops/key.sh`")

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert answered(out) == "manual-due"
    assert "agent-kit manual check" in out


def test_a_chore_only_a_person_can_close_never_puts_the_door_on_a_rung(project, capsys):
    a_manual_holding(project, "подтвердить домен · `key: bbbbbb` · `by-hand: код приходит на телефон`")

    code, out, _ = door(project, capsys)

    assert answered(out) == "nothing-is-due"
    assert "bbbbbb" in out  # counted in the view, and never ranked


def test_an_unfinished_run_still_outranks_a_chore(project, capsys):
    a_manual_holding(project, "положить ключ · `key: aaaaaa` · `proof: sh ops/key.sh`")
    a_run(project, "add-vat")

    _, out, _ = door(project, capsys)

    assert answered(out) == "run-created"


def test_a_chore_outranks_a_report_that_is_waiting(project, capsys):
    a_manual_holding(project, "положить ключ · `key: aaaaaa` · `proof: sh ops/key.sh`")
    delivered(project, "add-vat")

    _, out, _ = door(project, capsys)

    assert answered(out) == "manual-due"
    assert "pull-request-waiting" in out


def test_a_chore_the_door_ranks_is_a_chore_the_walk_runs(project, capsys):
    """The door ranks on the proof and the walk branches on the proof, so a line
    carrying both segments cannot become a rung nothing can remove."""
    a_manual_holding(
        project,
        "поставить ключ · `key: aaaaaa` · `proof: sh yes.sh` · `by-hand: и позвонить в банк`",
    )
    (project / "yes.sh").write_text("exit 0\n", encoding="utf-8")

    _, out, _ = door(project, capsys)
    assert answered(out) == "manual-due"

    from agent_kit.manual import Manual, check

    assert check(project).done == ["aaaaaa"]
    assert Manual(project).actions() == []


def test_a_file_the_door_cannot_read_names_a_code_and_hides_nothing(project, capsys):
    (project / ".agent-kit/v3/manual.md").write_text("```\n- открыто · `key: a`\n", encoding="utf-8")

    code, out, _ = door(project, capsys)

    assert code == ExitCode.OK
    assert "unreadable-manual" in out
    assert answered(out) == "nothing-is-due"


def test_the_door_names_the_chore_and_never_runs_the_proof(project, capsys):
    """A door that acts is not a door: the proof is run by the command it names."""
    a_manual_holding(project, "положить ключ · `key: aaaaaa` · `proof: touch ran-here`")

    door(project, capsys)

    assert not (project / "ran-here").exists()
