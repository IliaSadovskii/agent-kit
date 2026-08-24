"""S7 — what a person types at the machine, and what the page answers.

The commands here are an operator's surface, not a door of the method: they
show what is held, they hand a slot to a script that is standing in for a
driver, and they post a stop where the run's own driver reads it.
"""

import json

import pytest

from agent_kit.cli.main import main
from agent_kit.config import DEFAULT_WAIT, load_config
from agent_kit.errors import ExitCode
from agent_kit.machine import Ledger, Want, ledger_path
from agent_kit.paths import Paths


@pytest.fixture
def machine(tmp_path, monkeypatch, machine_home):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path / "project")
    return tmp_path


@pytest.fixture
def ledger(machine):
    return Ledger(ledger_path(Paths.from_env()))


def run(argv, capsys):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- the configuration finally has a reader ---------------------------------


def test_the_machine_can_say_how_long_a_run_waits(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[machine]\nmax_sessions = 2\nwait = 60\n", encoding="utf-8")

    config = load_config(path)

    assert (config.machine.max_sessions, config.machine.wait) == (2, 60)


def test_waiting_has_a_default_so_nobody_has_to_choose_one(tmp_path):
    assert load_config(tmp_path / "nothing.toml").machine.wait == DEFAULT_WAIT


def test_the_page_is_a_choice_of_this_machine(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[daemon]\nhost = "0.0.0.0"\nport = 8081\n', encoding="utf-8")

    config = load_config(path)

    assert (config.daemon.host, config.daemon.port) == ("0.0.0.0", 8081)


def test_the_page_answers_on_loopback_unless_it_is_told_otherwise(tmp_path):
    daemon = load_config(tmp_path / "nothing.toml").daemon

    assert (daemon.host, daemon.port) == ("127.0.0.1", 8080)


# --- what a person reads -----------------------------------------------------


def test_machine_prints_what_is_held_queued_and_limited(machine, ledger, capsys):
    ledger.take(Want(account="anthropic", provider="claude_code", project="/p", slug="one", step="build"),
                _four())
    ledger.wants_one(Want(account="anthropic", provider="claude_code", project="/p", slug="two", step="build"))
    ledger.limit("openai", until="2026-08-24T17:00:00+00:00", said_by="three/build")

    code, out, _ = run(["machine"], capsys)

    assert code == ExitCode.OK
    assert "one" in out and "two" in out
    assert "openai" in out and "17:00" in out


def test_machine_says_so_plainly_when_nothing_is_happening(machine, ledger, capsys):
    code, out, _ = run(["machine"], capsys)

    assert code == ExitCode.OK
    assert "nothing" in out.lower()


def test_doctor_says_where_the_ledger_is(machine, capsys):
    code, out, _ = run(["doctor"], capsys)

    assert code == ExitCode.OK
    assert "daemon.sqlite" in out


# --- a slot by hand ----------------------------------------------------------


def test_a_slot_can_be_taken_and_given_back_by_hand(machine, ledger, capsys):
    code, out, _ = run(["slot", "take", "--provider", "fake", "--slug", "by-hand"], capsys)

    assert code == ExitCode.OK
    assert [row.slug for row in ledger.held()] == ["by-hand"]

    code, _, _ = run(["slot", "release", "--slug", "by-hand"], capsys)

    assert code == ExitCode.OK
    assert ledger.held() == []


def test_a_slot_that_cannot_be_had_is_refused_by_name(machine, ledger, capsys):
    ledger.take(Want(account="fake", provider="fake", project="/p", slug="holder", step="build"), _four())

    code, _, err = run(
        ["slot", "take", "--provider", "fake", "--slug", "second", "--machine-max", "1"], capsys
    )

    assert code == ExitCode.PROVIDER
    assert "no-slot" in err


def test_a_slot_taken_by_hand_lives_as_long_as_it_was_asked_for(machine, ledger, capsys):
    run(["slot", "take", "--provider", "fake", "--slug", "brief", "--ttl", "0"], capsys)

    assert ledger.held() == [], "a lease with no life left outlived itself"


def test_a_slot_can_be_held_for_a_process_that_is_not_this_one(machine, ledger, capsys):
    """What the bench needs: a lease held by a driver that is alive and is not the run."""
    code, _, _ = run(["slot", "take", "--provider", "fake", "--slug", "somebody", "--pid", "1"], capsys)

    assert code == ExitCode.OK
    assert [row.pid for row in ledger.held()] == [1]


def test_a_run_can_be_held_by_hand_so_a_second_driver_meets_the_first(machine, ledger, capsys):
    code, _, _ = run(["slot", "hold", "--slug", "add-vat", "--pid", "1"], capsys)

    assert code == ExitCode.OK
    assert [row.slug for row in ledger.runs()] == ["add-vat"]


def test_a_run_held_by_hand_does_not_fill_the_machine(machine, ledger, capsys):
    run(["slot", "hold", "--slug", "add-vat", "--pid", "1"], capsys)

    assert ledger.held() == []


# --- a limit by hand ---------------------------------------------------------


def test_a_limit_can_be_set_and_cleared_by_hand(machine, ledger, capsys):
    code, _, _ = run(["limit", "set", "anthropic", "--until", "2026-08-24T17:00:00+00:00"], capsys)

    assert code == ExitCode.OK
    assert [row.account for row in ledger.limits()] == ["anthropic"]

    code, _, _ = run(["limit", "clear", "anthropic"], capsys)

    assert code == ExitCode.OK
    assert ledger.limits() == []


def test_a_limit_that_is_not_a_time_is_refused_before_it_is_written(machine, ledger, capsys):
    code, _, err = run(["limit", "set", "anthropic", "--until", "half past nine"], capsys)

    assert code == ExitCode.USAGE
    assert "bad-time" in err
    assert ledger.limits() == []


# --- stop --------------------------------------------------------------------


def test_stopping_a_run_nobody_is_driving_writes_the_state(machine, capsys, tmp_path):
    run(["run", "new", "add-vat", "--steps", "probe"], capsys)

    code, out, _ = run(["run", "stop", "add-vat", "the owner said so"], capsys)

    assert code == ExitCode.OK
    state = json.loads((tmp_path / "project/.agent-kit/v3/runs/add-vat/run.json").read_text())
    assert state["status"] == "stopped"


def test_stopping_a_run_a_driver_holds_posts_it_where_the_driver_reads_it(machine, ledger, capsys, tmp_path):
    run(["run", "new", "add-vat", "--steps", "probe"], capsys)
    ledger.hold_run(str((tmp_path / "project").resolve()), "add-vat", pid=1)

    code, out, _ = run(["run", "stop", "add-vat", "the owner said so"], capsys)

    assert code == ExitCode.OK
    assert "driver" in out
    state = json.loads((tmp_path / "project/.agent-kit/v3/runs/add-vat/run.json").read_text())
    assert state["status"] == "created", "the state was written under a driver that is still writing it"
    assert ledger.stop_asked(str((tmp_path / "project").resolve()), "add-vat") == "the owner said so"


# --- the page ----------------------------------------------------------------


def test_the_page_shows_what_the_ledger_holds(machine, ledger):
    from agent_kit.daemon import page

    ledger.take(Want(account="anthropic", provider="claude_code", project="/p", slug="one", step="build"),
                _four())

    html = page(ledger)

    assert "one" in html and "claude_code" in html
    assert "<html" in html.lower()


def test_the_page_has_nothing_to_press(machine, ledger):
    """Read-only until somebody asks for more: every button is a way to break a night."""
    from agent_kit.daemon import page

    html = page(ledger).lower()

    assert "<form" not in html and "<button" not in html


def test_what_the_page_polls_is_the_picture_and_nothing_else(machine, ledger):
    from agent_kit.daemon import as_json

    ledger.wants_one(Want(account="anthropic", provider="claude_code", project="/p", slug="two", step="build"))

    answered = json.loads(as_json(ledger))

    assert [row["slug"] for row in answered["queue"]] == ["two"]
    assert answered["held"] == [] and answered["limits"] == []


def test_the_daemon_says_where_it_would_answer(machine, capsys):
    code, out, _ = run(["daemon", "status"], capsys)

    assert code == ExitCode.OK
    assert "8080" in out


def test_the_unit_starts_the_daemon_this_machine_has(machine, capsys, tmp_path):
    code, out, _ = run(["daemon", "install"], capsys)

    assert code == ExitCode.OK
    unit = (tmp_path / "home/.config/systemd/user/agent-kit.service").read_text()
    assert "daemon start" in unit
    assert "systemctl --user enable" in out


def _four():
    from agent_kit.machine import Ceilings

    return Ceilings(max_sessions=4)
