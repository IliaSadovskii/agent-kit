"""S3 — a provider's level is measured, not declared.

`provider check` climbs a ladder and says which rung failed. A level nobody
measured is the same class of claim as a rule nobody tested.
"""

import json
import stat

import pytest

from agent_kit.providers.check import RUNGS, check_provider

ANSWER = {
    "type": "result",
    "is_error": False,
    "result": '```json\n{"branch": "kit/x", "can_write": true, "notes": ["clean tree"]}\n```',
    "session_id": "11111111-2222-3333-4444-555555555555",
    "total_cost_usd": 0.04,
    "usage": {"input_tokens": 2, "cache_read_input_tokens": 16091, "output_tokens": 4},
    "modelUsage": {"claude-sonnet-5": {"contextWindow": 1000000}},
}


def claude_that(tmp_path, body: str):
    path = tmp_path / "claude"
    path.write_text(f"#!/bin/sh\ncat > /dev/null\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return {"binary": [str(path)]}


def answering(tmp_path, answer=None):
    (tmp_path / "answer.json").write_text(json.dumps(answer or ANSWER), encoding="utf-8")
    return claude_that(tmp_path, f'if [ "$1" = "--version" ]; then echo "2.1.239 (Claude Code)"; '
                                 f"else cat {tmp_path}/answer.json; fi")


def test_every_rung_is_climbed_and_the_level_is_b(tmp_path):
    report = check_provider("claude_code", answering(tmp_path), project=tmp_path)

    assert report.level == "B"
    assert [rung.name for rung in report.rungs] == list(RUNGS)
    assert all(rung.passed for rung in report.rungs)
    assert report.failed is None


def test_the_context_it_measured_is_in_the_report(tmp_path):
    report = check_provider("claude_code", answering(tmp_path), project=tmp_path)

    assert report.facts.context_used == 2 + 16091 + 4
    assert report.facts.context_window == 1_000_000


def test_a_binary_that_is_not_there_fails_the_first_rung(tmp_path):
    report = check_provider("claude_code", {"binary": [str(tmp_path / "nowhere")]}, project=tmp_path)

    assert report.level is None
    assert report.failed == "binary"
    assert not report.rungs[0].passed


def test_a_cli_that_does_not_answer_fails_the_second(tmp_path):
    options = claude_that(tmp_path, 'echo "broken" >&2; exit 1')

    report = check_provider("claude_code", options, project=tmp_path)

    assert report.failed == "answers"
    assert "broken" in report.rungs[1].detail


def test_a_one_shot_job_that_returns_nothing_useful_fails_the_third(tmp_path):
    options = claude_that(
        tmp_path,
        'if [ "$1" = "--version" ]; then echo "2.1.239"; else echo "I would rather not"; fi',
    )

    report = check_provider("claude_code", options, project=tmp_path)

    assert report.failed == "one_shot"
    assert report.level is None


def test_an_answer_that_misses_the_contract_earns_level_a_not_b(tmp_path):
    """It started, it answered — that is level A. B needs the contract kept."""
    loose = dict(ANSWER, result='```json\n{"can_write": true}\n```')

    report = check_provider("claude_code", answering(tmp_path, loose), project=tmp_path)

    assert report.level == "A"
    assert report.failed == "contract"
    assert "branch" in report.rungs[3].detail


def test_a_provider_that_cannot_say_how_much_context_is_level_a(tmp_path):
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


def test_checking_leaves_nothing_behind_in_the_project(tmp_path):
    check_provider("claude_code", answering(tmp_path), project=tmp_path)

    assert not (tmp_path / ".agent-kit").exists()


def test_a_provider_the_kit_does_not_ship_is_refused(tmp_path):
    from agent_kit.errors import ProviderError

    with pytest.raises(ProviderError) as caught:
        check_provider("codex", {}, project=tmp_path)

    assert caught.value.code == "unknown-provider"


# --- the command surface --------------------------------------------------


def cli(argv, capsys, project):
    from agent_kit.cli.main import main

    code = main(["-C", str(project), *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_command_prints_the_ladder_and_the_level(tmp_path, capsys):
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
    assert "failed at binary" in err


def test_a_provider_that_earns_less_than_it_declares_is_reported(tmp_path, capsys):
    blind = {key: value for key, value in ANSWER.items() if key not in ("usage", "modelUsage")}
    binary = answering(tmp_path, blind)["binary"][0]

    code, out, err = cli(
        ["provider", "check", "claude_code", "--option", f"binary={binary}"], capsys, tmp_path
    )

    assert code == 4
    assert "level A" in out
    assert "declares level B" in err
