"""What a lens is, and how the kit finds the one that was asked for.

Six are named in the plan and one is built. A lens is not a step of a run and
not a role of the method: it is a way of looking at a commit that produces a
report and a list of work, and the driver below knows nothing about which one
it is holding.

Five things, and each of them has exactly one reader — the driver:

    measure     what the program works out before anybody is asked anything
    enclose     that measurement, as the session is shown it
    judge       the answer, checked against the measurement
    report      what the person reads
    candidates  the lines a composing sitting can be given

A lens that cannot supply all five is not a lens; it is a report nobody can
check, which is the audit the second version had.
"""

from __future__ import annotations

from typing import Any

from ..errors import UsageError
from ..steps import StepDefinition


class Lens:
    """One way of looking at a commit. Subclasses are in `lenses/`."""

    name: str = ""
    #: One line, printed by `--help` and standing at the top of the report.
    title: str = ""
    definition: StepDefinition

    def measure(self, tree, unpacked) -> Any:
        raise NotImplementedError

    def enclose(self, measured: Any) -> list[tuple[str, str]]:
        raise NotImplementedError

    def inventory(self, measured: Any) -> dict:
        """The measurement as it goes to disk, before the first session.

        On disk first for the reason a telling is: it is what every row of the
        answer is checked against, and it must survive the session dying, the
        machine being full and the person closing the terminal.
        """
        raise NotImplementedError

    def judge(self, output: dict, measured: Any) -> Any:
        raise NotImplementedError

    def report(self, measured: Any, judged: Any, name: str) -> str:
        raise NotImplementedError

    def candidates(self, measured: Any, judged: Any, today: str) -> str:
        """The lines a sitting composes from. Empty where there is no work."""
        raise NotImplementedError

    def said(self, measured: Any, judged: Any) -> list[str]:
        """What the person at the terminal is told, in their own language."""
        raise NotImplementedError


def lenses() -> dict[str, Lens]:
    from .lenses.dependencies import DependencyLens

    return {DependencyLens.name: DependencyLens()}


def lens_named(name: str) -> Lens:
    found = lenses().get(name)
    if found is None:
        raise UsageError(
            "unknown-lens",
            f"{name!r} is not a lens this kit has: {', '.join(sorted(lenses())) or 'none'}",
        )
    return found
