"""The feature's level: what a design owes, and what the walk refuses.

A feature decides what will prove it **before it writes any code**. Chosen after
the code, that list is written by somebody who already knows what they built and
is looking for a reason to be finished.

One home and two callers, which is `deliverable.py`'s shape and its argument:

- `design` asks it of its own answer, so a session that missed a kind is told
  and can fix it in the attempt it is already in, rather than two sessions later;
- `verify` asks it again, because a run assembled from other steps may carry no
  `design` at all — and then nothing has answered for a kind the project owes.

The two express the same judgement in their own vocabulary. A session's answer
is refused and asked again; a program's is a failure that a second attempt
cannot change. That is why the judgement raises its own error and neither caller
raises the other's: an attempt refused and a step failed are different events.

**What the bench holds and what it does not.** Each branch below has a trap on
the design's side of it, and `kind-unproved` has a second one on verify's side —
`a-run-that-skips-the-design`, which is the world where no design answered at
all. The other branches reached through `verify` — `kind-cannot-be-excused` and
`kind-excused-and-commanded` on a run assembled without a design — have no trap:
the same design output cannot be both absent and wrong, so the world that would
plant them is the world that has no design in it. Tests hold that side. Said here
rather than counted as measured.

`kind-not-owed`, `kind-named-twice` and `excuse-unjudged` are the white lists,
and one of the three has a trap (`where-nobody-measured`). The other two are held
by tests.

Two more things here were broken by hand and no case reddened, so tests and these
words are all that hold them. `proving` builds its list from what the project owes
rather than from what came back — build it from the rows instead and the bench
does not notice. `recount_the_proofs` runs its loop on a feature that excused
nothing — put the early return back and the bench does not notice that either.
Both want the same world the bench has none of: a session naming a kind its
project never answered. That is a case to write, not a line, and it is not in
this step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from ..errors import ExitCode, KitError
from .answers import owed_by_a_feature, proves_nothing
from .kinds import Kind, kind_named

if TYPE_CHECKING:  # pragma: no cover
    from ..project import Project


class UnprovedKind(KitError):
    """A feature's list does not answer for a kind the project owes.

    Its own class because its two callers turn it into two different events, and
    a code that meant both would be a code that means one thing to nobody.
    """

    exit_code = ExitCode.STATE


def proving(design: dict[str, Any], owed: tuple[Kind, ...]) -> list[tuple[str, str]]:
    """Every kind this project owes that the feature answered with a command.

    Built from the *owed* list and not from what came back, which is the
    difference between a white list and a session choosing what a program runs.
    A row naming a kind the project never answered is not a kind: on a project
    that has answered none — every project written before this — the list is
    empty whatever the design returned, and `verify` runs nothing out of it.
    """
    rows = {str(row.get("kind") or "").strip(): row for row in design.get("proves") or []}
    said = []
    for kind in owed:
        command = str((rows.get(kind.name) or {}).get("command") or "").strip()
        if command:
            said.append((kind.name, command))
    return said


def excused(design: dict[str, Any]) -> dict[str, str]:
    """Every kind this feature said cannot apply here, and why it said so."""
    return {
        str(row.get("kind") or ""): str(row.get("why") or "").strip()
        for row in design.get("proves") or []
        if str(row.get("why") or "").strip() and not str(row.get("command") or "").strip()
    }


def refuse_unless_every_kind_is_answered(design: dict[str, Any], project: "Project | None") -> None:
    """Every kind this project owes, against what the design returned.

    A project that owes nothing is asked nothing: the list is empty, the loops
    do not run, and a design written before this existed is exactly as good as
    it was. That is not leniency, it is the state of a project nobody has asked
    about a kind of verification yet, and the door is where it is named.
    """
    owed = owed_by_a_feature(project)
    if not owed:
        return

    by_name = {kind.name: kind for kind in owed}
    rows: dict[str, dict[str, Any]] = {}
    for row in design.get("proves") or []:
        name = str(row.get("kind") or "").strip()
        if name not in by_name:
            known = kind_named(name)
            raise UnprovedKind(
                f"kind-not-owed: {name}",
                f"{name!r} is not one of the kinds this project answers with a command "
                f"({', '.join(by_name)})"
                + ("" if known else "; it is not a kind this kit knows at all"),
            )
        if name in rows:
            raise UnprovedKind(
                f"kind-named-twice: {name}", f"{name} already has a record above this one"
            )
        rows[name] = row

    for kind in owed:
        _judge(kind, rows.get(kind.name))


def _judge(kind: Kind, row: dict[str, Any] | None) -> None:
    if row is None:
        raise UnprovedKind(
            f"kind-unproved: {kind.name}",
            f"this project checks itself for {kind.name} — {kind.catches} — and the design says "
            "nothing about it; silence about a kind is a refusal rather than a pass",
        )
    command = str(row.get("command") or "").strip()
    why = str(row.get("why") or "").strip()
    if command and why:
        raise UnprovedKind(
            f"kind-excused-and-commanded: {kind.name}",
            f"{kind.name} carries both a command and a reason it cannot apply here, and a record "
            "that says both has decided neither: the excuse means nothing runs, and the command "
            "claims something did",
        )
    if not command and not why:
        raise UnprovedKind(
            f"kind-unproved: {kind.name}",
            f"{kind.name} has a record with neither a command nor a reason, which is what a test "
            "written in the build and never started looks like",
        )
    if why and kind.never_skippable:
        raise UnprovedKind(
            f"kind-cannot-be-excused: {kind.name}",
            f"{kind.name} is the one kind no feature may excuse, and this one excuses it: {why}",
        )
    empty = proves_nothing(command)
    if empty:
        # The same question the project's own answer is held to, asked of the
        # side that decides whether *this change* is proved. It is here rather
        # than at the walk so that a session is told in the attempt it is
        # already in, and so that no program ever runs the string unexamined.
        raise UnprovedKind(
            f"command-that-proves-nothing: {kind.name}",
            f"{kind.name} is proved by {command!r}, and {empty!r} exits zero whatever is wrong; "
            "a command that cannot fail proves nothing about this change",
        )


# --- what the review judged, against what the program measured --------------


def measured_paths(verify: dict[str, Any]) -> list[str]:
    """The files the project's commands were measured over, by name.

    `verify` already wrote them — `<state> <digest> <path>` per change the tree
    held that its commit did not — so the review's white list is a reading of a
    measurement that exists rather than a second measurement of the same tree.

    Wider than this feature's diff, and deliberately so: a working copy
    legitimately holds what the feature is not about. A path from this list is
    evidence that the tree held it, never that the feature wrote it.
    """
    paths = []
    for line in verify.get("proved_over") or []:
        _, _, rest = str(line).strip().partition(" ")
        _, _, path = rest.partition(" ")
        if path:
            paths.append(path)
    return paths


def recount_the_proofs(
    review: dict[str, Any], design: dict[str, Any], verify: dict[str, Any]
) -> None:
    """Every judgement the review returned, against what was measured.

    Refusals here are about the *answer*, not about the code: a row naming a
    kind nobody excused, an excuse nobody judged, a contradiction resting on a
    file that was never measured. All three are asked again.

    What a substantiated contradiction *means* is not decided here. That is a
    finding, the run stops on it, and it is `deliverable.py` that says so — the
    same place a blocking finding is read, for the same reason: the reviewer did
    its work and recorded the truth, so the step passed.
    """
    from ..steps.contract import ContractRefusal

    # No early return on a feature that excused nothing. The loop below is what
    # holds a row to something: leaving it unrun there let a review contradict an
    # excuse that was never made, on a file nobody measured, and stop the night
    # on it. `kind-not-owed` is what an empty list says to any row at all.
    owed = excused(design)
    measured = set(measured_paths(verify))
    judged: set[str] = set()
    for row in review.get("proofs") or []:
        name = str(row.get("kind") or "").strip()
        if name not in owed:
            raise ContractRefusal(
                f"kind-not-owed: {name}",
                f"{name!r} is not one of the kinds this feature excused "
                f"({', '.join(owed) or 'it excused none'})",
            )
        judged.add(name)
        if str(row.get("verdict") or "") != CONTRADICTED:
            continue
        where = str(row.get("where") or "").strip()
        if not measured:
            raise ContractRefusal(
                f"nothing-was-measured: {name}",
                "this run holds no measurement of the tree, so nothing here can contradict an "
                "excuse; a contradiction resting on nothing is an invented finding",
            )
        if where not in measured:
            raise ContractRefusal(
                f"where-nobody-measured: {name}",
                (
                    "a contradiction says nothing without the file it stands on"
                    if not where
                    else f"{where!r} is not one of the {len(measured)} files the project's commands "
                    "were measured over"
                )
                + ", and a contradiction may only stand on one of them",
            )

    for name in owed:
        if name not in judged:
            raise ContractRefusal(
                f"excuse-unjudged: {name}",
                f"the design excused {name} and nothing here says whether the diff leaves that "
                "standing; every other pass reads the record rather than the change",
            )


#: The one verdict that is a judgement about the code rather than about the excuse.
CONTRADICTED = "contradicted"


def contradicted(review: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Every excuse the review says the diff contradicts: the kind, where, and why."""
    return [
        (
            str(row.get("kind") or ""),
            str(row.get("where") or ""),
            str(row.get("because") or ""),
        )
        for row in review.get("proofs") or []
        if str(row.get("verdict") or "") == CONTRADICTED
    ]


