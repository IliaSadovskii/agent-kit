"""S0 — the command surface and the exit codes. Each code means one thing."""

import json

import pytest

from agent_kit import __version__
from agent_kit.cli.main import main
from agent_kit.errors import ExitCode


@pytest.fixture
def machine(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.chdir(tmp_path / "project")
    return tmp_path


@pytest.fixture(autouse=True)
def project(tmp_path):
    (tmp_path / "project").mkdir(parents=True, exist_ok=True)


def run(argv, capsys):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_version(machine, capsys):
    code, out, _ = run(["--version"], capsys)

    assert code == ExitCode.OK
    assert __version__ in out


def test_help_answers(machine, capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--help"])

    assert caught.value.code == ExitCode.OK
    assert "agent-kit" in capsys.readouterr().out


def test_no_command_is_a_usage_error(machine, capsys):
    code, _, err = run([], capsys)

    assert code == ExitCode.USAGE
    assert "command" in err.lower()


def test_an_unknown_command_is_a_usage_error(machine, capsys):
    with pytest.raises(SystemExit) as caught:
        main(["nonesuch"])

    assert caught.value.code == ExitCode.USAGE


def test_doctor_reports_the_paths_and_says_what_is_missing(machine, capsys):
    code, out, _ = run(["doctor"], capsys)

    assert code == ExitCode.OK
    assert str(machine / "home/.config/agent-kit/config.toml") in out
    assert "missing" in out


def test_doctor_refuses_a_broken_config_with_its_reason(machine, capsys):
    config = machine / "home/.config/agent-kit/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text("[machine]\nmax_sessions = 0\n", encoding="utf-8")

    code, _, err = run(["doctor"], capsys)

    assert code == ExitCode.CONFIG
    assert "machine.max_sessions" in err


def test_config_show_prints_the_effective_configuration(machine, capsys):
    code, out, _ = run(["config", "show"], capsys)

    assert code == ExitCode.OK
    assert "max_sessions" in out


def test_a_run_is_created_advanced_and_read_back(machine, capsys):
    assert run(["run", "new", "add-login"], capsys)[0] == ExitCode.OK

    assert run(["run", "start", "add-login"], capsys)[0] == ExitCode.OK
    assert run(["run", "pass", "add-login"], capsys)[0] == ExitCode.OK

    code, out, _ = run(["run", "show", "add-login", "--json"], capsys)
    state = json.loads(out)

    assert code == ExitCode.OK
    assert state["slug"] == "add-login"
    assert state["branch"] == "kit/add-login"
    assert state["steps"][0]["status"] == "passed"


def test_run_list_shows_what_the_project_holds(machine, capsys):
    run(["run", "new", "add-login"], capsys)
    run(["run", "new", "fix-clock"], capsys)

    code, out, _ = run(["run", "list"], capsys)

    assert code == ExitCode.OK
    assert "add-login" in out and "fix-clock" in out


def test_an_unknown_run_is_a_state_error_with_a_named_reason(machine, capsys):
    code, _, err = run(["run", "show", "nonesuch"], capsys)

    assert code == ExitCode.STATE
    assert "unknown-run" in err


def test_passing_a_step_that_never_started_is_refused(machine, capsys):
    run(["run", "new", "add-login"], capsys)

    code, _, err = run(["run", "pass", "add-login"], capsys)

    assert code == ExitCode.STATE
    assert "no-step-running" in err
