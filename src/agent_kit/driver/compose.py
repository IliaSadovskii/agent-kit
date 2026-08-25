"""Composing a step's input.

Everything the step must read arrives enclosed. Reading is never an instruction,
so there is no reading step to skip and nothing to check that it happened.
"""

from __future__ import annotations

import re
from typing import Sequence

from ..state import Run
from ..steps import StepDefinition
from ..steps.contract import Contract

Enclosure = tuple[str, str]


def compose_input(
    run: Run,
    definition: StepDefinition,
    attempt: int,
    provider: str,
    enclosures: Sequence[Enclosure] = (),
    refusal: str | None = None,
    attempts_allowed: int = 3,
    parts_done: int = 0,
    parts_allowed: int = 0,
    contract: Contract | None = None,
) -> str:
    # What the *project* asks of this step, which may be more than the kit does.
    # The same object is checked against what comes back: one description, two
    # readers, and neither reads a description the other did not.
    contract = definition.contract if contract is None else contract
    parts = [
        f"# {definition.name} — {definition.title or definition.role}",
        "",
        f"run: {run.slug}",
        f"branch: {run.branch} — the program puts the work there at the end; do not create it",
        f"working copy: {run.tree or run.project or 'unstated'} — you are in it already",
        *([f"built on: {run.base}"] if run.base else []),
        *([f"after: {', '.join(run.needs)} — what they built is enclosed below"] if run.needs else []),
        f"provider: {provider}",
        f"attempt {attempt} of {attempts_allowed} on this provider",
        "",
    ]

    if definition.by_agent:
        parts += ["", "## What you are doing", "", definition.instructions().strip()]
    else:
        parts += [
            "",
            f"Executed by {definition.executor}, not by a session. This file is the record of",
            "what it was handed; nothing here is read by anybody as an instruction.",
        ]

    if run.brief:
        parts += ["", "## What this run is for", "", run.brief.strip()]

    if enclosures:
        parts += ["", "## What is enclosed", "", "Everything below is here so that you do not go looking for it."]
        for title, body in enclosures:
            fence = _fence_for(body)
            parts += ["", f"### {title}", "", fence, body.strip(), fence]

    if refusal:
        parts += [
            "",
            "## The previous attempt was refused",
            "",
            "The program read what came back and would not accept it:",
            "",
            f"    {refusal}",
            "",
            "Fix that. Repeating the previous answer wastes one of the attempts this step has.",
        ]

    if definition.splittable and definition.by_agent:
        left = max(parts_allowed - parts_done, 0)
        parts += [
            "",
            "## This step may be split",
            "",
            "You do not have to finish in one session. If you are running out of room, stop while you",
            "can still write a good answer: return what you did with `complete: false`, and put what is",
            "left in `remaining`, in enough detail that a session which never saw this one can carry on.",
            "",
            f"Sessions already spent on this step: {parts_done}. Sessions left after this one: {left}.",
            "Running out of them stops the run, so do not spend one on work you could have finished.",
        ]

    if definition.by_agent:
        parts += [
            "",
            "## What you must return",
            "",
            definition.output_rules().strip(),
            "",
            "### The fields of this step",
            "",
            contract.describe(),
        ]
    parts.append("")
    return "\n".join(parts)


def _fence_for(body: str) -> str:
    """A fence longer than any inside the body, so an enclosed output cannot break the input."""
    longest = max((len(run) for run in re.findall(r"`+", body)), default=0)
    return "`" * max(3, longest + 1)
