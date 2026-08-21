"""S3 — the first real adapter, driven against a `claude` that is a shell script.

Everything here runs with no agent CLI installed and no network: the adapter's
contract with Claude Code is "run this binary, give it this input, read this
JSON", and a script can hold up that end.
"""

import json
import os
import stat

import pytest

from agent_kit.driver.executor import StepRequest
from agent_kit.providers import registry
from agent_kit.providers.base import ExecutorFailed

ANSWER = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": '```json\n{"branch": "kit/add-login", "can_write": true}\n```',
    "session_id": "11111111-2222-3333-4444-555555555555",
    "total_cost_usd": 0.041,
    "duration_ms": 1737,
    "num_turns": 1,
    "usage": {
        "input_tokens": 2,
        "cache_creation_input_tokens": 9538,
        "cache_read_input_tokens": 16091,
        "output_tokens": 4,
    },
    "modelUsage": {"claude-sonnet-5": {"contextWindow": 1000000, "canonicalModel": "claude-sonnet-5"}},
}


def fake_claude(tmp_path, body: str):
    """A `claude` that records how it was called and answers with what we say."""
    path = tmp_path / "claude"
    path.write_text(f"#!/bin/sh\ncat > {tmp_path}/stdin.txt\npwd > {tmp_path}/cwd.txt\n"
                    f'printf "%s\\n" "$*" > {tmp_path}/argv.txt\n{body}\n', encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def executor(tmp_path, body: str = None, **options):
    body = f"cat {tmp_path}/answer.json" if body is None else body
    (tmp_path / "answer.json").write_text(json.dumps(ANSWER), encoding="utf-8")
    binary = fake_claude(tmp_path, body)
    return registry.build_executor("claude_code", {"binary": [str(binary)], **options})


def request(tmp_path, text="do the thing"):
    workdir = tmp_path / "work"
    workdir.mkdir(exist_ok=True)
    return StepRequest(
        slug="add-login",
        step_name="probe",
        attempt=1,
        provider="claude_code",
        input_text=text,
        workdir=workdir,
        project=tmp_path / "project",
    )


@pytest.fixture(autouse=True)
def project_dir(tmp_path):
    (tmp_path / "project").mkdir(exist_ok=True)


# --- level A: start it, write into it, read what it said ------------------


def test_the_input_reaches_the_session_whole(tmp_path):
    long_input = "a step's input\n" * 500

    executor(tmp_path).execute(request(tmp_path, long_input))

    assert (tmp_path / "stdin.txt").read_text() == long_input


def test_it_runs_in_the_project_not_wherever_the_kit_was_started(tmp_path):
    executor(tmp_path).execute(request(tmp_path))

    assert (tmp_path / "cwd.txt").read_text().strip() == str(tmp_path / "project")


def test_the_flags_come_from_the_provider_s_own_declaration(tmp_path):
    executor(tmp_path, model="sonnet", effort="high").execute(request(tmp_path))

    argv = (tmp_path / "argv.txt").read_text()
    assert "-p" in argv
    assert "--output-format json" in argv
    assert "--model sonnet" in argv
    assert "--effort high" in argv
    assert "--permission-mode bypassPermissions" in argv


def test_the_session_is_named_by_the_kit_and_confirmed_by_the_answer(tmp_path):
    """The plan: the session's real name reported rather than guessed."""
    result = executor(tmp_path).execute(request(tmp_path))

    argv = (tmp_path / "argv.txt").read_text()
    assert "--session-id" in argv
    assert result.facts.session == ANSWER["session_id"]
    assert result.facts.session in argv


def test_what_the_session_said_is_the_raw_output(tmp_path):
    result = executor(tmp_path).execute(request(tmp_path))

    assert result.raw == ANSWER["result"]


# --- level B: how much context, and is the account limited ---------------


def test_it_reports_how_much_context_the_session_holds(tmp_path):
    result = executor(tmp_path).execute(request(tmp_path))

    assert result.facts.context_used == 2 + 9538 + 16091 + 4
    assert result.facts.context_window == 1_000_000
    assert result.facts.model == "claude-sonnet-5"
    assert result.facts.cost_usd == pytest.approx(0.041)


def test_the_transcript_is_where_the_declaration_says_it_is(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = executor(tmp_path).execute(request(tmp_path))

    assert result.facts.transcript.name == f"{ANSWER['session_id']}.jsonl"
    assert str(tmp_path / "project").replace("/", "-") in str(result.facts.transcript)


def test_a_limited_account_says_so_and_says_until_when(tmp_path):
    limited = dict(ANSWER, is_error=True, subtype="error_during_execution",
                   result="Claude usage limit reached. Your limit will reset at 5pm (UTC).")
    body = f"cat {tmp_path}/limited.json"
    (tmp_path / "limited.json").write_text(json.dumps(limited), encoding="utf-8")

    with pytest.raises(ExecutorFailed) as caught:
        executor(tmp_path, body=body).execute(request(tmp_path))

    assert caught.value.code == "provider-limited"
    assert "5pm" in caught.value.detail


# --- what goes wrong, and how it is named --------------------------------


def test_a_binary_that_is_not_there_is_named_not_traced(tmp_path):
    runner = registry.build_executor("claude_code", {"binary": [str(tmp_path / "nowhere")]})

    with pytest.raises(ExecutorFailed) as caught:
        runner.execute(request(tmp_path))

    assert caught.value.code == "binary-missing"


def test_a_session_that_exits_badly_is_an_attempt_not_a_crash(tmp_path):
    runner = executor(tmp_path, body='echo "something went wrong" >&2\nexit 1')

    with pytest.raises(ExecutorFailed) as caught:
        runner.execute(request(tmp_path))

    assert caught.value.code == "session-failed"
    assert "something went wrong" in caught.value.detail


def test_an_answer_that_is_not_the_json_the_cli_promises(tmp_path):
    runner = executor(tmp_path, body='echo "not json at all"')

    with pytest.raises(ExecutorFailed) as caught:
        runner.execute(request(tmp_path))

    assert caught.value.code == "unreadable-answer"


def test_a_session_that_never_answers_is_stopped(tmp_path):
    runner = executor(tmp_path, body="sleep 30", timeout=["1"])

    with pytest.raises(ExecutorFailed) as caught:
        runner.execute(request(tmp_path))

    assert caught.value.code == "session-timeout"
    assert "1" in caught.value.detail


def test_an_error_the_cli_reports_in_its_own_json(tmp_path):
    failed = dict(ANSWER, is_error=True, subtype="error_during_execution",
                  result="the tool call failed")
    (tmp_path / "failed.json").write_text(json.dumps(failed), encoding="utf-8")

    with pytest.raises(ExecutorFailed) as caught:
        executor(tmp_path, body=f"cat {tmp_path}/failed.json").execute(request(tmp_path))

    assert caught.value.code == "session-error"
    assert "the tool call failed" in caught.value.detail


def test_an_answer_with_no_result_at_all(tmp_path):
    empty = {key: value for key, value in ANSWER.items() if key != "result"}
    (tmp_path / "empty.json").write_text(json.dumps(empty), encoding="utf-8")

    with pytest.raises(ExecutorFailed) as caught:
        executor(tmp_path, body=f"cat {tmp_path}/empty.json").execute(request(tmp_path))

    assert caught.value.code == "empty-answer"


# --- the folder declares what is true about the tool ---------------------


def test_claude_code_declares_itself_level_b_and_real():
    facts = registry.facts("claude_code")

    assert facts.level == "B"
    assert facts.real is True
    assert facts.binary == "claude"


def test_the_kit_now_ships_two_providers():
    assert registry.provider_names() == ["claude_code", "fake"]