# --- what the driver hands each step ----------------------------------------


def recount_for(
    step: str, prior: dict[str, dict[str, Any]], project: "Project | None"
) -> Callable[[dict[str, Any]], None] | None:
    """The check a step's answer is held to beyond its own fields, or nothing.

    Two steps have one, and both need something the contract cannot hold: what
    the *project* owes, and what an earlier step *measured*. So it is built here,
    where both are in hand, and handed to the contract the driver renders.
    """
    from ..steps.contract import ContractRefusal

    if step == "design":
        # Gathered, never a single check hung inside another: what a *project*
        # owes is answered by most projects with nothing, and a check hung
        # inside that branch is a check nobody performs. S8g's manual actions
        # are owed by every project, and would have vanished on the same hook.
        checks: list[Callable[[dict[str, Any]], None]] = []

        if owed_by_a_feature(project):
            def design_answers_for_every_kind(output: dict[str, Any]) -> None:
                try:
                    refuse_unless_every_kind_is_answered(output, project)
                except UnprovedKind as unproved:
                    # A session's answer, so it is refused and asked again with
                    # the reason enclosed. The same judgement reaches `verify`
                    # as a failure, because by then nobody can fix it.
                    raise ContractRefusal(unproved.code, unproved.detail) from None

            checks.append(design_answers_for_every_kind)

        def design_answers_for_every_action(output: dict[str, Any]) -> None:
            from ..manual import ManualRefused, refuse_unless_each_action_is_answered

            try:
                refuse_unless_each_action_is_answered(output)
            except ManualRefused as refused:
                # Mended in the attempt it is already in. `record` asks the same
                # question again, because a run assembled from other steps may
                # carry no design at all — and there it is a step that failed.
                raise ContractRefusal(refused.code, refused.detail) from None

        checks.append(design_answers_for_every_action)

        def design_answers(output: dict[str, Any]) -> None:
            for one in checks:
                one(output)

        return design_answers

    if step == "review":
        # Whatever the run holds. A run with no design in it excused nothing,
        # and a judgement about nothing is exactly what must not be acted on.
        design = prior.get("design") or {}
        verify = prior.get("verify") or {}

        def review_judged_every_excuse(output: dict[str, Any]) -> None:
            recount_the_proofs(output, design, verify)

        return review_judged_every_excuse

    return None
