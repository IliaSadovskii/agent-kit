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
    with pytest.raises(ProviderError) as caught:
        registry.facts("codex")

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
