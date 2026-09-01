"""A provider is a folder and nothing else — and a folder that lies is refused."""

import pytest

from agent_kit.errors import ProviderError
from agent_kit.providers import registry


def test_the_registry_reads_the_folder():
    assert "fake" in registry.provider_names()


def test_the_fake_declares_itself_a_fixture():
    facts = registry.facts("fake")

    assert facts.real is False
    assert facts.level == "A"


def test_a_provider_the_kit_does_not_ship_is_refused_by_name():
    """The name has to be one the kit will not ship tomorrow. It was `codex`,
    which S9 ships — a test whose subject moves into the catalogue stops asking
    its question on the day it matters most."""
    with pytest.raises(ProviderError) as caught:
        registry.facts("a-tool-nobody-wrote")

    assert caught.value.code == "unknown-provider"


def declare(tmp_path, monkeypatch, name, text):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "provider.toml").write_text(text, encoding="utf-8")
    monkeypatch.setattr(registry, "PROVIDERS_DIR", tmp_path)
    return folder


def test_a_declaration_that_is_not_valid_toml_is_refused_not_raised(tmp_path, monkeypatch):
    declare(tmp_path, monkeypatch, "broken", "this is not = = toml")

    with pytest.raises(ProviderError) as caught:
        registry.facts("broken")

    assert caught.value.code == "bad-declaration"


def test_a_declaration_with_no_provider_table_is_refused(tmp_path, monkeypatch):
    """Silence must not read as 'a real level A agent'."""
    declare(tmp_path, monkeypatch, "empty", "title = 'nothing here'\n")

    with pytest.raises(ProviderError) as caught:
        registry.facts("empty")

    assert caught.value.code == "bad-declaration"


def test_a_provider_that_declares_nothing_to_run_is_refused(tmp_path, monkeypatch):
    """A folder with no binary and no adapter is not a provider, it is a wish."""
    declare(tmp_path, monkeypatch, "hollow", "[provider]\ntitle = 'nothing behind it'\n")

    with pytest.raises(ProviderError) as caught:
        registry.build_executor("hollow")

    assert caught.value.code == "bad-declaration"
    assert "binary" in caught.value.detail


