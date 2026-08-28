"""What the kit prints about a kind, and what it encloses into a step.

The plan's last sentence about the feature's level: *the kit prints what a
feature of this project owes, with the command for each, rather than leaving a
model to join two files six times a night.* The two files are the catalogue,
which is the kit's, and the answers, which are the project's. Joining them is
one function and it lives here — the door, the command a person types and the
input a session is handed all read the same sentences.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .answers import owed_by_a_feature, unanswered
from .kinds import CATALOGUE

if TYPE_CHECKING:  # pragma: no cover
    from ..project import Project


def about(kind, answer=None) -> str:
    """One kind, in the words the catalogue holds and this project's answer to it."""
    said = [f"{kind.name} — catches {kind.catches}"]
    if kind.not_for:
        said.append(f"does not apply to {kind.not_for}")
    if kind.never_skippable:
        said.append("no feature may excuse it")
    if answer is not None and answer.is_a_command:
        said.append(f"this project proves it with `{answer.command}`")
    elif answer is not None:
        said.append(f"this project does not do it: {answer.why} (decided {answer.since})")
    else:
        said.append("this project has not said anything about it")
    return "; ".join(said)


def catalogue_lines(project: "Project | None") -> list[str]:
    """Every kind the kit knows, with what this project answered. The whole list."""
    return [
        "- " + about(kind, project.answer_for(kind.name) if project is not None else None)
        for kind in CATALOGUE
    ]


def what_a_feature_owes(
    project: "Project | None",
    step: str,
    design: dict[str, Any] | None = None,
    verify: dict[str, Any] | None = None,
) -> str:
    """The enclosure, which is different for the step that decides and the one that judges.

    Empty for a project that owes nothing: an enclosure saying *there is nothing
    here* is a section a session reads and acts on, and there is nothing to act
    on. That is the ordinary state of a project nobody has answered for yet.
    """
    owed = owed_by_a_feature(project)
    if not owed:
        return ""
    if step == "review":
        return _for_the_review(design or {}, verify or {})
    return _for_the_design(project, owed)


def _for_the_design(project: "Project | None", owed) -> str:
    said = [
        "This project checks itself for the kinds below, and every feature of it decides what it",
        "owes under each one *before* any code exists. Return one record in `proves` per kind:",
        "the command this change owes, or the `why` it cannot apply here — measured against the",
        "words after *does not apply to*, which are the kit's and not yours to widen.",
        "",
    ]
    said += ["- " + about(kind, project.answer_for(kind.name) if project else None) for kind in owed]
    left = unanswered(project)
    if left:
        said += [
            "",
            "Kinds this project has not answered yet, which it therefore owes nothing under and "
            "which you do not decide about here: " + ", ".join(kind.name for kind in left) + ".",
        ]
    return "\n".join(said)


def _for_the_review(design: dict[str, Any], verify: dict[str, Any]) -> str:
    from .owed import excused, measured_paths

    excuses = excused(design)
    if not excuses:
        return ""
    measured = measured_paths(verify)
    said = [
        "This feature excused the kinds below: it says each one cannot apply to this change.",
        "Read every one of them against the change itself and return a record in `proofs`.",
        "This is the one thing no record can do for itself — every other pass reads what the",
        "design said, and only you read what was built.",
        "",
    ]
    said += [f"- {kind} — because: {why}" for kind, why in excuses.items()]
    said += [
        "",
        "What the project's commands were measured over, and the only files a contradiction may",
        "name. It is wider than this feature: a working copy legitimately holds what the feature",
        "is not about, so a file being here says the tree held it, never that this change wrote it.",
        "",
    ]
    said += [f"- {path}" for path in measured] or ["- nothing was measured in this run"]
    return "\n".join(said)
