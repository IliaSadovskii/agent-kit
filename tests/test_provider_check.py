"""S3 — a provider's level is measured, not declared.

`provider check` climbs a ladder and says which rung failed. A level nobody
measured is the same class of claim as a rule nobody tested.
"""

import json
import stat

import pytest

from agent_kit.driver.check import RUNGS, check_provider

ANSWER = {
    "type": "result",
    "is_error": False,
    "result": '```json\n{"branch": "kit/x", "can_write": true, "notes": ["clean tree"]}\n```',
    "session_id": "11111111-2222-3333-4444-555555555555",
    "total_cost_usd": 0.04,
    "usage": {"input_tokens": 2, "cache_read_input_tokens": 16091, "output_tokens": 4},
    "modelUsage": {"claude-sonnet-5": {"contextWindow": 1000000}},
}


def _rung(report, name):
    return next(rung for rung in report.rungs if rung.name == name)


def claude_that(tmp_path, body: str):
    path = tmp_path / "claude"
    path.write_text(f"#!/bin/sh\ncat > /dev/null\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return {"binary": [str(path)]}


def answering(tmp_path, answer=None):
    (tmp_path / "answer.json").write_text(json.dumps(answer or ANSWER), encoding="utf-8")
    return claude_that(tmp_path, f'if [ "$1" = "--version" ]; then echo "2.1.239 (Claude Code)"; '
                                 f"else cat {tmp_path}/answer.json; fi")


def test_every_rung_is_climbed_and_the_level_is_b(tmp_path, monkeypatch):
    _transcript(tmp_path, monkeypatch)

    report = check_provider("claude_code", answering(tmp_path), project=tmp_path)

    assert report.level == "B"
    assert [rung.name for rung in report.rungs] == list(RUNGS)
    assert all(rung.passed for rung in report.rungs)
    assert report.failed is None


def _transcript(tmp_path, monkeypatch, used=None):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    folder = home / ".claude/projects" / str(tmp_path.resolve()).replace("/", "-")
    folder.mkdir(parents=True, exist_ok=True)
    usage = used or {"input_tokens": 2, "cache_read_input_tokens": 16091, "output_tokens": 4}
    (folder / f"{ANSWER['session_id']}.jsonl").write_text(
        json.dumps({"type": "assistant", "message": {"usage": usage}}) + "\n", encoding="utf-8"
    )


def test_the_login_is_a_rung_of_its_own(tmp_path, monkeypatch):
    """A logged-out CLI answers --version perfectly well. That is not a login."""
    _transcript(tmp_path, monkeypatch)
    options = claude_that(
        tmp_path,
        'if [ "$1" = "--version" ]; then echo "2.1.239"; else '
        'echo "Invalid API key · Please run /login" >&2; exit 1; fi',
    )

    report = check_provider("claude_code", options, project=tmp_path)

    assert report.failed == "login"
    assert report.level is None
    assert "login" in _rung(report, "login").detail.lower()


def test_whether_a_limit_could_be_read_is_measured_too(tmp_path, monkeypatch):
    """Level B is context AND the limit. A provider that cannot read one is not B."""
    _transcript(tmp_path, monkeypatch)

    report = check_provider("claude_code", answering(tmp_path), project=tmp_path)

    limits = next(rung for rung in report.rungs if rung.name == "limits")
    assert limits.passed
    assert "reset" in limits.detail or "limit" in limits.detail


def test_a_rung_a_provider_cannot_be_asked_is_not_a_rung_it_climbed(tmp_path):
    """The fake has no binary and no version. Those are not passes."""
    reply = tmp_path / "reply.md"
    reply.write_text('```json\n{"branch": "kit/x", "can_write": true}\n```', encoding="utf-8")

    report = check_provider("fake", {"reply": [str(reply)]}, project=tmp_path)

    binary = next(rung for rung in report.rungs if rung.name == "binary")
    assert binary.applies is False
    assert binary.passed is False  # not applicable is not passed


def test_the_context_it_measured_is_in_the_report(tmp_path, monkeypatch):
    _transcript(tmp_path, monkeypatch)

    report = check_provider("claude_code", answering(tmp_path), project=tmp_path)

    assert report.facts.context_used == 2 + 16091 + 4
    assert report.facts.context_window == 1_000_000


def test_a_binary_that_is_not_there_fails_the_first_rung(tmp_path):
    report = check_provider("claude_code", {"binary": [str(tmp_path / "nowhere")]}, project=tmp_path)

    assert report.level is None
    assert report.failed == "binary"
    assert not report.rungs[0].passed


def test_what_was_measured_is_written_down_and_read_back(tmp_path, monkeypatch):
    """A level that is printed and thrown away is a claim again by morning."""
    from agent_kit.providers.measured import measured_levels

    _transcript(tmp_path, monkeypatch)
    check_provider("claude_code", answering(tmp_path), project=tmp_path, remember=True)

    remembered = measured_levels()

    assert remembered["claude_code"].level == "B"
    assert remembered["claude_code"].measured_at


def test_a_cli_that_does_not_answer_fails_the_second(tmp_path):
    options = claude_that(tmp_path, 'echo "broken" >&2; exit 1')

    report = check_provider("claude_code", options, project=tmp_path)

    assert report.failed == "answers"
    assert "broken" in _rung(report, "answers").detail


def test_a_one_shot_job_that_returns_nothing_useful_fails_the_third(tmp_path):
    options = claude_that(
        tmp_path,
        'if [ "$1" = "--version" ]; then echo "2.1.239"; else echo "I would rather not"; fi',
    )

    report = check_provider("claude_code", options, project=tmp_path)

    assert report.failed == "one_shot"
    assert report.level is None


def test_an_answer_that_misses_the_contract_earns_level_a_not_b(tmp_path, monkeypatch):
    """It started, it answered — that is level A. B needs the contract kept."""
    _transcript(tmp_path, monkeypatch)
    loose = dict(ANSWER, result='```json\n{"can_write": true}\n```')

    report = check_provider("claude_code", answering(tmp_path, loose), project=tmp_path)

    assert report.level == "A"
    assert report.failed == "contract"
    assert "branch" in _rung(report, "contract").detail


def test_a_provider_that_cannot_say_how_much_context_is_level_a(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))  # no transcript to read
    blind = {key: value for key, value in ANSWER.items() if key not in ("usage", "modelUsage")}

    report = check_provider("claude_code", answering(tmp_path, blind), project=tmp_path)

    assert report.level == "A"
    assert report.failed == "observed"


