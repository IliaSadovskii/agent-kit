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
    '[provider.setup]\ninstall = ["put-it-there", "newcomer"]\nlogin = ["newcomer", "login"]\n'
    'login_note = "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 \u0438 \u0432\u044b\u0439\u0434\u0438\u0442\u0435 \u0438\u0437 \u044d\u043a\u0440\u0430\u043d\u0430."\n\n'
    '[provider.flags]\nversion = ["--version"]\n'
)

#: The same tool, with nothing to log in to. What is left is the writing alone.
NO_LOGIN = (
    '[provider]\ntitle = "the newcomer"\nbinary = "newcomer"\n\n'
    '[provider.setup]\ninstall = ["put-it-there", "newcomer"]\n\n'
    '[provider.flags]\nversion = ["--version"]\n'
)

WALL = "a paragraph nobody standing mid-install has any use for"

#: Four paragraphs written for a reader of `provider.toml`.
WORDY = NEWCOMER.replace(
    'notes = "a tool that has to be put here first"',
    f'notes = """\n{WALL}\n\nand a second one, and a third, and a fourth\n"""',
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


# --- what the walk may not write, and what it may not call by somebody's code ---


def test_a_kit_that_ships_no_agent_is_a_different_state_from_a_machine_with_none(
    machine, tmp_path, monkeypatch
):
    """Two states, two codes. `no-provider` is the driver's: a role has nobody and
    there is no default, and the answer is to configure one. This one is the kit
    itself carrying no agent at all, and configuring is not the answer to it."""
    ships(tmp_path, monkeypatch, only='[provider]\ntitle = "not an agent"\nreal = false\n')
    printed, say = saying()

    with pytest.raises(ProviderError) as refused:
        walk(None, ask=typing(), say=say, paths=machine)

    assert refused.value.code == "ships-no-provider"


def test_the_walk_freezes_no_default_the_person_never_chose(machine, tmp_path, monkeypatch):
    """Rebuilding `[machine]` from the effective configuration would write `wait`
    and `backoff` as literal numbers on a machine that never chose either — and
    from that day a changed default in the kit would not reach this machine."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    written = machine.config_file.read_text(encoding="utf-8")
    assert 'provider = "newcomer"' in written
    assert "wait" not in written
    assert "backoff" not in written
    assert "max_sessions" not in written


def test_a_key_the_person_did_choose_survives_the_default_being_written(
    machine, tmp_path, monkeypatch
):
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    machine.config_file.parent.mkdir(parents=True, exist_ok=True)
    machine.config_file.write_text("[machine]\nmax_sessions = 7\n", encoding="utf-8")
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    written = machine.config_file.read_text(encoding="utf-8")
    assert "max_sessions = 7" in written
    assert 'provider = "newcomer"' in written
    assert "backoff" not in written


# --- which one a bare `agent-kit setup` walks --------------------------------


def test_a_bare_walk_takes_the_one_that_works_over_the_one_that_is_missing(
    machine, tmp_path, monkeypatch
):
    """S9 breaks a choice that could not go wrong while one provider was real.

    `next((one for one in real if not one.ready), real[0])` reads *the first that
    needs the walk*, and with a catalogue of one working provider that was always
    the working one. With four shipped and three of them not installed, the same
    line walks a machine whose agent is standing and configured off to install a
    tool nobody asked about — in alphabetical order.
    """
    installs(tmp_path)  # the newcomer is here and answers
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER,
          zzz_absent='[provider]\nbinary = "zzz-absent"\n'
                     '[provider.setup]\ninstall = ["put-it-there", "zzz-absent"]\n')

    printed, say = saying()
    code = walk(None, typing("done"), say, machine)

    said = "\n".join(printed)
    assert code == int(ExitCode.OK)
    assert "put-it-there zzz-absent" not in said
    assert "[providers.newcomer] enabled" in said


def test_a_bare_walk_on_a_machine_with_nothing_takes_the_first_shipped(
    machine, tmp_path, monkeypatch
):
    """And where nothing works, the walk is still the walk: it names one and
    goes. Preferring a working provider must not mean refusing a fresh machine."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER,
          zzz_absent='[provider]\nbinary = "zzz-absent"\n')

    printed, say = saying()
    with pytest.raises(ProviderError) as caught:
        walk(None, typing("done"), say, machine)

    assert caught.value.code == "provider-not-ready"
    assert "newcomer" in "\n".join(printed)


# --- S9b: how many steps there are, and how far along this one is ------------


