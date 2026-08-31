"""S3 — the first real adapter, driven against a `claude` that is a shell script.

Everything here runs with no agent CLI installed and no network: the adapter's
contract with Claude Code is "run this binary, give it this input, read this
JSON", and a script can hold up that end.
"""

import json
import stat
import time

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
    """A `claude` that records how it was called and answers with what we say.

    Each argument on its own line, so a test can see that a value follows the
    flag it belongs to rather than merely appearing somewhere in the command.
    """
    path = tmp_path / "claude"
    path.write_text(f"#!/bin/sh\ncat > {tmp_path}/stdin.txt\npwd > {tmp_path}/cwd.txt\n"
                    f'printf "%s\\n" "$@" > {tmp_path}/argv.txt\n{body}\n', encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def argv(tmp_path) -> list[str]:
    return (tmp_path / "argv.txt").read_text().splitlines()


def value_after(tmp_path, flag: str) -> str | None:
    words = argv(tmp_path)
    return words[words.index(flag) + 1] if flag in words and words.index(flag) + 1 < len(words) else None


def executor(tmp_path, body: str = None, **options):
    body = f"cat {tmp_path}/answer.json" if body is None else body
    (tmp_path / "answer.json").write_text(json.dumps(ANSWER), encoding="utf-8")
    binary = fake_claude(tmp_path, body)
    given = {key: value if isinstance(value, list) else [value] for key, value in options.items()}
    return registry.build_executor("claude_code", {"binary": [str(binary)], **given})


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

    assert "-p" in argv(tmp_path)
    assert value_after(tmp_path, "--output-format") == "json"
    assert value_after(tmp_path, "--model") == "sonnet"
    assert value_after(tmp_path, "--effort") == "high"
    assert value_after(tmp_path, "--permission-mode") == "bypassPermissions"


def test_the_session_reads_the_project_s_instructions_and_not_the_operator_s(tmp_path):
    """The driver composes a step's input. A personal file on the machine is not part of it.

    Measured on the real CLI: with no flag a session obeys both the project's
    CLAUDE.md and the operator's own; with this one, only the project's.
    """
    executor(tmp_path).execute(request(tmp_path))

    assert value_after(tmp_path, "--setting-sources") == "project"


def test_the_kit_names_the_session_rather_than_hunting_for_it(tmp_path):
    result = executor(tmp_path).execute(request(tmp_path))

    assert value_after(tmp_path, "--session-id") == result.meta["session"]


def test_the_name_the_session_reports_is_the_one_that_counts(tmp_path):
    """The plan: the session's real name reported rather than guessed.

    The kit asks for a name. If the answer comes back under a different one,
    the answer is right and the request was a wish — the transcript is filed
    under what the CLI actually used.
    """
    result = executor(tmp_path).execute(request(tmp_path))

    assert result.facts.session == ANSWER["session_id"]
    assert result.facts.session != result.meta["session"]
    assert result.facts.transcript.name == f"{ANSWER['session_id']}.jsonl"


def test_what_the_session_said_is_the_raw_output(tmp_path):
    result = executor(tmp_path).execute(request(tmp_path))

    assert result.raw == ANSWER["result"]


# --- level B: how much context, and is the account limited ---------------


def transcript_of(tmp_path, monkeypatch, turns):
    """A session's own record, the shape Claude Code writes it in."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    folder = home / ".claude/projects" / str(tmp_path / "project").replace("/", "-")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{ANSWER['session_id']}.jsonl"
    lines = [{"type": "assistant", "message": {"usage": usage}} for usage in turns]
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return path


def test_how_much_context_the_session_holds_comes_from_its_own_record(tmp_path, monkeypatch):
    """The counters in the answer are totals over every turn: they re-count the
    cached prefix once per turn and outgrow the window. What the session was
    actually carrying is the last turn, and only the transcript has it."""
    transcript_of(
        tmp_path,
        monkeypatch,
        [
            {"input_tokens": 2, "cache_creation_input_tokens": 9538, "cache_read_input_tokens": 16091,
             "output_tokens": 4},
            {"input_tokens": 2, "cache_creation_input_tokens": 278, "cache_read_input_tokens": 26725,
             "output_tokens": 244},
        ],
    )

    result = executor(tmp_path).execute(request(tmp_path))

    assert result.facts.context_used == 2 + 278 + 26725 + 244
    assert result.facts.context_window == 1_000_000
    assert result.facts.context_share == pytest.approx(0.027249)


def test_what_the_answer_totals_is_kept_as_spend_not_as_fullness(tmp_path):
    result = executor(tmp_path).execute(request(tmp_path))

    assert result.facts.tokens_billed == 2 + 9538 + 16091 + 4
    assert result.facts.cost_usd == pytest.approx(0.041)
    assert result.facts.model == "claude-sonnet-5"


def test_with_no_transcript_to_read_it_says_it_does_not_know(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    result = executor(tmp_path).execute(request(tmp_path))

    assert result.facts.context_used is None
    assert result.facts.observed is False  # level B is a measurement, not a guess


def test_the_model_that_did_the_work_is_the_one_reported(tmp_path, monkeypatch):
    """A subagent or a title generator puts a second, smaller model in the answer."""
    two = dict(ANSWER, modelUsage={
        "claude-haiku-4-5": {"contextWindow": 200000, "outputTokens": 12},
        "claude-sonnet-5": {"contextWindow": 1000000, "outputTokens": 900},
    })
    (tmp_path / "two.json").write_text(json.dumps(two), encoding="utf-8")

    result = executor(tmp_path, body=f"cat {tmp_path}/two.json").execute(request(tmp_path))

    assert result.facts.model == "claude-sonnet-5"
    assert result.facts.context_window == 1_000_000


def test_the_transcript_is_where_the_declaration_says_it_is(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    result = executor(tmp_path).execute(request(tmp_path))

    assert result.facts.transcript.parent.parent == home / ".claude/projects"
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
    assert caught.value.until == "5pm (UTC)"
    assert not caught.value.retryable


def test_a_limit_announced_on_the_way_out_is_caught_too(tmp_path):
    """Exit non-zero with the message on stderr: the other shape of the same news."""
    body = 'echo "Claude usage limit reached. Your limit will reset at 9am." >&2\nexit 1'

    with pytest.raises(ExecutorFailed) as caught:
        executor(tmp_path, body=body).execute(request(tmp_path))

    assert caught.value.code == "provider-limited"
    assert caught.value.until == "9am"


def test_an_answer_that_merely_talks_about_limits_is_a_good_answer(tmp_path):
    """A step reviewing throttling code says these words. It has not been limited.

    Read on the success path, this cost three real sessions and a failed run.
    """
    talkative = dict(ANSWER, result='```json\n{"branch": "kit/x", "can_write": true, '
                                    '"notes": ["the endpoint has no rate limit", '
                                    '"a 429 says usage limit reached and the limit will reset at midnight"]}\n```')
    (tmp_path / "talk.json").write_text(json.dumps(talkative), encoding="utf-8")

    result = executor(tmp_path, body=f"cat {tmp_path}/talk.json").execute(request(tmp_path))

    assert "rate limit" in result.raw


# --- what goes wrong, and how it is named --------------------------------


def test_a_binary_that_is_not_there_is_named_not_traced(tmp_path):
    runner = registry.build_executor("claude_code", {"binary": [str(tmp_path / "nowhere")]})

    with pytest.raises(ExecutorFailed) as caught:
        runner.execute(request(tmp_path))

    assert caught.value.code == "binary-missing"
    assert not caught.value.retryable  # three attempts will not make it appear


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


def test_the_kit_ships_exactly_the_providers_its_folder_holds():
    """Exact, and not a floor: the catalogue is the folder, and adding or
    retiring one is deliberate, in a commit that says so — the same reason
    `bench.SHIPPED` is a number rather than a `>=`. Both the assertion and the
    name of this test said *two providers* until S9 shipped two more."""
    assert registry.provider_names() == ["claude_code", "codex", "fake", "gemini_cli"]


# --- the stream, the bytes, and what the CLI puts around its JSON ---------


def test_a_preamble_before_the_json_does_not_lose_the_answer(tmp_path):
    """The CLI, node, or a shell can say something first. The answer is still there."""
    body = f'echo "Shell cwd was reset to /work"; cat {tmp_path}/answer.json'

    result = executor(tmp_path, body=body).execute(request(tmp_path))

    assert result.raw == ANSWER["result"]


def test_a_byte_that_is_not_utf8_does_not_crash_the_driver(tmp_path):
    body = f'printf "\\377\\376"; cat {tmp_path}/answer.json'

    result = executor(tmp_path, body=body).execute(request(tmp_path))

    assert result.raw == ANSWER["result"]


def test_a_timeout_takes_the_whole_session_with_it(tmp_path):
    """A session left half-alive keeps editing files and keeps spending."""
    marker = tmp_path / "the-child-lived.txt"
    body = f'(sleep 3; touch {marker}) &\nsleep 30'

    with pytest.raises(ExecutorFailed) as caught:
        executor(tmp_path, body=body, timeout=["1"]).execute(request(tmp_path))

    assert caught.value.code == "session-timeout"
    time.sleep(4)
    assert not marker.exists(), "a tool the session started outlived the session"


def test_what_a_refused_attempt_cost_is_not_lost(tmp_path):
    """The spend must be visible exactly when the kit is burning money on retries."""
    failed = dict(ANSWER, is_error=True, result="the tool call failed")
    (tmp_path / "failed.json").write_text(json.dumps(failed), encoding="utf-8")

    with pytest.raises(ExecutorFailed) as caught:
        executor(tmp_path, body=f"cat {tmp_path}/failed.json").execute(request(tmp_path))

    assert caught.value.facts.cost_usd == pytest.approx(0.041)
    assert caught.value.facts.session == ANSWER["session_id"]


def test_an_option_that_is_not_a_number_is_refused_by_name(tmp_path):
    from agent_kit.errors import UsageError

    with pytest.raises(UsageError) as caught:
        registry.build_executor("claude_code", {"timeout": ["soon"]})

    assert caught.value.code == "bad-option"
