"""The contract a channel to the owner satisfies, and how an answer names its question.

Two implementations ship: Telegram, which is the one settled in the plan, and a
channel that is two files, which is what the bench answers with. A channel is
chosen by name in `config.toml`, the way a provider is, and neither of them is
named anywhere outside this package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from ..errors import ProviderError
from ..knowledge.format import ALPHABET, ID_LENGTH

#: What a person types when they are not replying to the message. The identifier
#: is derived from the run and the question's own words, so it is short enough
#: to retype and a bench case can name it before the run exists.
COMMAND = "/a"

_NAMED = re.compile(rf"^[{ALPHABET}]{{{ID_LENGTH}}}$")


class ChannelFailed(ProviderError):
    """The channel could not be reached, and a night must not end because of it.

    It is somebody else's service, so it carries the code that already means
    *this cannot be reached right now* — but the driver never lets it out: a
    question whose channel is broken takes its default, and the record says
    which of the two silences it was. It reaches a person through
    `agent-kit owner check`, which is where they go to find out on purpose.
    """


@dataclass(frozen=True)
class Heard:
    """One thing a person said, before anybody knows which question it answers."""

    text: str
    #: The identifier they typed, where they typed one.
    names: str = ""
    #: The message they replied to, where the channel says. What a person
    #: actually does on a phone is reply, and this is what makes that work.
    answers: str = ""


class Channel(Protocol):
    """Send this; tell me what has come back since here."""

    name: str

    def send(self, text: str) -> str:
        """Say it, and answer with what the channel calls the message it went out as."""

    def read(self, offset: str) -> tuple[list[Heard], str]:
        """What has been said since `offset`, and the offset to ask from next."""


def understand(said: str) -> tuple[str, str]:
    """A person's message, split into the question it names and what they answered.

    Both forms, because both happen: `/a k7f3q2 one rate` is what the message
    the kit sends tells them to type, and a bare identifier is what somebody
    types when they are copying. Anything else names no question, which is not
    an error — it may be a reply to the message instead.
    """
    words = (said or "").strip().split()
    if not words:
        return "", ""
    if words[0] == COMMAND:
        words = words[1:]
        if not words:
            return "", ""
        return (words[0], " ".join(words[1:])) if _NAMED.match(words[0]) else ("", " ".join(words))
    if _NAMED.match(words[0]):
        return words[0], " ".join(words[1:])
    return "", said.strip()
