"""A channel that is two files. What the bench answers with, and it ships.

The bench must not reach the network — a case that did would be a case that
fails on a machine with no login, which is the whole reason the bench can
compare one version of the kit against the next. So the fixture is not a mock
inside the tests: it is a channel like any other, chosen by name.
"""

from __future__ import annotations

from pathlib import Path

from .channel import ChannelFailed, Heard, understand

#: A line in the inbox may address the message it answers rather than the
#: question, which is what a reply on a phone is.
REPLY = "#"


class FileChannel:
    """`<path>.out` is what went to the owner; `<path>.in` is what came back."""

    name = "file"

    def __init__(self, path: Path | str) -> None:
        path = Path(path)
        self.out = path.with_name(path.name + ".out")
        self.inbox = path.with_name(path.name + ".in")
        #: A channel that cannot be reached, on purpose. The bench needs one:
        #: a night must go on when the token is wrong or Telegram is down, and
        #: that is a mechanism like any other, so it gets a trap like any other.
        self.broken = path.with_name(path.name + ".fail")

    def send(self, text: str) -> str:
        self._refuse_if_broken()
        self.out.parent.mkdir(parents=True, exist_ok=True)
        number = self._sent() + 1
        with self.out.open("a", encoding="utf-8") as handle:
            handle.write(f"--- {number}\n{text.rstrip()}\n")
        return str(number)

    def read(self, offset: str) -> tuple[list[Heard], str]:
        self._refuse_if_broken()
        lines = self._lines()
        already = int(offset) if offset.isdigit() else 0
        heard = [_heard(line) for line in lines[already:] if line.strip()]
        return heard, str(len(lines))

    def _sent(self) -> int:
        try:
            return sum(1 for line in self.out.read_text(encoding="utf-8").splitlines() if line.startswith("--- "))
        except OSError:
            return 0

    def _lines(self) -> list[str]:
        try:
            return self.inbox.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

    def _refuse_if_broken(self) -> None:
        if self.broken.exists():
            raise ChannelFailed(
                "channel-failed",
                f"the owner's channel is not answering: {self.broken.read_text(encoding='utf-8').strip()}",
            )


def _heard(line: str) -> Heard:
    if line.startswith(REPLY):
        message, _, text = line[len(REPLY):].partition(" ")
        return Heard(text=text.strip(), answers=message.strip())
    names, text = understand(line)
    return Heard(text=text, names=names)