def test_the_walk_numbers_the_steps_it_will_take(machine, tmp_path, monkeypatch):
    """A machine with nothing on it: put the tool there, log it in, write it down."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    printed, say = saying()

    def person(prompt):
        installs(tmp_path)  # what they did in the other terminal
        return "\n"

    walk("newcomer", ask=person, say=say, paths=machine)

    screen = "\n".join(printed)
    assert "3 шага" in screen
    assert "1/3" in screen and "2/3" in screen and "3/3" in screen


def test_a_tool_already_standing_is_a_walk_of_two_steps(machine, tmp_path, monkeypatch):
    """The count is derived from what the walk will do, not written down beside it.

    A person who is only logging in is told `1/2`, and a walk that always said
    three would be counting a step it has already decided not to take.
    """
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    screen = "\n".join(printed)
    assert "2 шага" in screen
    assert "1/2" in screen and "2/2" in screen
    assert "/3" not in screen


def test_a_tool_with_nothing_left_but_the_writing_is_one_step(machine, tmp_path, monkeypatch):
    """And it asks nothing at all: the stream is empty and the walk still ends."""
    ships(tmp_path, monkeypatch, newcomer=NO_LOGIN)
    installs(tmp_path)
    printed, say = saying()

    code = walk("newcomer", ask=typing(), say=say, paths=machine)

    screen = "\n".join(printed)
    assert code == ExitCode.OK
    assert "1 шаг" in screen
    assert "1/1" in screen


def test_the_pool_question_is_a_step_and_the_count_says_so(machine, tmp_path, monkeypatch):
    """The one question that is not a command to run is still a step of the walk,
    and a count that left it out would run out before the screen did."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    machine.config_file.parent.mkdir(parents=True, exist_ok=True)
    machine.config_file.write_text("[providers.other]\nenabled = true\n", encoding="utf-8")
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "one-subscription\n"), say=say, paths=machine)

    screen = "\n".join(printed)
    assert "3 шага" in screen
    assert "1/3" in screen and "2/3" in screen and "3/3" in screen


def test_the_step_a_person_is_on_is_numbered_where_it_is_printed(machine, tmp_path, monkeypatch):
    """Not just present somewhere: the mark stands at the head of its own step."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    marked = [line.strip().split()[0] for line in printed if line.strip()[:3] in ("1/2", "2/2")]
    assert marked == ["1/2", "2/2"]


# --- S9b: what the walk stopped printing ------------------------------------


def test_the_walk_names_the_one_it_walks_and_not_the_whole_catalogue(
    machine, tmp_path, monkeypatch
):
    """`doctor` answers what this machine has. A walk that opens with the same
    inventory answers a question nobody asked and buries the step that is next."""
    ships(
        tmp_path, monkeypatch, newcomer=NEWCOMER,
        zzz_elsewhere='[provider]\ntitle = "the one nobody named"\nbinary = "zzz-elsewhere"\n',
    )
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    screen = "\n".join(printed)
    assert "zzz-elsewhere" not in screen
    assert "the one nobody named" not in screen


def test_the_declarations_notes_are_not_dumped_at_somebody_mid_install(
    machine, tmp_path, monkeypatch
):
    """Four paragraphs written for a reader of `provider.toml` are a wall in
    front of a person who wants to know what to type next."""
    ships(tmp_path, monkeypatch, newcomer=WORDY)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    assert WALL not in "\n".join(printed)


def test_the_notes_read_at_the_screen_whose_question_they_answer(
    machine, tmp_path, monkeypatch, capsys
):
    """Rule 5: a field with no reader is not written. The walk prints one line
    now, so `notes` reads where the question is *what this machine has*."""
    from agent_kit.cli.main import main

    ships(tmp_path, monkeypatch, newcomer=WORDY)
    installs(tmp_path)

    code = main(["doctor"])

    assert code == ExitCode.OK
    assert WALL in capsys.readouterr().out


def test_the_line_the_walk_does_print_is_the_declarations_own(
    machine, tmp_path, monkeypatch
):
    """What a person must do inside the login screen is true of the tool, so it
    is declared beside the command rather than guessed at by the walk."""
    ships(tmp_path, monkeypatch, newcomer=NEWCOMER)
    installs(tmp_path)
    printed, say = saying()

    walk("newcomer", ask=typing("\n", "\n"), say=say, paths=machine)

    assert "Выберите аккаунт и выйдите из экрана." in "\n".join(printed)
