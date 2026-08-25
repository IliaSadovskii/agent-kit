"""S8 — the commands a person types for a batch, and what each of them refuses."""

import json
import subprocess

import pytest

from agent_kit.cli.main import main
from agent_kit.errors import ExitCode

DECLARED = """
name = "vat"

[features.rates]
brief = "A table of VAT rates"

[features.quote]
brief = "Money quotes a price with VAT"
needs = ["rates"]
"""


def git(root, *argv):
    return subprocess.run(["git", *argv], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture
def project(tmp_path, monkeypatch, machine_home):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "kit@example.com")
    git(root, "config", "user.name", "kit")
    (root / "money.py").write_text("amount = 1000\n")
    declared = root / ".agent-kit/v3/project.toml"
    declared.parent.mkdir(parents=True, exist_ok=True)
    declared.write_text('[project]\ndefault_branch = "main"\n\n[commands]\ntest = "true"\n', encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-m", "first")
    (root / "batch.toml").write_text(DECLARED, encoding="utf-8")
    monkeypatch.chdir(root)
    return root


def run(argv, capsys):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_a_batch_is_created_from_the_file_the_owner_wrote(project, capsys):
    code, out, _ = run(["batch", "new", "batch.toml"], capsys)

    assert code == ExitCode.OK
    assert "vat" in out and "2" in out
    assert (project / ".agent-kit/v3/batches/vat/batch.json").is_file()


def test_a_declaration_that_cannot_run_is_refused_before_anything_is_made(project, capsys):
    (project / "batch.toml").write_text(
        'name = "vat"\n\n[features.quote]\nbrief = "b"\nneeds = ["rates"]\n', encoding="utf-8"
    )

    code, _, err = run(["batch", "new", "batch.toml"], capsys)

    assert code == ExitCode.CONFIG
    assert "no-such-feature" in err
    assert not (project / ".agent-kit/v3/batches").exists()


def test_batch_list_and_show_say_where_every_feature_got_to(project, capsys):
    run(["batch", "new", "batch.toml"], capsys)

    code, out, _ = run(["batch", "list"], capsys)
    assert code == ExitCode.OK and "vat" in out

    code, out, _ = run(["batch", "show", "vat"], capsys)
    assert code == ExitCode.OK
    assert "rates" in out and "quote" in out and "pending" in out
    assert "needs rates" in out


def test_batch_show_json_is_the_state_itself(project, capsys):
    run(["batch", "new", "batch.toml"], capsys)

    _, out, _ = run(["batch", "show", "vat", "--json"], capsys)

    assert json.loads(out)["features"][0]["slug"] == "rates"


def test_skipping_says_what_it_takes_with_it_at_the_moment_it_is_typed(project, capsys):
    run(["batch", "new", "batch.toml"], capsys)

    code, out, _ = run(["batch", "skip", "vat", "rates", "not settled yet"], capsys)

    assert code == ExitCode.OK
    assert "rates" in out and "quote" in out

    _, shown, _ = run(["batch", "show", "vat"], capsys)
    assert shown.count("skipped") == 2


def test_a_skip_reaches_the_driver_that_holds_the_batch(project, capsys):
    from agent_kit.machine import Ledger, ledger_path
    from agent_kit.paths import Paths

    run(["batch", "new", "batch.toml"], capsys)
    ledger = Ledger(ledger_path(Paths.from_env()))
    ledger.hold_batch(str(project.resolve()), "vat", pid=1)

    code, out, _ = run(["batch", "skip", "vat", "rates", "not settled yet"], capsys)

    assert code == ExitCode.OK
    assert "skip-asked" in out
    assert ledger.skips_asked(str(project.resolve()), "vat") == [("rates", "not settled yet")]


def test_stopping_a_batch_nobody_drives_is_written_where_it_stands(project, capsys):
    run(["batch", "new", "batch.toml"], capsys)

    code, out, _ = run(["batch", "stop", "vat", "enough for tonight"], capsys)

    assert code == ExitCode.OK
    _, shown, _ = run(["batch", "show", "vat"], capsys)
    assert "enough for tonight" in shown


def test_an_unknown_batch_is_a_state_error_that_names_it(project, capsys):
    code, _, err = run(["batch", "show", "hedges"], capsys)

    assert code == ExitCode.STATE
    assert "hedges" in err


def test_the_trees_a_project_holds_can_be_listed_and_taken_away(project, capsys):
    from agent_kit.driver.tree import make_tree

    make_tree(project, "rates", branch="kit/rates", base="main")

    code, out, _ = run(["tree", "list"], capsys)
    assert code == ExitCode.OK and "rates" in out

    code, out, _ = run(["tree", "remove", "rates"], capsys)
    assert code == ExitCode.OK

    _, out, _ = run(["tree", "list"], capsys)
    assert "rates" not in out


def test_a_run_can_be_told_that_somebody_else_speaks_for_it(project, capsys):
    """`--silent` is read by the driver: a batch of five must not wake a phone five times."""
    from agent_kit.cli.main import build_parser

    parsed = build_parser().parse_args(["run", "go", "add-vat", "--silent"])

    assert parsed.silent is True
