"""The kinds of verification the kit knows, and what each one catches.

One home, and nothing holds a copy. The second version kept the same list in
two places with nothing to make them agree, so no `project.toml`, no role's
prose and no template names a kind: what a step must read is enclosed into it
from here, and a project answers the list rather than restating it.

**A kind says what defect it catches, never a tool.** Tools differ per
ecosystem and this list may not: `mypy` is one project's answer to `types` and
`tsc` is another's, and a catalogue naming either would be a catalogue about
Python or about TypeScript.

Three of them, and the count is a decision rather than the end of the list.
Nine more are named in the plan; each is three lines here and no new mechanism,
so they arrive when a project has an answer for them. What earns its place
today is the spread: one kind that may never be excused, and two that may, with
different shapes of project behind the excuse.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kind:
    """One kind of verification, and what a project is asked about it."""

    name: str
    #: The defect it catches, in the words a person would use about their own
    #: product. Enclosed into `design`, where a feature decides what it owes.
    catches: str
    #: The shape of project it does not apply to. Empty where there is none:
    #: some kinds apply to everything anybody builds. Enclosed with `catches`,
    #: so an excuse is written against the kit's own words rather than a
    #: session's memory of what the kind is for.
    not_for: str = ""
    #: A kind no feature may excuse. `verify` refuses a `why` against one.
    never_skippable: bool = False


SUITE = Kind(
    name="suite",
    catches="code that worked and stopped working",
    never_skippable=True,
)

TYPES = Kind(
    name="types",
    catches="a value used as something it is not, found without running the code",
    not_for="a stack with no static types to check",
)

END_TO_END = Kind(
    name="end-to-end",
    catches="the parts pass separately and the product does not work together",
    not_for="a library with no runnable product of its own",
)

#: In the order a project is asked about them, and the order every list prints.
CATALOGUE: tuple[Kind, ...] = (SUITE, TYPES, END_TO_END)


def kind_named(name: str) -> Kind | None:
    """The kind by that name, or nothing at all — never an invented one."""
    return next((kind for kind in CATALOGUE if kind.name == name), None)


def names() -> tuple[str, ...]:
    return tuple(kind.name for kind in CATALOGUE)
