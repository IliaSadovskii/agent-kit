"""Composing a step's input.

Everything the step must read arrives enclosed. Reading is never an instruction,
so there is no reading step to skip and nothing to check that it happened.
"""

from __future__ import annotations

import re
from typing import Sequence

from ..state import Run
from ..steps import StepDefinition

Enclosure = tuple[str, str]


def compose_input(
    run: Run,
    definition: StepDefinition,
    attempt: int,
    provider: str,
    enclosures: Sequence[Enclosure] = (),
    refusal: str | None = None,
    attempts_allowed: int = 3,
) -> str:
    parts = [
        f"# {definition.name} — {definition.title or definition.role}",
        "",
        f"run: {run.slug}",
        f"branch: {run.branch}",
        f"project: {run.project or 'unstated'}",
        f"provider: {provider}",
        f"attempt {attempt} of {attempts_allowed} on this provider",
        "",
        "## What you are doing",
        "",
        definition.instructions().strip(),
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

    parts += [
        "",
        "## What you must return",
        "",
        definition.output_rules().strip(),
        "",
        "### The fields of this step",
        "",
        definition.contract.describe(),
        "",
    ]
    return "\n".join(parts)


def _fence_for(body: str) -> str:
    """A fence longer than any inside the body, so an enclosed output cannot break the input."""
    longest = max((len(run) for run in re.findall(r"`+", body)), default=0)
    return "`" * max(3, longest + 1)
