"""The gate: what a night may not start without.

Dozens of features run afterwards with nobody watching, so the class of defect
nothing catches is asked about while the owner is still standing. That is the
whole argument, and it is the second version's own: it refused to start an epic
without a declared way to run and to test the product, and that refusal was
fatal by design.

Three things about the work, read out of the declaration, and one about the
project, read out of what it declares. Every one of them is a question a night
would otherwise have nobody to ask:

- **the bounds** — what this work is and, harder, what it is not. Without the
  second list nothing stops a session at 03:00 widening its own brief.
- **an ending per scenario** — what *finished* means for work nobody watches.
- **a way to run the project's own checks** — `no-commands`, the same code and
  the same fault `verify` refuses by, asked before anything is created rather
  than in the middle of the first feature.

One home and two callers. `agent-kit batch compose` asks before it spends a
session; `agent-kit batch new` refuses before it creates a batch, a run or a
tree. Neither holds a copy of the question.

**What is not here, and it is a seam rather than an omission.** The plan's
sentence is *a kind of verification is unanswered*, and the catalogue of kinds
— what each one catches, which session runs it, the shape of project it does
not apply to — is S8e's. The kit knows one kind today and the project answers
it in `[commands]`. When the catalogue arrives this gate does not change: it
already asks whether every kind the kit knows has an answer, over a catalogue
of one.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ConfigError
from ..project import Project
from .declaration import Declaration


@dataclass(frozen=True)
class Unanswered:
    """One thing the night would have nobody to ask. Two readers, one shape."""

    code: str
    detail: str

    def refusal(self) -> ConfigError:
        return ConfigError(self.code, self.detail)


def unanswered(declaration: Declaration, project: Project | None) -> list[Unanswered]:
    """Everything the gate found, and not only the first of it.

    All of them, because a person who fixes one line and is refused for the
    next has been made to walk the gate twice for one composing.
    """
    said: list[Unanswered] = []

    if not declaration.inside or not declaration.outside:
        said.append(
            Unanswered(
                "bounds-unwritten",
                f"{declaration.name} does not say what this work is and what it is not; both lists "
                "are the gate, and the second is the one nobody writes unasked",
            )
        )

    if not declaration.scenarios:
        said.append(
            Unanswered(
                "no-scenarios",
                f"{declaration.name} names no pass through the product, so nothing says what these "
                "features are finished for",
            )
        )
    for scenario in declaration.scenarios:
        if not scenario.ends:
            said.append(
                Unanswered(
                    "scenario-with-no-ending",
                    f"{declaration.name}: the scenario {scenario.what!r} does not say how it ends, "
                    "and an ending is what *finished* means where nobody is watching",
                )
            )

    return said + unanswered_about_the_project(project)


def unanswered_about_the_project(project: Project | None) -> list[Unanswered]:
    """The half of the gate that has nothing to do with what was composed.

    Its own function because `batch compose` asks it *before* the first session:
    a project with no way to check anything cannot start a night whatever is
    composed, and finding that out after two turns is finding it out at the
    owner's expense.
    """
    if project is not None and project.commands:
        return []
    # The same code `verify` refuses by, asked before anything is spent rather
    # than in the middle of the first feature of the night.
    where = project.source if project is not None else "this project"
    return [
        Unanswered(
            "no-commands",
            f"{where} declares no commands, so there is no way to check anything this night builds",
        )
    ]


def refuse_unless_answered(declaration: Declaration, project: Project | None) -> None:
    """The gate as a refusal: the first thing it found, with all of them named."""
    said = unanswered(declaration, project)
    if not said:
        return
    first = said[0]
    rest = "; also: " + "; ".join(one.code for one in said[1:]) if len(said) > 1 else ""
    raise ConfigError(first.code, first.detail + rest, hint="agent-kit batch compose <имя>")
