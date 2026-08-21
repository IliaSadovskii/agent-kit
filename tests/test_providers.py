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


def test_a_provider_with_no_executor_module_is_refused(tmp_path, monkeypatch):
    declare(tmp_path, monkeypatch, "hollow", "[provider]\ntitle = 'nothing behind it'\n")

    with pytest.raises(ProviderError) as caught:
        registry.build_executor("hollow")

    assert caught.value.code == "no-adapter"


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
