"""S7a — заводим канал одной командой, вместо шести шагов в чужой документации.

`config.toml` — файл, который человек читает и комментирует, так что команда,
которая его правит, правит ровно свой блок и не трогает ни байта чужого.
"""

import stat

import pytest

from agent_kit.config import OwnerConfig, load_config, write_owner_block
from agent_kit.errors import ConfigError
from agent_kit.owner import TELEGRAM_TOKEN, read_secret
from agent_kit.owner.setup import setup

TOKEN = "8123456:AAF-not-a-real-token"


# --- один блок, и ничего вокруг него -----------------------------------------


def test_the_block_is_written_and_nothing_around_it_is_touched(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        "# сколько сессий эта машина тянет разом\n"
        "[machine]\n"
        "max_sessions = 2  # памяти хватает на две\n",
        encoding="utf-8",
    )

    write_owner_block(path, OwnerConfig(channel="telegram", chat="55", wait=1200))

    said = path.read_text()
    assert "# памяти хватает на две" in said
    assert "# сколько сессий эта машина тянет разом" in said
    assert load_config(path).owner.chat == "55"
    assert load_config(path).machine.max_sessions == 2


def test_an_owner_block_that_is_already_there_is_replaced_and_not_doubled(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[owner]\nchannel = "file"\nfile = "/tmp/x"\n\n[machine]\nmax_sessions = 3\n',
                    encoding="utf-8")

    write_owner_block(path, OwnerConfig(channel="telegram", chat="55", wait=600))

    said = path.read_text()
    assert said.count("[owner]") == 1
    assert "file" not in said
    assert load_config(path).owner.channel == "telegram"
    assert load_config(path).machine.max_sessions == 3


def test_a_file_that_is_not_there_yet_is_made(tmp_path):
    path = tmp_path / "nested" / "config.toml"

    write_owner_block(path, OwnerConfig(channel="telegram", chat="55"))

    assert load_config(path).owner.chat == "55"


def test_what_is_written_is_read_back_by_the_kit_that_wrote_it(tmp_path):
    """Круг замкнут: команда пишет то, что загрузчик потом примет без отказа."""
    path = tmp_path / "config.toml"

    write_owner_block(path, OwnerConfig(channel="telegram", chat="-100500", wait=0))

    assert load_config(path).owner == OwnerConfig(channel="telegram", chat="-100500", wait=0, file="")


# --- вся дорожка целиком ------------------------------------------------------


class Bot:
    """Телеграм, отвечающий по бумажке. Ни одного сокета здесь не открывается."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.asked = []

    def __call__(self, token, chat=""):
        self.token = token
        return self

    def _next(self, method):
        self.asked.append(method)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def me(self):
        return self._next("getMe")

    def listen(self, offset):
        return self._next("listen")

    def send(self, text):
        self.asked.append(("sendMessage", text))
        return "1"


def said_by(lines):
    def say(text):
        lines.append(text)

    return say


def typed(*answers):
    held = list(answers)

    def ask(_prompt):
        return held.pop(0)

    return ask


def test_the_whole_road_from_a_token_to_a_working_channel(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    lines = []
    bot = Bot(["vat_night_bot", ("55", "Илья", "510")])

    written = setup(ask=typed(TOKEN), say=said_by(lines), bot=bot, wait=10, pause=lambda _: None)

    assert written.channel == "telegram"
    assert written.chat == "55"
    # Токен — в секретах, и только там: config.toml остаётся файлом, который не стыдно показать.
    from agent_kit.paths import Paths

    paths = Paths.from_env()
    assert read_secret(paths.secrets_file, TELEGRAM_TOKEN) == TOKEN
    assert TOKEN not in paths.config_file.read_text()
    assert load_config(paths.config_file).owner.chat == "55"
    # И человеку сказали, куда писать, его же словами.
    assert any("vat_night_bot" in line for line in lines)
    # Подтверждение действительно ушло. Прежнее утверждение было истинным
    # всегда: если `send` не звали, последним в списке лежала строка "listen",
    # и сравнение кортежей проходило впустую.
    (last,) = [one for one in bot.asked if isinstance(one, tuple)]
    assert last[0] == "sendMessage"
    assert "Илья" in last[1]


def test_the_secret_is_written_where_only_its_owner_reads_it(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    bot = Bot(["vat_night_bot", ("55", "Илья", "510")])

    setup(ask=typed(TOKEN), say=said_by([]), bot=bot, wait=10, pause=lambda _: None)

    from agent_kit.paths import Paths

    assert stat.S_IMODE(Paths.from_env().secrets_file.stat().st_mode) == 0o600


def test_a_token_that_the_api_refuses_writes_nothing_at_all(tmp_path, monkeypatch):
    """Ступень названа, и ни секрет, ни конфиг не тронуты: настройка либо вся, либо никакая."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from agent_kit.owner import ChannelFailed

    bot = Bot([ChannelFailed("channel-failed", "telegram getMe refused: Unauthorized")])

    with pytest.raises(ChannelFailed):
        setup(ask=typed("не-токен"), say=said_by([]), bot=bot, wait=10, pause=lambda _: None)

    from agent_kit.paths import Paths

    paths = Paths.from_env()
    assert not paths.secrets_file.exists()
    assert not paths.config_file.exists()


def test_nobody_writes_to_the_bot_in_time_and_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    bot = Bot(["vat_night_bot", ("", "", "0"), ("", "", "0"), ("", "", "0")])

    with pytest.raises(ConfigError) as refused:
        setup(ask=typed(TOKEN), say=said_by([]), bot=bot, wait=0, pause=lambda _: None)

    assert refused.value.code == "no-chat"
    from agent_kit.paths import Paths

    assert not Paths.from_env().config_file.exists()


def test_nothing_is_typed_and_the_command_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(ConfigError) as refused:
        setup(ask=typed(""), say=said_by([]), bot=Bot([]), wait=0, pause=lambda _: None)

    assert refused.value.code == "no-token"


def test_a_config_that_cannot_be_written_takes_the_token_back(tmp_path, monkeypatch):
    """Либо всё, либо ничего: токен без канала — это живой бот, о котором машина не знает."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        "agent_kit.owner.setup.write_owner_block",
        lambda *a, **k: (_ for _ in ()).throw(OSError("диск только для чтения")),
    )
    bot = Bot(["vat_night_bot", ("55", "Илья", "510")])

    with pytest.raises(OSError):
        setup(ask=typed(TOKEN), say=said_by([]), bot=bot, wait=10, pause=lambda _: None)

    from agent_kit.paths import Paths

    assert read_secret(Paths.from_env().secrets_file, TELEGRAM_TOKEN) == ""


def test_setup_reads_the_channel_under_the_readers_lease(tmp_path, monkeypatch):
    """getUpdates — на одного потребителя, и настройка не исключение из правила."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from agent_kit.machine import Ledger, ledger_path
    from agent_kit.paths import Paths

    ledger = Ledger(ledger_path(Paths.from_env()))
    # Кто-то уже читает канал: живой процесс, и это не мы.
    held = ledger.read_channel(pid=1)
    assert held.granted

    bot = Bot(["vat_night_bot"])
    with pytest.raises(ConfigError) as refused:
        setup(ask=typed(TOKEN), say=said_by([]), bot=bot, wait=0, pause=lambda _: None)

    assert refused.value.code == "no-chat"
    assert "listen" not in bot.asked, "настройка читала канал через голову держателя аренды"