def test_a_folder_with_only_a_declaration_is_a_level_a_provider(tmp_path, monkeypatch):
    """The plan: adding one at level A is provider.toml alone."""
    import stat

    binary = tmp_path / "some-cli"
    binary.write_text('#!/bin/sh\ncat > /dev/null\necho "it answered"\n', encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    declare(tmp_path, monkeypatch, "declared_only", f"""
[provider]
title = "a provider that is only a declaration"
level = "A"
binary = "{binary}"
[provider.flags]
headless = ["-p"]
""")

    executor = registry.build_executor("declared_only", {})
    from pathlib import Path

    from agent_kit.driver.executor import StepRequest

    result = executor.execute(
        StepRequest(slug="s", step_name="probe", attempt=1, provider="declared_only",
                    input_text="hello", workdir=tmp_path, project=tmp_path)
    )

    assert result.raw.strip() == "it answered"
    assert result.facts.observed is False  # level A knows nothing about context


def test_a_declaration_with_a_key_the_kit_does_not_read_is_refused(tmp_path, monkeypatch):
    """The stricter half must not be the one only the kit writes."""
    declare(tmp_path, monkeypatch, "typo", "[provider]\ntitle = 'x'\nlevle = 'B'\n")

    with pytest.raises(ProviderError) as caught:
        registry.facts("typo")

    assert caught.value.code == "bad-declaration"
    assert "levle" in caught.value.detail


# --- a key nobody reads is argv nobody passes -------------------------------


def test_a_flag_the_kit_does_not_read_is_refused(tmp_path, monkeypatch):
    """A misspelt flag key is silence wearing a declaration's clothes.

    The top-level keys have been checked since S3 and `setup.*` since S9a, but
    `flags` went through as a dictionary. That is the one table where silence is
    invisible: a provider whose `headless` is deliberately absent — Gemini CLI
    decides by whether stdin is a terminal — and one whose `headless` is spelt
    `hedless` build exactly the same argv.
    """
    declare(tmp_path, monkeypatch, "typo_flag",
            '[provider]\nbinary = "x"\n[provider.flags]\nhedless = ["-p"]\n')

    with pytest.raises(ProviderError) as caught:
        registry.facts("typo_flag")

    assert caught.value.code == "bad-declaration"
    assert "hedless" in caught.value.detail


def test_an_answer_key_the_kit_does_not_read_is_refused(tmp_path, monkeypatch):
    declare(tmp_path, monkeypatch, "typo_answer",
            '[provider]\nbinary = "x"\n[provider.answer]\nsesion = "session_id"\n')

    with pytest.raises(ProviderError) as caught:
        registry.facts("typo_answer")

    assert caught.value.code == "bad-declaration"
    assert "sesion" in caught.value.detail


def test_every_key_the_kit_does_read_is_accepted(tmp_path, monkeypatch):
    """The other half: the check must not refuse what the shipped ones declare."""
    declare(tmp_path, monkeypatch, "thorough", """
[provider]
binary = "x"
[provider.flags]
headless = ["-p"]
full_access = ["--go"]
instructions = ["--project"]
model = ["--model"]
effort = ["--effort"]
session = ["--session-id"]
version = ["--version"]
[provider.answer]
text = "result"
session = "session_id"
cost = "total_cost_usd"
failed = "is_error"
window = "modelUsage"
used = "usage"
""")

    facts = registry.facts("thorough")

    assert facts.flags["headless"] == ["-p"]
    assert facts.answer["text"] == "result"


def test_a_flag_table_that_is_not_a_table_is_refused(tmp_path, monkeypatch):
    declare(tmp_path, monkeypatch, "flat", '[provider]\nbinary = "x"\nflags = "-p"\n')

    with pytest.raises(ProviderError) as caught:
        registry.facts("flat")

    assert caught.value.code == "bad-declaration"



# --- a choice the tool cannot be told ---------------------------------------


PLAIN = '[provider]\nbinary = "x"\n[provider.flags]\nheadless = ["-p"]\nversion = ["--version"]\n'


def test_a_model_the_tool_has_no_flag_for_is_refused_by_name(tmp_path, monkeypatch):
    """`config.toml` names a model; the tool has no flag; the session ran anyway.

    `command()` read `if self.model and flags.get("model")` and dropped the
    choice on the floor. The machine then paid for a night on whatever model the
    tool defaults to, and no file anywhere said a choice had been made and lost.
    """
    from agent_kit.errors import ConfigError

    declare(tmp_path, monkeypatch, "plain", PLAIN)

    with pytest.raises(ConfigError) as caught:
        registry.build_executor("plain", {"model": ["a-model-it-never-heard-of"]})

    assert caught.value.code == "model-not-selectable"
    assert "plain" in caught.value.detail


def test_an_effort_the_tool_has_no_flag_for_is_refused_by_name(tmp_path, monkeypatch):
    from agent_kit.errors import ConfigError

    declare(tmp_path, monkeypatch, "plain", PLAIN)

    with pytest.raises(ConfigError) as caught:
        registry.build_executor("plain", {"effort": ["high"]})

    assert caught.value.code == "effort-not-selectable"


def test_a_choice_the_tool_can_be_told_is_not_refused(tmp_path, monkeypatch):
    declare(tmp_path, monkeypatch, "choosy",
            '[provider]\nbinary = "x"\n[provider.flags]\n'
            'headless = ["-p"]\nmodel = ["--model"]\neffort = ["--effort"]\n')

    executor = registry.build_executor("choosy", {"model": ["m"], "effort": ["high"]})

    assert executor.command() == ["x", "-p", "--model", "m", "--effort", "high"]


def test_a_machine_that_chose_nothing_is_not_refused(tmp_path, monkeypatch):
    """The refusal is about a choice that would be lost, not about the flag."""
    declare(tmp_path, monkeypatch, "plain", PLAIN)

    assert registry.build_executor("plain", {}).command() == ["x", "-p"]



# --- the fixture answers, and may also act ----------------------------------


def test_a_scripted_reply_may_do_what_a_session_would_have_done(tmp_path):
    """A session answers and edits. A fixture that only answers cannot plant a trap.

    So a reply file may carry a script beside it, and it runs in the project
    before the answer is given. Only the fake provider has this: it is the one
    thing that stands where a session would.
    """
    from agent_kit.providers.base import StepRequest
    from agent_kit.providers.fake.adapter import build_executor

    reply = tmp_path / "01-build.json"
    reply.write_text('{"complete": true}', encoding="utf-8")
    (tmp_path / "01-build.sh").write_text("#!/bin/sh\nprintf 'RATE = 20\\n' >> money.py\n", encoding="utf-8")
    (tmp_path / "01-build.sh").chmod(0o755)
    project = tmp_path / "project"
    project.mkdir()

    executor = build_executor({"reply": [str(reply)]})
    result = executor.execute(
        StepRequest(
            slug="add-vat", step_name="build", attempt=1, provider="fake",
            input_text="", workdir=project, project=project,
        )
    )

    assert result.raw == '{"complete": true}'
    assert (project / "money.py").read_text() == "RATE = 20\n"


def test_a_reply_whose_script_fails_is_a_refused_attempt_not_a_crash(tmp_path):
    from agent_kit.providers.base import ExecutorFailed, StepRequest
    from agent_kit.providers.fake.adapter import build_executor

    reply = tmp_path / "01-build.json"
    reply.write_text("{}", encoding="utf-8")
    (tmp_path / "01-build.sh").write_text("#!/bin/sh\necho no >&2\nexit 3\n", encoding="utf-8")
    (tmp_path / "01-build.sh").chmod(0o755)

    executor = build_executor({"reply": [str(reply)]})

    with pytest.raises(ExecutorFailed) as refused:
        executor.execute(
            StepRequest(
                slug="add-vat", step_name="build", attempt=1, provider="fake",
                input_text="", workdir=tmp_path, project=tmp_path,
            )
        )

    assert refused.value.code == "reply-script-failed"


def test_a_reply_script_that_hangs_takes_its_children_with_it(tmp_path):
    """The fixture starts other people's processes too, and the rule is the kit's own."""
    import time

    from agent_kit.providers.base import ExecutorFailed, StepRequest
    from agent_kit.providers.fake import adapter

    mark = tmp_path / "still-alive"
    reply = tmp_path / "01-build.json"
    reply.write_text("{}", encoding="utf-8")
    (tmp_path / "01-build.sh").write_text(
        "#!/bin/sh\n"
        f'(while true; do echo x >> "{mark}"; sleep 0.2; done) &\n'
        "sleep 30\n",
        encoding="utf-8",
    )

    executor = adapter.build_executor({"reply": [str(reply)]})
    with pytest.raises(ExecutorFailed) as stopped:
        with_short_patience(adapter, 2, executor, tmp_path)

    assert stopped.value.code == "reply-script-failed"
    grew = mark.stat().st_size if mark.exists() else 0
    time.sleep(1.5)
    assert (mark.stat().st_size if mark.exists() else 0) == grew


def with_short_patience(adapter, seconds, executor, where):
    from agent_kit.providers.base import StepRequest

    was, adapter.ACTS_TIMEOUT = adapter.ACTS_TIMEOUT, seconds
    try:
        return executor.execute(
            StepRequest(
                slug="add-vat", step_name="build", attempt=1, provider="fake",
                input_text="", workdir=where, project=where,
            )
        )
    finally:
        adapter.ACTS_TIMEOUT = was


# --- S7: a reply that is a refusal rather than an answer --------------------


def test_a_reply_file_may_be_a_refusal(tmp_path):
    """The bench needs a provider that can play a limited account, a dead session,

    a CLI that crashed. One line in a reply file, and its reader is the bench.
    """
    from agent_kit.providers.base import ExecutorFailed
    from agent_kit.providers.fake import FakeExecutor
    from agent_kit.providers.fake.adapter import build_executor

    reply = tmp_path / "01-reply.json"
    reply.write_text("!refuse provider-limited until=2026-08-24T17:00:00+00:00\n", encoding="utf-8")

    executor = build_executor({"reply": [str(reply)]})
    with pytest.raises(ExecutorFailed) as refused:
        executor.execute(_a_request(tmp_path))

    assert refused.value.code == "provider-limited"
    assert refused.value.until == "2026-08-24T17:00:00+00:00"
    assert refused.value.retryable is False


def test_a_refusal_with_nothing_after_the_code_is_still_a_refusal(tmp_path):
    from agent_kit.providers.base import ExecutorFailed
    from agent_kit.providers.fake.adapter import build_executor

    reply = tmp_path / "01-reply.json"
    reply.write_text("!refuse session-timeout\n", encoding="utf-8")

    with pytest.raises(ExecutorFailed) as refused:
        build_executor({"reply": [str(reply)]}).execute(_a_request(tmp_path))

    assert refused.value.code == "session-timeout"
    assert refused.value.until is None


def test_an_answer_that_merely_mentions_a_refusal_is_an_answer(tmp_path):
    from agent_kit.providers.fake.adapter import build_executor

    reply = tmp_path / "01-reply.json"
    reply.write_text('{"note": "it said !refuse somewhere in the middle"}', encoding="utf-8")

    answered = build_executor({"reply": [str(reply)]}).execute(_a_request(tmp_path))

    assert "!refuse" in answered.raw


def _a_request(tmp_path):
    from agent_kit.providers.base import StepRequest

    return StepRequest(
        slug="add-vat", step_name="design", attempt=1, provider="fake",
        input_text="", workdir=tmp_path, project=tmp_path,
    )


# --- S9a: the commands a person runs, declared beside the binary -------------


def test_a_provider_declares_how_it_is_installed_and_how_it_is_logged_into(tmp_path, monkeypatch):
    """Two argv lists and nothing else. A command the kit cannot run can still
    be held to something: its first word is looked for on PATH before it is
    printed, and the rung below it is climbed again after it was run."""
    declare(
        tmp_path,
        monkeypatch,
        "newcomer",
        '[provider]\nbinary = "newcomer"\n\n'
        '[provider.setup]\ninstall = ["npm", "install", "-g", "newcomer"]\nlogin = ["newcomer", "login"]\n',
    )

    facts = registry.facts("newcomer")

    assert facts.install == ["npm", "install", "-g", "newcomer"]
    assert facts.login == ["newcomer", "login"]


def test_a_provider_that_declares_no_setup_says_so_with_nothing(tmp_path, monkeypatch):
    declare(tmp_path, monkeypatch, "bare", '[provider]\nbinary = "bare"\n')

    facts = registry.facts("bare")

    assert facts.install == [] and facts.login == []


@pytest.mark.parametrize(
    "block",
    [
        '[provider.setup]\ninstall = "npm install -g newcomer"\n',
        '[provider.setup]\ninstall = ["npm", ""]\n',
        '[provider.setup]\nlogin = [4]\n',
        '[provider.setup]\nrun = ["npm"]\n',
    ],
)
def test_a_setup_command_that_is_not_argv_is_refused_by_name(tmp_path, monkeypatch, block):
    """Prose in this block would be a declaration nobody can check. Argv can be
    taken by its first word and asked of PATH; a sentence cannot."""
    declare(tmp_path, monkeypatch, "sloppy", f'[provider]\nbinary = "sloppy"\n\n{block}')

    with pytest.raises(ProviderError) as caught:
        registry.facts("sloppy")

    assert caught.value.code == "bad-declaration"


def test_claude_code_ships_the_two_commands_a_fresh_machine_needs():
    facts = registry.facts("claude_code")

    assert facts.install and facts.login
    assert all(isinstance(word, str) and word for word in facts.install + facts.login)


def test_the_fixture_declares_neither_because_nobody_installs_it():
    facts = registry.facts("fake")

    assert facts.install == [] and facts.login == []


# --- S9b: what a session that failed gets to say ----------------------------
#
# Both defects below were found by the first live climb of the ladder against a
# real provider, on a machine where Codex was installed and not logged in. The
# bench cannot reach either of them from `providers/fake/`, which has no CLI and
# no account, so what holds the shape is here.


def test_a_refusal_carries_the_end_of_what_was_said_not_the_beginning():
    """A CLI puts its banner first and its reason last.

    Measured: `codex exec` against an account that was not signed in printed
    *Reading prompt from stdin…*, its version, the workdir and the model, and
    the 401 came after all of it. Trimmed from the front, the screen carried the
    banner and cut off exactly where the sentence somebody needed began.
    """
    from agent_kit.providers.process import short

    said = "a banner nobody needs\n" * 200 + "ERROR: 401 Unauthorized"

    kept = short(said)

    assert "ERROR: 401 Unauthorized" in kept
    assert kept.startswith("…")  # and it says that it dropped a front


def test_a_diagnostic_screen_gets_more_of_that_end_than_a_nights_log_does():
    """Two limits and not one: a run writes a refusal per attempt and a whole
    transcript per attempt is its own defect, while `provider check` is a screen
    somebody typed to find out what is wrong with exactly one provider."""
    from agent_kit.providers.process import short, tail

    said = "\n".join(
        f"line {number}: a session starting up and saying so at some length" for number in range(500)
    ) + "\nERROR: the reason"

    assert "ERROR: the reason" in tail(said)
    assert len(tail(said)) > len(short(said))
    assert len(tail(said).splitlines()) <= 40  # and still not a transcript


def _cli(tmp_path, monkeypatch, name, body, declaration):
    """A provider that is a shell script, declared by a folder and nothing else."""
    import stat

    binary = tmp_path / f"{name}-cli"
    binary.write_text(f"#!/bin/sh\ncat > /dev/null\n{body}\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    declare(tmp_path, monkeypatch, name, declaration.format(binary=binary))
    return registry.build_executor(name, {})


def _ask(executor, tmp_path, name):
    from agent_kit.driver.executor import StepRequest

    return executor.execute(
        StepRequest(slug="s", step_name="probe", attempt=1, provider=name,
                    input_text="hello", workdir=tmp_path, project=tmp_path)
    )


A_CLI = '[provider]\nbinary = "{binary}"\n'
A_CLI_THAT_SIGNS_OUT = A_CLI + (
    '[provider.signed_out]\nsays = ["missing bearer or basic authentication"]\n'
)


def test_a_failing_session_keeps_the_whole_of_what_it_printed(tmp_path, monkeypatch):
    """`detail` is the end of it and `said` is all of it. The screen chooses."""
    from agent_kit.providers.base import ExecutorFailed

    banner = "; ".join(f"banner line {number}" for number in range(200))
    executor = _cli(tmp_path, monkeypatch, "wordy",
                    f'echo "{banner}" >&2\necho "ERROR: the reason" >&2\nexit 1', A_CLI)

    with pytest.raises(ExecutorFailed) as caught:
        _ask(executor, tmp_path, "wordy")

    assert caught.value.code == "session-failed"
    assert "ERROR: the reason" in caught.value.detail
    assert "banner line 0" in caught.value.said  # the whole of it survives
    assert "banner line 0" not in caught.value.detail  # and the line does not


def test_an_account_that_is_not_signed_in_is_a_code_and_not_a_phrase(tmp_path, monkeypatch):
    """The words belong to the tool that says them, so they live in its folder.

    They were a list of English substrings in `driver/check.py` — the kit doing
    to somebody else's stderr exactly what it forbids its own bench judges.
    """
    from agent_kit.providers.base import ExecutorFailed

    executor = _cli(
        tmp_path, monkeypatch, "loggedout",
        'echo "ERROR: unexpected status 401 Unauthorized: Missing bearer or '
        'basic authentication in header" >&2\nexit 1',
        A_CLI_THAT_SIGNS_OUT,
    )

    with pytest.raises(ExecutorFailed) as caught:
        _ask(executor, tmp_path, "loggedout")

    assert caught.value.code == "provider-signed-out"
    # Asking a logged-out account twice more, with the pause doubling between,
    # buys nothing: the chain drops it and asks the spare, which may be signed in.
    assert caught.value.retryable is False


def test_a_provider_that_declares_no_such_words_fails_as_an_ordinary_session(tmp_path, monkeypatch):
    """Silence is not a diagnosis, and it must not be turned into one."""
    from agent_kit.providers.base import ExecutorFailed

    executor = _cli(tmp_path, monkeypatch, "silent",
                    'echo "ERROR: 401 Unauthorized: Missing bearer" >&2\nexit 1', A_CLI)

    with pytest.raises(ExecutorFailed) as caught:
        _ask(executor, tmp_path, "silent")

    assert caught.value.code == "session-failed"


def test_a_session_that_worked_is_not_read_for_those_words(tmp_path, monkeypatch):
    """Only ever read off a failure — the same rule the limit has."""
    executor = _cli(tmp_path, monkeypatch, "chatty",
                    'echo "I once saw Missing bearer or basic authentication"', A_CLI_THAT_SIGNS_OUT)

    result = _ask(executor, tmp_path, "chatty")

    assert "Missing bearer" in result.raw


@pytest.mark.parametrize("block", [
    '[provider.signed_out]\nsays = "not a list"\n',
    '[provider.signed_out]\nsays = []\n',
    '[provider.signed_out]\nsays = [""]\n',
    '[provider.limits]\nsays = "not a list"\n',
])
def test_words_to_look_for_that_are_not_a_list_of_words_are_refused(tmp_path, monkeypatch, block):
    """A bare string here walks its own characters: `"401"` would match every
    text holding a `4`. That is a false sign-out on a night, and a provider
    dropped from the chain for it."""
    declare(tmp_path, monkeypatch, "sloppy", '[provider]\nbinary = "x"\n' + block)

    with pytest.raises(ProviderError) as caught:
        registry.facts("sloppy")

    assert caught.value.code == "bad-declaration"


def test_a_key_under_signed_out_that_nobody_reads_is_refused(tmp_path, monkeypatch):
    """The same rule every other sub-table of the declaration is held to."""
    declare(tmp_path, monkeypatch, "extra",
            '[provider]\nbinary = "x"\n[provider.signed_out]\nsays = ["x"]\nuntil = "y"\n')

    with pytest.raises(ProviderError) as caught:
        registry.facts("extra")

    assert caught.value.code == "bad-declaration"


def test_the_shipped_declarations_say_what_they_have_seen_and_no_more():
    """Measured where it was measured, silent where nobody looked.

    `codex` carries the half of the sentence the owner's own machine printed on
    1 September 2026 and not the broad half: `401 Unauthorized` alone is also
    printed by somebody else's API reached from inside a session, and a false
    sign-out costs a provider dropped from a night's chain. `gemini_cli` carries
    nothing, because nobody here has seen it refuse for want of an account.
    """
    codex = registry.facts("codex")

    assert codex.signed_out == ["missing bearer or basic authentication"]
    assert registry.facts("gemini_cli").signed_out == []


# --- S9c: what a machine must already have, declared before anybody installs --
#
# The first live walks taught this by costing an afternoon: `bubblewrap` was
# learned from a conversation rather than from the kit, and every requirement
# a person hit arrived as a refusal *after* the install command had run. A
# requirement is a word asked of PATH, so it is measured like everything else
# here, and it is declared where what is true about a tool is declared.


def test_a_provider_declares_what_the_machine_must_already_have(tmp_path, monkeypatch):
    """A word, and the line saying why. Both, or the declaration is refused."""
    declare(
        tmp_path,
        monkeypatch,
        "newcomer",
        '[provider]\nbinary = "newcomer"\n\n'
        '[provider.setup]\ninstall = ["npm", "install", "-g", "newcomer"]\n\n'
        '[[provider.requires]]\nbinary = "node"\nwhy = "сам инструмент — сценарий node"\n',
    )

    facts = registry.facts("newcomer")

    assert [(one.binary, one.why) for one in facts.requires] == [
        ("node", "сам инструмент — сценарий node")
    ]


def test_a_provider_that_requires_nothing_says_so_with_nothing(tmp_path, monkeypatch):
    declare(tmp_path, monkeypatch, "bare", '[provider]\nbinary = "bare"\n')

    assert registry.facts("bare").requires == []


@pytest.mark.parametrize(
    "block",
    [
        '[provider.requires]\nbinary = "node"\nwhy = "x"\n',      # a table, not an array
        '[[provider.requires]]\nbinary = "node"\n',                 # no reason to name it
        '[[provider.requires]]\nwhy = "x"\n',                       # nothing to ask PATH
        '[[provider.requires]]\nbinary = "node --version"\nwhy = "x"\n',  # not one word
        '[[provider.requires]]\nbinary = "node"\nwhy = "x"\nversion = "20"\n',  # nobody reads it
        '[[provider.requires]]\nbinary = "node"\nwhy = "x"\n[[provider.requires]]\n'
        'binary = "node"\nwhy = "y"\n',                             # named twice
    ],
)
def test_a_requirement_that_cannot_be_asked_of_path_is_refused_by_name(
    tmp_path, monkeypatch, block
):
    """Prose here would be the thing these four days caught three times: a claim
    written from documentation and printed at somebody as if it were measured."""
    declare(
        tmp_path, monkeypatch, "sloppy",
        f'[provider]\nbinary = "sloppy"\n\n[provider.setup]\ninstall = ["npm", "i"]\n\n{block}',
    )

    with pytest.raises(ProviderError) as caught:
        registry.facts("sloppy")

    assert caught.value.code == "bad-declaration"


def test_a_requirement_the_kit_already_derives_is_refused(tmp_path, monkeypatch):
    """The first word of the install command is asked of PATH already, and the
    provider's own binary is the first rung of the ladder. Declaring either
    would put one thing on the screen twice, under two spellings of why."""
    for word in ("npm", "sloppy"):
        room = tmp_path / word
        room.mkdir()
        declare(
            room, monkeypatch, "sloppy",
            '[provider]\nbinary = "sloppy"\n\n'
            '[provider.setup]\ninstall = ["npm", "install", "-g", "sloppy"]\n\n'
            f'[[provider.requires]]\nbinary = "{word}"\nwhy = "x"\n',
        )

        with pytest.raises(ProviderError) as caught:
            registry.facts("sloppy")

        assert caught.value.code == "bad-declaration"


def test_the_shipped_declarations_require_what_was_measured_on_a_machine():
    """Measured on the owner's server on 1 September 2026, by looking at the
    files: `codex` and `gemini` are both `#!/usr/bin/env node`, so neither runs
    without node. The `claude` standing on that machine is a native binary, so
    a node requirement written for it would be a claim about a tool nobody here
    has installed that way — and unmeasured claims are what this week caught
    three times out of three.
    """
    for name in ("codex", "gemini_cli"):
        assert [one.binary for one in registry.facts(name).requires] == ["node"]
        assert all(one.why for one in registry.facts(name).requires)
    assert registry.facts("claude_code").requires == []
    assert registry.facts("fake").requires == []
