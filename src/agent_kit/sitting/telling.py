"""What the owner said, and how a record points back at it.

Every part the sitting writes has to be traceable to a line the owner said.
The obvious way is to make the model quote the words back and check the quote
is really in the telling — and that is a check, which is the weaker of the two
things a design can do. A range of lines removes the possibility instead: the
model cannot point at words nobody typed, because it does not supply the words
at all. Nothing to retype, nothing to normalise, and no argument about a comma.

    said: "L12-L14"

The telling goes into the input numbered, so the range is something the session
reads off the page rather than counts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..errors import StateError

_RANGE = re.compile(r"^L(?P<first>\d+)(?:\s*-\s*L?(?P<last>\d+))?$")


class SittingRefusal(StateError):
    """The answer satisfied its contract and is still not an answer.

    Refused like any other attempt: the reason goes into the next input and the
    session is asked again. It is not a failure of the sitting until the
    attempts run out.
    """


@dataclass(frozen=True)
class Telling:
    """The owner's own words, kept exactly as they were typed."""

    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()

    @property
    def empty(self) -> bool:
        return not self.text.strip()

    def numbered(self) -> str:
        """The telling as the session is shown it: one number per line, from one."""
        return "\n".join(f"L{number}: {line}" for number, line in enumerate(self.lines, start=1))

    def said(self, where: str, about: str) -> list[str]:
        """The lines a range names, or a named refusal.

        A range that runs off the end, or that covers nothing but blank lines,
        is a record pointing at something the owner did not say — which is the
        one thing this whole field exists to make impossible.
        """
        matched = _RANGE.match((where or "").strip())
        if matched is None:
            raise SittingRefusal(
                "not-a-range",
                f"{about}: {where!r} is not a range of the telling; it wants the shape L12 or L12-L14",
            )
        first = int(matched.group("first"))
        last = int(matched.group("last") or first)
        if first < 1 or last < first or last > len(self.lines):
            raise SittingRefusal(
                "no-such-lines",
                f"{about}: {where} names lines this telling does not have; it runs from L1 to "
                f"L{len(self.lines)}",
            )
        held = self.lines[first - 1 : last]
        if not any(line.strip() for line in held):
            raise SittingRefusal(
                "nothing-was-said", f"{about}: {where} covers nothing but blank lines"
            )
        return held
