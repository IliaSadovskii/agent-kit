"""S7a — the kit's first secret, and the file the plan gave it.

`~/.local/state/agent-kit/secrets` has been printed by `doctor` since S0 with
nothing that ever wrote it. The bot token is what it is for.
"""

import stat

import pytest

from agent_kit.errors import ConfigError
from agent_kit.owner.secrets import read_secret, write_secret


def test_a_secret_that_was_never_written_is_empty(tmp_path):
    assert read_secret(tmp_path / "secrets", "telegram_token") == ""


def test_a_secret_is_written_where_only_its_owner_can_read_it(tmp_path):
    path = tmp_path / "secrets"

    write_secret(path, "telegram_token", "12345:abc")

    assert read_secret(path, "telegram_token") == "12345:abc"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_writing_a_second_secret_keeps_the_first(tmp_path):
    path = tmp_path / "secrets"
    write_secret(path, "telegram_token", "12345:abc")

    write_secret(path, "another", "x")

    assert read_secret(path, "telegram_token") == "12345:abc"
    assert read_secret(path, "another") == "x"


def test_a_secrets_file_that_cannot_be_read_says_so_by_name(tmp_path):
    path = tmp_path / "secrets"
    path.write_text("this is not toml = = =\n", encoding="utf-8")

    with pytest.raises(ConfigError) as refused:
        read_secret(path, "telegram_token")

    assert refused.value.code == "unreadable-secrets"


def test_the_secret_never_reaches_the_configuration(tmp_path):
    """`config.toml` stays safe to show, which is the sentence the plan wrote about it."""
    from agent_kit.config import load_config

    write_secret(tmp_path / "secrets", "telegram_token", "12345:abc")
    (tmp_path / "config.toml").write_text('[owner]\nchannel = "telegram"\nchat = "55"\n', encoding="utf-8")

    config = load_config(tmp_path / "config.toml")

    assert "12345" not in str(config)
