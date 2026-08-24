"""The owner's channel: the phone this machine can reach, and the question it waits on.

S7a, and its own step rather than half of S7: the daemon is about a machine's
slots and this is about a person's phone. Folding them together is what made the
second version's control surface a live session.

The arrow keeps pointing one way: this depends on the errors, on the machine's
ledger for the rows a question waits in, and on nothing else in the kit. The
driver depends on this.
"""

from .ask import (
    ANSWERED,
    BROKEN,
    HAD_ROUND,
    NO_CHANNEL,
    NOBODY,
    Owner,
    Question,
    Settled,
    as_assumption,
    questions_of,
)
from .channel import Channel, ChannelFailed, understand
from .check import RUNGS, Report, walk
from .file import FileChannel
from .secrets import TELEGRAM_TOKEN, read_secret, write_secret
from .setup import setup
from .telegram import Telegram

__all__ = [
    "ANSWERED",
    "BROKEN",
    "Channel",
    "ChannelFailed",
    "FileChannel",
    "HAD_ROUND",
    "NOBODY",
    "NO_CHANNEL",
    "Owner",
    "Question",
    "RUNGS",
    "Report",
    "Settled",
    "TELEGRAM_TOKEN",
    "Telegram",
    "as_assumption",
    "open_channel",
    "read_secret",
    "setup",
    "write_secret",
    "questions_of",
    "described",
    "understand",
    "walk",
]


#: Two, and both ship. A third would be a config block nobody asked for: one
#: channel was settled in the plan, and the other is what the bench answers with.
CHANNELS = ("telegram", "file")


def open_channel(owner, secrets) -> Channel | None:
    """The channel this machine chose, or nothing at all.

    Nothing at all is a real answer and the common one: a machine with no
    channel takes every default at once and writes it down, which is what every
    machine did before S7a and what any of them may keep doing.
    """
    from pathlib import Path

    from ..errors import ConfigError

    if not owner.channel:
        return None
    if owner.channel == "file":
        if not owner.file:
            raise ConfigError(
                "missing-key", "owner.file says where the file channel keeps its two files"
            )
        return FileChannel(owner.file)
    if owner.channel == "telegram":
        token = read_secret(secrets, TELEGRAM_TOKEN)
        if not token:
            raise ConfigError(
                "no-token",
                f"the telegram channel needs a bot token, and {Path(secrets)} holds none",
                hint="agent-kit owner set-token",
            )
        if not owner.chat:
            raise ConfigError("missing-key", "owner.chat says which chat the kit writes to")
        return Telegram(token=token, chat=owner.chat)
    raise ConfigError(
        "unknown-channel", f"{owner.channel!r} is not a channel this kit has: {', '.join(CHANNELS)}"
    )


def described(owner, secrets) -> str:
    """Одной строкой: что за канал у этой машины и всё ли у него есть.

    Здесь, а не в `doctor`: имя канала не называет никто вне этого пакета — то
    же правило, по которому имя провайдера живёт только в `providers/`.
    """
    from pathlib import Path

    if not owner.channel:
        return "канала нет — `agent-kit owner setup` заводит его целиком"
    said = f"{owner.channel}, ждёт ответа {owner.wait} с"
    if owner.channel == "telegram":
        token = "токен есть" if read_secret(secrets, TELEGRAM_TOKEN) else "токена нет"
        return f"{said}, чат {owner.chat or 'не назван'}, {token}"
    return f"{said}, {owner.file or Path()}"
