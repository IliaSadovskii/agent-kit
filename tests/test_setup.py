"""S9a — the way in, for a machine that has nothing installed.

One reading, two screens over it, and a walk that prints commands and runs none.
"""

import stat

import pytest

from agent_kit.errors import ChannelError, ConfigError, ExitCode, ProviderError
from agent_kit.paths import Paths
from agent_kit.setup import read, render, walk


# --- a machine of its own ---------------------------------------------------


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A home, a `bin` on PATH with nothing in it, and no configuration at all."""
    home = tmp_path / "home"
    binaries = tmp_path / "bin"
    binaries.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(binaries))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    return Paths.from_env()


def ships(tmp_path, monkeypatch, **declarations):
    """A providers folder of our own: the catalogue is the folder, always."""
    from agent_kit.providers import registry

    root = tmp_path / "providers"
    root.mkdir(parents=True, exist_ok=True)
    for name, text in declarations.items():
        (root / name).mkdir()
        (root / name / "provider.toml").write_text(text, encoding="utf-8")
    monkeypatch.setattr(registry, "PROVIDERS_DIR", root)
    return root


NEWCOMER = (
    '[provider]\ntitle = "the newcomer"\nbinary = "newcomer"\n'
    'notes = "a tool that has to be put here first"\n\n'
    '[provider.setup]\ninstall = ["put-it-there", "newcomer"]\nlogin = ["newcomer", "login"]\n\n'
    '[provider.flags]\nversion = ["--version"]\n'
)


def installs(tmp_path):
    """What a person runs in the other terminal — and what the kit never runs."""
    binary = tmp_path / "bin/newcomer"
    binary.write_text("#!/bin/sh\necho 'newcomer 1.0'\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    return binary


def typing(*lines):
    """The person at the terminal. A stream that runs out is a person who left."""
    said = iter(lines)

    def ask(prompt):
        return next(said, "")

    return ask


def saying():
    printed = []
    return printed, printed.append


# --- the reading ------------------------------------------------------------


def test_the_list_is_the_folder_and_nothing_else(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER, other='[provider]\nbinary = "other"\n')

    reading = read(machine)

    assert [one.name for one in reading.providers] == ["newcomer", "other"]


def test_a_provider_that_is_not_here_stops_on_the_first_free_rung(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)

    one = read(machine).named("newcomer")

    assert one.ready is False
    assert one.stopped_on == "binary"
    assert one.install == ["put-it-there", "newcomer"]
    assert one.installer_missing == "put-it-there"


def test_a_provider_that_is_here_climbs_both_free_rungs(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)

    one = read(machine).named("newcomer")

    assert one.ready is True
    assert [(rung.name, rung.held) for rung in one.rungs] == [("binary", True), ("answers", True)]


def test_the_fixture_is_marked_rather_than_hidden(machine):
    """`Declaration.real` has exactly one reader, and this is it."""
    reading = read(machine)

    assert reading.named("fake").real is False
    assert any("fixture" in line for line in render(reading))


def test_a_configuration_that_will_not_parse_is_named_not_raised(machine, tmp_path):
    machine.config_file.parent.mkdir(parents=True, exist_ok=True)
    machine.config_file.write_text("this is = = not toml", encoding="utf-8")

    reading = read(machine)

    assert reading.unreadable_config is not None
    assert reading.unreadable_config.code == "unreadable-config"
    assert reading.providers


# --- the walk ---------------------------------------------------------------


def test_a_machine_with_nothing_installed_reaches_a_provider(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    printed, say = saying()

    def person(prompt):
        installs(tmp_path)  # what they did in the other terminal
        return "\n"

    code = walk("newcomer", ask=person, say=say, paths=machine)

    assert code == ExitCode.OK
    written = machine.config_file.read_text(encoding="utf-8")
    assert "[providers.newcomer]" in written
    assert "enabled = true" in written
    assert 'provider = "newcomer"' in written


def test_the_install_command_is_printed_and_never_run(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    printed, say = saying()

    with pytest.raises(ProviderError):
        walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    screen = "\n".join(printed)
    assert "put-it-there newcomer" in screen
    assert not (tmp_path / "bin/newcomer").exists()


def test_an_install_that_installed_nothing_writes_nothing(machine, tmp_path, monkeypatch):
    """The rung is climbed again afterwards, so *installed* is measured, never reported."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    printed, say = saying()

    with pytest.raises(ProviderError) as refused:
        walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    assert refused.value.code == "provider-not-ready"
    assert refused.value.exit_code == ExitCode.PROVIDER
    assert not machine.config_file.exists()


