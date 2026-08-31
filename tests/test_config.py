"""S0 — the configuration. One truth, and it states choices, never facts about a tool."""

import pytest

from agent_kit.config import DEFAULT_ANSWER_WAIT, DEFAULT_MAX_SESSIONS, load_config
from agent_kit.errors import ConfigError


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_missing_file_is_defaults_not_an_error(tmp_path):
    config = load_config(tmp_path / "config.toml")

    assert config.source is None
    assert config.machine.max_sessions == DEFAULT_MAX_SESSIONS
    assert config.providers == {}
    assert config.roles == {}


def test_reads_the_shape_the_plan_fixed(tmp_path):
    path = write(
        tmp_path / "config.toml",
        """
[machine]
max_sessions = 4

[providers.codex]
enabled = true
model = "gpt-5.4-codex"
effort = "high"
max_sessions = 2

[roles.build]
provider = "codex"
fallback = ["claude_code"]
""",
    )

    config = load_config(path)

    assert config.source == path
    assert config.machine.max_sessions == 4
    codex = config.providers["codex"]
    assert (codex.enabled, codex.model, codex.effort, codex.max_sessions) == (True, "gpt-5.4-codex", "high", 2)
    build = config.roles["build"]
    assert (build.provider, build.fallback) == ("codex", ["claude_code"])


def test_a_role_may_fall_back_to_nothing(tmp_path):
    path = write(tmp_path / "config.toml", '[roles.review]\nprovider = "opencode"\n')

    assert load_config(path).roles["review"].fallback == []


@pytest.mark.parametrize(
    "text, reason",
    [
        ("[machine]\nmax_sessions = 0\n", "machine.max_sessions"),
        ('[machine]\nmax_sessions = "four"\n', "machine.max_sessions"),
        ("[providers.codex]\nenabled = 1\n", "providers.codex.enabled"),
        ('[roles.build]\nprovider = "codex"\nfallback = [1]\n', "roles.build.fallback"),
        ("[roles.build]\n", "roles.build.provider"),
        ("[nonsense]\nx = 1\n", "nonsense"),
        ("[providers.codex]\ntranscript = \"~/x\"\n", "providers.codex.transcript"),
        ("not toml at all = = =\n", "config.toml"),
    ],
)
def test_a_refusal_names_what_it_refused(tmp_path, text, reason):
    path = write(tmp_path / "config.toml", text)

    with pytest.raises(ConfigError) as caught:
        load_config(path)

    assert reason in str(caught.value)


# --- S7a: the owner's channel ----------------------------------------------


def test_a_machine_with_no_owner_block_has_no_channel(tmp_path):
    config = load_config(write(tmp_path / "config.toml", "[machine]\nmax_sessions = 1\n"))

    assert config.owner.channel == ""
    assert config.owner.wait == DEFAULT_ANSWER_WAIT


def test_the_owner_block_says_which_channel_and_how_long_it_waits(tmp_path):
    config = load_config(
        write(
            tmp_path / "config.toml",
            """
[owner]
channel = "telegram"
chat = "55"
wait = 600
""",
        )
    )

    assert config.owner.channel == "telegram"
    assert config.owner.chat == "55"
    assert config.owner.wait == 600


def test_waiting_no_time_at_all_is_a_real_answer(tmp_path):
    """Zero means take the default at once, the way `machine.wait = 0` refuses at once."""
    config = load_config(write(tmp_path / "config.toml", '[owner]\nchannel = "file"\nwait = 0\n'))

    assert config.owner.wait == 0


def test_the_owner_block_refuses_what_it_does_not_read(tmp_path):
    with pytest.raises(ConfigError) as refused:
        load_config(write(tmp_path / "config.toml", '[owner]\ntoken = "secret"\n'))

    assert refused.value.code == "unknown-key"
    assert "owner.token" in refused.value.detail


def test_config_show_says_everything_it_reads(tmp_path):
    """A command called *show the configuration* that is silent about a setting is a defect."""
    from agent_kit.cli.main import _config_as_data

    shown = _config_as_data(load_config(write(tmp_path / "config.toml", '[owner]\nchannel = "file"\n')))

    assert set(shown["owner"]) == {"channel", "chat", "wait", "file"}


def test_a_machine_may_name_its_own_pause_between_attempts(tmp_path):
    """Ноль — настоящий ответ: пробовать снова сразу же."""
    from agent_kit.config import DEFAULT_BACKOFF

    assert load_config(tmp_path / "config.toml").machine.backoff == DEFAULT_BACKOFF
    assert load_config(write(tmp_path / "config.toml", "[machine]\nbackoff = 0\n")).machine.backoff == 0
    assert load_config(write(tmp_path / "config.toml", "[machine]\nbackoff = 5\n")).machine.backoff == 5

    with pytest.raises(ConfigError) as caught:
        load_config(write(tmp_path / "config.toml", "[machine]\nbackoff = -1\n"))
    assert caught.value.detail.startswith("machine.backoff")


# --- S9a: the provider this machine runs when a role does not say otherwise ---


def test_the_machine_may_name_the_provider_every_role_falls_back_to(tmp_path):
    """`doctor` has printed *every role falls back to the default* since S0, and
    there was no default. The key is what makes that line true."""
    path = write(tmp_path / "config.toml", '[machine]\nprovider = "claude_code"\n')

    config = load_config(path)

    assert config.machine.provider == "claude_code"


def test_a_machine_that_names_no_provider_says_so_with_an_empty_string(tmp_path):
    config = load_config(write(tmp_path / "config.toml", "[machine]\nmax_sessions = 2\n"))

    assert config.machine.provider == ""


def test_a_provider_that_is_not_a_name_is_refused(tmp_path):
    path = write(tmp_path / "config.toml", "[machine]\nprovider = 4\n")

    with pytest.raises(ConfigError) as refused:
        load_config(path)

    assert refused.value.code == "bad-value"
    assert "machine.provider" in refused.value.detail


@pytest.mark.parametrize("value", ["false", "0", "[]", '""'])
def test_a_provider_that_is_not_a_name_is_refused_whatever_shape_it_is(tmp_path, value):
    """`table.get(key) and ...` reads every falsy value as *not named*, silently.
    A name is a non-empty string or it is a mistake, and a mistake is refused."""
    path = write(tmp_path / "config.toml", f"[machine]\nprovider = {value}\n")

    with pytest.raises(ConfigError) as refused:
        load_config(path)

    assert refused.value.code == "bad-value"
    assert "machine.provider" in refused.value.detail
