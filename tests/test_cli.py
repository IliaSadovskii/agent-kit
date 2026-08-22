"""S0 — the command surface and the exit codes. Each code means one thing."""

import json

import pytest

from agent_kit import __version__
from agent_kit.cli.main import main
from agent_kit.errors import ExitCode


@pytest.fixture
def machine(tmp_path, monkeypatch, machine_home):
    """A home of its own (from conftest) and a project directory to stand in."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
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
    assert run(["run", "new", "add-login", "--steps", "probe"], capsys)[0] == ExitCode.OK

    assert run(["run", "start", "add-login"], capsys)[0] == ExitCode.OK
    assert run(["run", "pass", "add-login"], capsys)[0] == ExitCode.OK

    code, out, _ = run(["run", "show", "add-login", "--json"], capsys)
    state = json.loads(out)

    assert code == ExitCode.OK
    assert state["slug"] == "add-login"
    assert state["branch"] == "kit/add-login"
    assert state["steps"][0]["status"] == "passed"


def test_run_list_shows_what_the_project_holds(machine, capsys):
    run(["run", "new", "add-login", "--steps", "probe"], capsys)
    run(["run", "new", "fix-clock", "--steps", "probe"], capsys)

    code, out, _ = run(["run", "list"], capsys)

    assert code == ExitCode.OK
    assert "add-login" in out and "fix-clock" in out


def test_an_unknown_run_is_a_state_error_with_a_named_reason(machine, capsys):
    code, _, err = run(["run", "show", "nonesuch"], capsys)

    assert code == ExitCode.STATE
    assert "unknown-run" in err


def test_passing_a_step_that_never_started_is_refused(machine, capsys):
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, _, err = run(["run", "pass", "add-login"], capsys)

    assert code == ExitCode.STATE
    assert "no-step-running" in err


# --- the step commands -----------------------------------------------------


def test_step_list_names_what_the_kit_can_run(machine, capsys):
    code, out, _ = run(["step", "list"], capsys)

    assert code == ExitCode.OK
    assert "probe" in out


def test_step_show_prints_the_contract(machine, capsys):
    code, out, _ = run(["step", "show", "probe"], capsys)

    assert code == ExitCode.OK
    assert "branch" in out and "can_write" in out


def test_step_show_refuses_a_step_nobody_declared(machine, capsys):
    code, _, err = run(["step", "show", "nonesuch"], capsys)

    assert code == ExitCode.STATE
    assert "unknown-step" in err


def test_a_run_cannot_be_created_from_a_step_that_does_not_exist(machine, capsys):
    code, _, err = run(["run", "new", "add-login", "--steps", "probe,nonesuch"], capsys)

    assert code == ExitCode.STATE
    assert "unknown-step" in err


def test_step_input_composes_what_would_be_enclosed(machine, capsys):
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, out, _ = run(["step", "input", "add-login"], capsys)

    assert code == ExitCode.OK
    assert "kit/add-login" in out
    assert "```json" in out
    assert "can_write" in out


def test_step_run_against_the_fake_provider(machine, capsys, tmp_path):
    reply = tmp_path / "reply.md"
    reply.write_text('```json\n{"branch": "kit/add-login", "can_write": true}\n```', encoding="utf-8")
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, out, _ = run(["step", "run", "add-login", "--provider", "fake", "--option", f"reply={reply}"], capsys)

    assert code == ExitCode.OK
    assert "probe passed" in out
    assert json.loads(
        (tmp_path / "project/.agent-kit/v3/runs/add-login/steps/0-probe/output.json").read_text()
    )["branch"] == "kit/add-login"


def test_step_run_reports_a_refusal_and_leaves_the_step_unpassed(machine, capsys, tmp_path):
    reply = tmp_path / "reply.md"
    reply.write_text("I had a look and it seems fine.", encoding="utf-8")
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, out, err = run(["step", "run", "add-login", "--provider", "fake", "--option", f"reply={reply}"], capsys)

    assert code == ExitCode.STATE
    assert "output-not-json" in out
    assert "refused" in err
    assert run(["run", "show", "add-login", "--json"], capsys)[1].count('"passed"') == 0


def test_a_provider_the_kit_does_not_ship_is_refused_before_anything_runs(machine, capsys):
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, _, err = run(["step", "run", "add-login", "--provider", "codex"], capsys)

    assert code == ExitCode.PROVIDER
    assert "unknown-provider" in err


def test_provider_list_reads_the_folder(machine, capsys):
    code, out, _ = run(["provider", "list"], capsys)

    assert code == ExitCode.OK
    assert "fake" in out
    assert "fixture" in out


def test_a_step_run_with_no_provider_at_all_is_refused(machine, capsys):
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, _, err = run(["step", "run", "add-login"], capsys)

    assert code == ExitCode.PROVIDER
    assert "no-provider" in err or "unknown-provider" in err


def test_an_explicit_provider_beats_the_role_table(machine, capsys, tmp_path):
    """The person typed a provider. Configuration does not overrule what was asked for."""
    config = machine / "home/.config/agent-kit/config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('[roles.probe]\nprovider = "claude_code"\n', encoding="utf-8")
    reply = tmp_path / "reply.md"
    reply.write_text('```json\n{"branch": "kit/x", "can_write": true}\n```', encoding="utf-8")
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, out, _ = run(
        ["step", "run", "add-login", "--provider", "fake", "--option", f"reply={reply}"], capsys
    )

    assert code == ExitCode.OK
    assert "probe passed" in out


def test_step_input_refuses_a_run_that_is_over(machine, capsys):
    run(["run", "new", "add-login", "--steps", "probe"], capsys)
    run(["run", "start", "add-login"], capsys)
    run(["run", "fail", "add-login", "gave up"], capsys)

    code, _, err = run(["step", "input", "add-login"], capsys)

    assert code == ExitCode.STATE
    assert "run-finished" in err


@pytest.mark.parametrize(
    "option, reason",
    [("reply", "bad-option"), ("=value", "bad-option"), ("reply=/nowhere/at/all", "no-reply")],
)
def test_a_bad_option_is_refused_by_name(machine, capsys, option, reason):
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, _, err = run(["step", "run", "add-login", "--provider", "fake", "--option", option], capsys)

    assert code in (ExitCode.USAGE, ExitCode.PROVIDER)
    assert reason in err


def test_an_option_value_may_contain_the_separator(machine, capsys, tmp_path):
    reply = tmp_path / "a=b.md"
    reply.write_text('```json\n{"branch": "kit/x", "can_write": true}\n```', encoding="utf-8")
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    code, _, _ = run(
        ["step", "run", "add-login", "--provider", "fake", "--option", f"reply={reply}"], capsys
    )

    assert code == ExitCode.OK


def test_run_show_says_what_a_step_cost_and_how_full_the_session_got(machine, capsys, tmp_path):
    """Every field the driver writes has a reader, and this is it."""
    reply = tmp_path / "reply.md"
    reply.write_text('```json\n{"branch": "kit/x", "can_write": true}\n```', encoding="utf-8")
    run(["run", "new", "add-login", "--steps", "probe"], capsys)
    run(["step", "run", "add-login", "--provider", "fake", "--option", f"reply={reply}"], capsys)

    meta = tmp_path / "project/.agent-kit/v3/runs/add-login/steps/0-probe/meta.json"
    meta.write_text(json.dumps({
        "provider": "fake", "attempt": 1, "step": "probe", "model": "fake-script",
        "session": "s-1", "cost_usd": 0.12, "context_used": 27249, "context_window": 1000000,
        "duration_ms": 1737,
    }), encoding="utf-8")

    code, out, _ = run(["run", "show", "add-login"], capsys)

    assert code == ExitCode.OK
    assert "0.12" in out
    assert "27,249" in out or "27249" in out
    assert "fake-script" in out


def test_provider_list_says_whether_a_level_was_ever_measured(machine, capsys):
    code, out, _ = run(["provider", "list"], capsys)

    assert code == ExitCode.OK
    assert "not measured" in out


def test_the_configuration_reaches_the_provider_it_configures(machine, capsys, tmp_path):
    """`config.toml` answers what `provider.toml` asks. An answer nobody passes on is not an answer."""
    config = machine / "home/.config/agent-kit/config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        '[providers.claude_code]\nmodel = "opus"\neffort = "high"\n'
        '[roles.probe]\nprovider = "claude_code"\n',
        encoding="utf-8",
    )
    run(["run", "new", "add-login", "--steps", "probe"], capsys)

    from agent_kit.cli.main import _runner
    from agent_kit.state import RunStore
    from agent_kit.steps import builtin_registry

    runner = _runner(RunStore(tmp_path / "project"), builtin_registry(), provider=None, options=[])

    assert runner.executors["claude_code"].model == "opus"
    assert runner.executors["claude_code"].effort == "high"


# --- S4: a run of a feature says which feature ------------------------------


def test_a_run_that_says_nothing_else_is_a_whole_feature(machine, capsys, tmp_path):
    code, out, _ = run(["run", "new", "add-vat", "--brief", "Money should know about VAT"], capsys)

    assert code == ExitCode.OK
    state = json.loads(run(["run", "show", "add-vat", "--json"], capsys)[1])
    assert [step["name"] for step in state["steps"]] == ["design", "build", "verify", "review", "deliver"]
    assert state["brief"] == "Money should know about VAT"


def test_a_feature_with_no_brief_is_refused_before_anything_runs(machine, capsys):
    code, _, err = run(["run", "new", "add-vat"], capsys)

    assert code == ExitCode.STATE
    assert "no-brief" in err


def test_run_show_says_what_the_run_is_for(machine, capsys):
    run(["run", "new", "add-vat", "--brief", "Money should know about VAT"], capsys)

    code, out, _ = run(["run", "show", "add-vat"], capsys)

    assert code == ExitCode.OK
    assert "Money should know about VAT" in out


# --- S4: driving a whole run ------------------------------------------------


DESIGN_REPLY = json.dumps(
    {
        "title": "Money learns a VAT rate",
        "summary": "Money learns a VAT rate.",
        "changes": ["money.py — with_vat"],
        "seams": ["Money is frozen"],
        "verification": ["1000 at 20% is 1200"],
        "needs_owner": [],
        "assumptions": [],
    }
)
BUILD_REPLY = json.dumps(
    {"complete": True, "summary": "Done.", "files": ["money.py"], "tests": ["test_vat"], "deviations": []}
)


def scripted(tmp_path, *bodies):
    """The fake provider answers from files, one per attempt."""
    options = []
    for number, body in enumerate(bodies):
        path = tmp_path / f"reply-{number}.json"
        path.write_text("```json\n" + body + "\n```", encoding="utf-8")
        options += ["--option", f"reply={path}"]
    return options


def declare(tmp_path, text):
    path = tmp_path / "project/.agent-kit/v3/project.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_run_go_walks_every_step_to_the_end(machine, capsys, tmp_path):
    declare(tmp_path, '[commands]\ntest = "true"\n')
    run(["run", "new", "add-vat", "--brief", "VAT", "--steps", "design,build,verify"], capsys)

    code, out, _ = run(
        ["run", "go", "add-vat", "--provider", "fake", *scripted(tmp_path, DESIGN_REPLY, BUILD_REPLY)],
        capsys,
    )

    assert code == ExitCode.OK
    assert "design passed" in out and "build passed" in out and "verify passed" in out
    assert json.loads(run(["run", "show", "add-vat", "--json"], capsys)[1])["status"] == "done"


def test_run_go_stops_at_the_step_that_would_not_pass(machine, capsys, tmp_path):
    declare(tmp_path, '[commands]\ntest = "exit 1"\n')
    run(["run", "new", "add-vat", "--brief", "VAT", "--steps", "design,build,verify"], capsys)

    code, out, err = run(
        ["run", "go", "add-vat", "--provider", "fake", *scripted(tmp_path, DESIGN_REPLY, BUILD_REPLY)],
        capsys,
    )

    assert code == ExitCode.REFUSED
    assert "verify" in err
    assert json.loads(run(["run", "show", "add-vat", "--json"], capsys)[1])["status"] == "stopped"


def test_run_go_refuses_a_run_that_is_already_over(machine, capsys, tmp_path):
    run(["run", "new", "add-vat", "--brief", "VAT", "--steps", "probe"], capsys)
    run(["run", "stop", "add-vat", "the owner said so"], capsys)

    code, _, err = run(["run", "go", "add-vat", "--provider", "fake"], capsys)

    assert code == ExitCode.STATE
    assert "run-finished" in err


def test_the_programs_are_always_there_whatever_the_role_table_says(machine, capsys, tmp_path):
    declare(tmp_path, '[commands]\ntest = "true"\n')
    run(["run", "new", "add-vat", "--brief", "VAT", "--steps", "verify"], capsys)

    code, out, _ = run(["run", "go", "add-vat"], capsys)

    assert code == ExitCode.OK
    assert "verify passed" in out


def test_a_project_may_say_which_provider_runs_a_role_here(machine, capsys, tmp_path):
    declare(tmp_path, '[commands]\ntest = "true"\n\n[roles.design]\nprovider = "fake"\n')
    run(["run", "new", "add-vat", "--brief", "VAT", "--steps", "design"], capsys)

    code, out, _ = run(["run", "go", "add-vat", *scripted(tmp_path, DESIGN_REPLY)], capsys)

    assert code == ExitCode.OK
    assert "design passed" in out


def test_a_run_the_method_refused_is_stopped_and_not_failed(machine, capsys, tmp_path):
    """A red suite is what the method is for, not a sign the kit broke."""
    declare(tmp_path, '[commands]\ntest = "exit 1"\n')
    run(["run", "new", "add-vat", "--brief", "VAT", "--steps", "design,build,verify"], capsys)

    code, _, err = run(
        ["run", "go", "add-vat", "--provider", "fake", *scripted(tmp_path, DESIGN_REPLY, BUILD_REPLY)],
        capsys,
    )

    assert code == ExitCode.REFUSED
    assert "verify" in err
    state = json.loads(run(["run", "show", "add-vat", "--json"], capsys)[1])
    assert state["status"] == "stopped"
    assert state["steps"][2]["status"] == "passed"  # verify did its work: it recorded the truth
    assert "passed" in state["reason"]


def test_a_provider_that_will_not_answer_still_fails_the_run(machine, capsys, tmp_path):
    """The other half of the same distinction: this one really is a breakage."""
    run(["run", "new", "add-vat", "--brief", "VAT", "--steps", "design"], capsys)

    code, _, err = run(
        ["run", "go", "add-vat", "--provider", "fake", *scripted(tmp_path, "not json at all")], capsys
    )

    assert code == ExitCode.STATE
    assert json.loads(run(["run", "show", "add-vat", "--json"], capsys)[1])["status"] == "failed"