def test_a_stream_that_closed_while_a_question_stood_writes_nothing(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    printed, say = saying()

    with pytest.raises(ChannelError) as refused:
        walk("newcomer", ask=typing(), say=say, paths=machine)

    assert refused.value.code == "nobody-to-ask"
    assert refused.value.exit_code == ExitCode.CHANNEL
    assert not machine.config_file.exists()


def test_a_configuration_that_will_not_parse_is_never_overwritten(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    machine.config_file.parent.mkdir(parents=True, exist_ok=True)
    machine.config_file.write_text("this is = = not toml", encoding="utf-8")
    printed, say = saying()

    with pytest.raises(ConfigError) as refused:
        walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    assert refused.value.code == "unreadable-config"
    assert machine.config_file.read_text(encoding="utf-8") == "this is = = not toml"


def test_what_stood_in_the_file_before_the_walk_is_still_there(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    machine.config_file.parent.mkdir(parents=True, exist_ok=True)
    machine.config_file.write_text(
        "# what I chose, and why\n"
        "[machine]\n"
        "max_sessions = 7\n"
        "\n"
        "[providers.other]\n"
        "enabled = false\n"
        "\n"
        "[roles.build]\n"
        'provider = "other"\n',
        encoding="utf-8",
    )
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n", "\n"), say=say, paths=machine)

    written = machine.config_file.read_text(encoding="utf-8")
    assert "# what I chose, and why" in written
    assert "[providers.other]\nenabled = false" in written
    assert '[roles.build]\nprovider = "other"' in written
    assert "max_sessions = 7" in written
    assert "[providers.newcomer]" in written


def test_the_account_is_asked_only_where_there_is_something_to_answer(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    assert not any("pool" in line for line in printed)
    assert "account" not in machine.config_file.read_text(encoding="utf-8")


def test_the_account_is_asked_where_a_second_provider_is_configured(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    machine.config_file.parent.mkdir(parents=True, exist_ok=True)
    machine.config_file.write_text("[providers.other]\nenabled = true\n", encoding="utf-8")
    printed, say = saying()

    # Two lines and not three: the tool is already standing, so the install
    # command is never printed and its answer is never asked for.
    walk("newcomer", ask=typing("\n", "one-subscription\n"), say=say, paths=machine)

    assert any("pool" in line for line in printed)
    assert 'account = "one-subscription"' in machine.config_file.read_text(encoding="utf-8")


def test_the_walk_ends_by_naming_what_measures_the_account(machine, tmp_path, monkeypatch):
    """The block is written on the free rungs alone. Without this line the machine
    where a person is most lost — tool standing, account silent — hears nothing."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    assert "agent-kit provider check newcomer" in "\n".join(printed)


def test_a_provider_the_kit_does_not_ship_is_refused_by_name(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    printed, say = saying()

    with pytest.raises(ProviderError) as refused:
        walk("codex", ask=typing("\n"), say=say, paths=machine)

    assert refused.value.code == "unknown-provider"


def test_the_login_command_is_printed_and_the_login_is_not_claimed(machine, tmp_path, monkeypatch):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    screen = "\n".join(printed)
    assert "newcomer login" in screen
    assert "has not been measured" in screen