def test_the_fake_provider_is_checkable_too(tmp_path):
    reply = tmp_path / "reply.md"
    reply.write_text('```json\n{"branch": "kit/x", "can_write": true}\n```', encoding="utf-8")

    report = check_provider("fake", {"reply": [str(reply)]}, project=tmp_path)

    assert report.level == "A"  # it answers, and it knows nothing about context
    assert report.failed == "observed"


def test_a_provider_that_cannot_even_be_built_is_a_report_not_a_traceback(tmp_path):
    report = check_provider("fake", {}, project=tmp_path)  # the fake needs a reply= and got none

    assert report.level is None
    assert report.failed == "binary"
    assert "no-reply" in _rung(report, "binary").detail


def test_checking_leaves_nothing_behind_in_the_project(tmp_path, monkeypatch):
    _transcript(tmp_path, monkeypatch)
    options = answering(tmp_path)
    before = sorted(entry.name for entry in tmp_path.iterdir())

    check_provider("claude_code", options, project=tmp_path)

    assert sorted(entry.name for entry in tmp_path.iterdir()) == before


def test_a_provider_the_kit_does_not_ship_is_refused(tmp_path):
    """Demonstrated with a name the kit will not ship tomorrow. It was `codex`,
    and S9 ships it: a test whose subject walks into the catalogue stops asking
    its question on the day the catalogue grows."""
    from agent_kit.errors import ProviderError

    with pytest.raises(ProviderError) as caught:
        check_provider("a-tool-nobody-wrote", {}, project=tmp_path)

    assert caught.value.code == "unknown-provider"


# --- the command surface --------------------------------------------------


