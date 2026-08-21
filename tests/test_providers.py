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
