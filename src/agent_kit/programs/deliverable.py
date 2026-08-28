"""Is this work deliverable at all — asked once, by whoever asks first.

Three refusals, and all three are final: a blocking finding, a verify that did
not pass, a build that never finished. None of them will have changed by the
next attempt, so none is worth a second session.

They lived in `deliver` until S6 put a step in front of it. A blocking finding
must stop the run *before* anything reaches the owner's knowledge, not after, so
`record` asks the same question with the same codes — and `deliver` keeps asking
it, because a run assembled from other steps may not have had a `record` at all.
"""

from __future__ import annotations

from typing import Any

from ..providers.base import ExecutorFailed
from ..verification.owed import contradicted

BLOCKING = "blocking"

#: A finding that is real and does not stop delivery. `record` names a line of
#: the ledger for each; `deliver` holds it to having named one. `blocking` never
#: reaches either — the run is over before them — and a `note` costs nothing and
#: blocks nothing, which is exactly what a line in somebody's ledger does not.
WORTH_FIXING = "worth-fixing"

#: The steps whose output both programs compose themselves from.
READ = ("design", "build", "verify", "review")


def read(prior: dict[str, dict[str, Any]], *also: str) -> tuple[dict, dict, dict, dict]:
    """Everything the programs read, or a refusal naming what never ran."""
    missing = [name for name in READ + also if not prior.get(name)]
    if missing:
        raise ExecutorFailed(
            "nothing-to-read",
            f"this step composes itself from what earlier steps returned, and "
            f"{', '.join(missing)} returned nothing",
            retryable=False,
        )
    return prior["design"], prior["build"], prior["verify"], prior["review"]


def where(finding: dict) -> str:
    place = finding.get("where")
    return f"{finding.get('what')} ({place})" if place else str(finding.get("what"))


def refuse_unless_deliverable(build: dict, verify: dict, review: dict) -> None:
    if not build.get("complete"):
        left = ", ".join(build.get("remaining") or []) or "it did not say what is left"
        raise ExecutorFailed(
            "build-unfinished", f"the build did not finish: {left}", retryable=False, expected=True
        )

    if not verify.get("passed"):
        failed = [
            f"{command.get('name')} exited with {command.get('exit_code')}"
            for command in (*(verify.get("commands") or []), *(verify.get("kinds") or []))
            if not command.get("passed") and command.get("command")
        ]
        raise ExecutorFailed(
            "not-verified",
            f"the project's own commands did not come back green: {', '.join(failed) or 'no command ran'}",
            retryable=False,
            expected=True,
        )

    # The verdict is the reviewer's own summary of its findings, and the two
    # must agree — a reviewer that blocks and lists nothing, or lists something
    # blocking and passes anyway, has not made a decision the program can act on.
    blocking = [finding for finding in review.get("findings") or [] if finding.get("severity") == BLOCKING]
    verdict = review.get("verdict")
    if blocking and verdict != "blocked":
        raise ExecutorFailed(
            "review-disagrees-with-itself",
            f"the verdict is {verdict!r} and yet a finding blocks: " + "; ".join(where(f) for f in blocking),
            retryable=False,
        )
    if verdict == "blocked":
        named = "; ".join(where(finding) for finding in blocking) or "and it named nothing that does"
        raise ExecutorFailed(
            "blocked-by-review", f"the review blocks delivery: {named}", retryable=False, expected=True
        )

    # An excuse the change contradicts. Its own code and not `blocked-by-review`:
    # *the review found a defect* and *the review caught a kind of test being
    # skipped* are different events, they need different things from the owner,
    # and a judge that could not tell them apart would be reading the sentence.
    #
    # It is a finding rather than a bad answer, so the reviewer is not asked
    # again: it recorded what is true, which was its work. The run stops here.
    for kind, place, because in contradicted(review):
        raise ExecutorFailed(
            f"why-the-diff-contradicts: {kind}",
            f"the design excused {kind} and {place} says otherwise: {because or 'the review gave no reason'}",
            retryable=False,
            expected=True,
        )


def expensive_of(design: dict) -> list[dict]:
    return [item for item in (design.get("assumptions") or []) if item.get("expensive")]
