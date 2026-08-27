"""S8 — the commands a person types for a batch, and what each of them refuses."""

import json
import subprocess

import pytest

from agent_kit.cli.main import main
from agent_kit.errors import ExitCode

DECLARED = """
name = "vat"

[mvp]
inside = ["a price with VAT on it"]
outside = ["registration numbers"]

[[scenarios]]
what = "a customer is quoted and then invoiced"
ends = "the quote and the receipt name the same tax"

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


def test_the_door_lists_the_batches_and_show_says_where_a_feature_got_to(project, capsys):
    """`batch list` is the door's line now; `batch show` is still one batch in detail."""
    run(["batch", "new", "batch.toml"], capsys)

    code, out, _ = run(["-C", str(project), "next"], capsys)
    assert code == ExitCode.OK and "vat" in out

    with pytest.raises(SystemExit) as caught:
        main(["batch", "list"])
    assert caught.value.code == ExitCode.USAGE
    assert "list" in capsys.readouterr().err

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


def a_feature_the_night_stopped(project, capsys):
    """A batch whose first feature stopped, with the run it stands on stopped too."""
    from agent_kit.batch import BatchStore, FeatureStatus
    from agent_kit.state import RunStore

    run(["batch", "new", "batch.toml"], capsys)
    runs = RunStore(project)
    runs.create("rates", steps=["design", "build"], project=str(project.resolve()))
    runs.start_step("rates")
    runs.stop("rates", "stopped-by-request: enough for tonight")

    batches = BatchStore(project)
    made = batches.load("vat")
    made.starting("rates", tree=None)
    made.ended("rates", FeatureStatus.STOPPED, reason="stopped-by-request: enough for tonight")
    batches.save(made)
    return batches, runs


def test_a_stopped_feature_is_carried_on_with_the_run_it_stands_on(project, capsys):
    from agent_kit.batch import FeatureStatus
    from agent_kit.state import RunStatus

    batches, runs = a_feature_the_night_stopped(project, capsys)

    code, out, _ = run(["batch", "reopen", "vat", "rates"], capsys)

    assert code == ExitCode.OK
    # Said at the moment it is typed, the way a skip is: quote is coming back too.
    assert "rates" in out and "quote" in out
    made = batches.load("vat")
    assert made.feature("rates").status is FeatureStatus.PENDING
    assert made.feature("quote").status is FeatureStatus.PENDING
    assert made.ready() == ["rates"]
    # And the run itself, or `batch go` would read the same ending straight back.
    assert runs.load("rates").status is RunStatus.RUNNING


def test_a_feature_is_not_carried_on_under_a_driver_that_is_building_the_batch(project, capsys):
    from agent_kit.machine import Ledger, ledger_path
    from agent_kit.paths import Paths

    a_feature_the_night_stopped(project, capsys)
    Ledger(ledger_path(Paths.from_env())).hold_batch(str(project.resolve()), "vat", pid=1)

    code, _, err = run(["batch", "reopen", "vat", "rates"], capsys)

    assert code == ExitCode.STATE
    assert "batch-held-elsewhere" in err


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


# --- S8b: the gate, at the one place a batch is made ------------------------


def test_a_night_whose_scenarios_have_no_ending_is_refused_before_anything_is_made(project, capsys):
    (project / "batch.toml").write_text(
        DECLARED.replace(
            'ends = "the quote and the receipt name the same tax"', 'ends = ""'
        ),
        encoding="utf-8",
    )

    code, _, err = run(["batch", "new", "batch.toml"], capsys)

    assert code == ExitCode.CONFIG
    assert "scenario-with-no-ending" in err
    assert not (project / ".agent-kit/v3/batches").exists()
    assert not (project / ".agent-kit/v3/runs").exists()
    assert not (project / ".agent-kit/v3/trees").exists()


def test_a_night_with_no_bounds_is_refused(project, capsys):
    (project / "batch.toml").write_text(
        DECLARED.replace('outside = ["registration numbers"]', "outside = []"), encoding="utf-8"
    )

    code, _, err = run(["batch", "new", "batch.toml"], capsys)

    assert code == ExitCode.CONFIG and "bounds-unwritten" in err


def test_a_project_with_no_way_to_check_anything_does_not_start_a_night(project, capsys):
    (project / ".agent-kit/v3/project.toml").write_text(
        '[project]\ndefault_branch = "main"\n', encoding="utf-8"
    )

    code, _, err = run(["batch", "new", "batch.toml"], capsys)

    assert code == ExitCode.CONFIG
    assert "no-commands" in err
    assert not (project / ".agent-kit/v3/batches").exists()


def test_the_refusal_names_everything_it_found_and_not_only_the_first(project, capsys):
    (project / ".agent-kit/v3/project.toml").write_text(
        '[project]\ndefault_branch = "main"\n', encoding="utf-8"
    )
    (project / "batch.toml").write_text(
        DECLARED.replace('outside = ["registration numbers"]', "outside = []"), encoding="utf-8"
    )

    code, _, err = run(["batch", "new", "batch.toml"], capsys)

    assert code == ExitCode.CONFIG
    assert "bounds-unwritten" in err and "no-commands" in err


def test_a_frame_the_declaration_names_reaches_the_batch_file(project, capsys):
    (project / "batch.toml").write_text(
        DECLARED + '\n[[frames]]\nwhat = "the rate lives in one place"\n', encoding="utf-8"
    )
    run(["batch", "new", "batch.toml"], capsys)

    held = json.loads((project / ".agent-kit/v3/batches/vat/batch.json").read_text())
    assert [frame["what"] for frame in held["frames"]] == ["the rate lives in one place"]
    assert held["frames"][0]["id"] == ""
