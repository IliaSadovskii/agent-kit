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
    NO_CHANNEL,
    NOBODY,
    Owner,
    Question,
    Settled,
    as_assumption,
    questions_of,
)
from .channel import Channel, ChannelFailed, understand
from .file import FileChannel
from .secrets import TELEGRAM_TOKEN, read_secret, write_secret
from .telegram import Telegram

__all__ = [
    "ANSWERED",
    "BROKEN",
    "Channel",
    "ChannelFailed",
    "FileChannel",
    "NOBODY",
    "NO_CHANNEL",
    "Owner",
    "Question",
    "Settled",
    "TELEGRAM_TOKEN",
    "Telegram",
    "as_assumption",
    "open_channel",
    "read_secret",
    "write_secret",
    "questions_of",
    "understand",
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