def cli(argv, capsys, project):
    from agent_kit.cli.main import main

    code = main(["-C", str(project), *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_command_prints_the_ladder_and_the_level(tmp_path, capsys, monkeypatch):
    _transcript(tmp_path, monkeypatch)
    binary = answering(tmp_path)["binary"][0]

    code, out, _ = cli(
        ["provider", "check", "claude_code", "--option", f"binary={binary}"], capsys, tmp_path
    )

    assert code == 0
    assert "level B" in out
    for rung in RUNGS:
        assert rung in out
    assert "context" in out


def test_the_command_says_which_rung_failed(tmp_path, capsys):
    code, _, err = cli(
        ["provider", "check", "claude_code", "--option", f"binary={tmp_path / 'nowhere'}"], capsys, tmp_path
    )

    assert code == 4
    # The code and the rung's own name, not the sentence around them: this test
    # measured the prose, and the prose was rewritten the day the refusal got a
    # code — which is the thing the project's own rule is about.
    assert "provider-not-ready" in err
    assert "binary" in err


def test_a_provider_that_earns_less_than_it_declares_is_reported(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    blind = {key: value for key, value in ANSWER.items() if key not in ("usage", "modelUsage")}
    binary = answering(tmp_path, blind)["binary"][0]

    code, out, err = cli(
        ["provider", "check", "claude_code", "--option", f"binary={binary}"], capsys, tmp_path
    )

    assert code == 4
    assert "level A" in out
    assert "declares level B" in err


# --- S9a: the second free rung, for every provider that declares the flag ----


def _declare(tmp_path, monkeypatch, name, text):
    from agent_kit.providers import registry

    folder = tmp_path / "providers" / name
    folder.mkdir(parents=True)
    (folder / "provider.toml").write_text(text, encoding="utf-8")
    monkeypatch.setattr(registry, "PROVIDERS_DIR", tmp_path / "providers")


def test_a_level_a_provider_with_a_version_flag_climbs_the_rung(tmp_path, monkeypatch):
    """`version()` used to live in the level-B adapter alone, so *the two free
    rungs are climbed for everyone* was false for every provider declared by a
    `provider.toml` and nothing else — which is what S9 adds three of."""
    binary = tmp_path / "newcomer"
    binary.write_text("#!/bin/sh\necho 'newcomer 1.2.3'\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    _declare(
        tmp_path, monkeypatch, "newcomer",
        '[provider]\nbinary = "newcomer"\n\n[provider.flags]\nversion = ["--version"]\n',
    )

    report = check_provider("newcomer", {"binary": [str(binary)]}, project=tmp_path)

    assert _rung(report, "binary").passed
    answers = _rung(report, "answers")
    assert answers.passed and "newcomer 1.2.3" in answers.detail


def test_a_provider_with_no_version_flag_is_not_asked_rather_than_failed(tmp_path, monkeypatch):
    """A rung nobody can climb is neither passed nor failed. Failing it here
    would drop a working provider below level A for a flag it never declared."""
    binary = tmp_path / "quiet"
    binary.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    _declare(tmp_path, monkeypatch, "quiet", '[provider]\nbinary = "quiet"\n')

    report = check_provider("quiet", {"binary": [str(binary)]}, project=tmp_path)

    answers = _rung(report, "answers")
    assert answers.applies is False
    assert answers.passed is False
    assert answers.held is True


def test_a_ladder_that_stopped_names_a_code_and_not_only_prose(tmp_path, monkeypatch, capsys):
    """A judge reads a code. `provider check` printed which rung failed in a
    sentence and no code at all, while the walk refuses the same state by name."""
    from agent_kit.cli.main import main
    from agent_kit.errors import ExitCode

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    code = main(["provider", "check", "claude_code", "--option", f"binary={tmp_path / 'nowhere'}"])
    said = capsys.readouterr()

    assert code == ExitCode.PROVIDER
    assert "provider-not-ready" in said.err


# --- the rung the probe was already measuring and nobody read ----------------


def test_a_session_that_cannot_write_does_not_earn_level_a(tmp_path, monkeypatch):
    """`can_write` is what the probe goes and finds out, and nothing read it.

    S9 makes it reachable: `codex exec` sandboxes to read-only unless it is told
    otherwise, so a declaration that forgets the sandbox flag gives a provider
    that starts, answers, keeps the contract — and cannot edit a file. Without
    this rung the ladder called that level A and the owner found out at the
    build step of a night.
    """
    _transcript(tmp_path, monkeypatch)
    walled = dict(ANSWER, result='```json\n{"branch": "kit/x", "can_write": false}\n```')

    report = check_provider("claude_code", answering(tmp_path, walled), project=tmp_path)

    assert report.failed == "writes"
    assert report.level is None
    assert _rung(report, "contract").passed  # it answered perfectly well


def test_a_provider_whose_answer_could_not_be_read_is_not_asked_whether_it_writes(tmp_path, monkeypatch):
    """A rung nobody could climb is not a rung anybody failed — and the level
    an unreadable answer earns is the one it earned before this rung existed."""
    _transcript(tmp_path, monkeypatch)
    loose = dict(ANSWER, result='```json\n{"can_write": true}\n```')  # no branch: contract fails

    report = check_provider("claude_code", answering(tmp_path, loose), project=tmp_path)

    writes = _rung(report, "writes")
    assert writes.applies is False
    assert writes.held is True
    assert report.level == "A"


def test_a_choice_the_machine_made_is_not_a_rung_of_the_providers_ladder(tmp_path, monkeypatch):
    """`effort-not-selectable` is the machine's configuration being wrong, and
    exit code 4 means *an agent cannot be run right now*. Burying it in the
    `binary` rung said the binary was missing, which was not true."""
    from agent_kit.errors import ConfigError

    binary = tmp_path / "newcomer"
    binary.write_text("#!/bin/sh\necho 'newcomer 1.2.3'\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    _declare(tmp_path, monkeypatch, "newcomer",
             '[provider]\nbinary = "newcomer"\n\n[provider.flags]\nversion = ["--version"]\n')

    with pytest.raises(ConfigError) as caught:
        check_provider("newcomer", {"binary": [str(binary)], "effort": ["high"]}, project=tmp_path)

    assert caught.value.code == "effort-not-selectable"
