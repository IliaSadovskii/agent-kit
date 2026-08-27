"""The two turns of a composing sitting, declared the way every step of the kit is.

They are `StepDefinition`s and they are deliberately **not** in the builtin
registry: nothing about a run may order one, and `run new` refuses a step it
does not know. What they borrow is everything else — the contract, the input the
driver composes, the envelope, the workspace, the chain of attempts.

Two turns and no more. The first composes the evening; the second composes it
again with the owner's answers taken as true. A third would be a conversation,
and every handover in this kit is a file.
"""

from __future__ import annotations

from ..steps.contract import Contract, LongText, Records, Text, TextList
from ..steps.definition import StepDefinition

#: Every field has a reader, and they are three: the program that writes the
#: declaration, the program that writes the frame blocks, and the loop that puts
#: a question to the person standing here. Nothing here is printed and left.
_FEATURES = Records(
    "features",
    empty_is_an_answer=False,
    help="one record per feature of this evening. A feature is one branch, one pull request "
         "and one thing a reviewer holds in their head",
    shape=(
        Text("slug", help="its name: lowercase, hyphens, no spaces. It becomes the branch"),
        LongText(
            "brief",
            help="what this one feature builds, in enough detail that a session which has read "
                 "nothing else could build it",
        ),
        Text(
            "needs",
            required=False,
            help="the slug of the one feature this is built on and opens against; leave it out "
                 "where it stands on its own. One, never two: a pull request has one base",
        ),
        Text("said", help="the lines of the telling this comes from, as `L12` or `L12-L14`"),
        Text(
            "question",
            required=False,
            help="only where what the owner asked for is denied by what the description already "
                 "says: one line they can answer, naming both. It is the only thing that reaches "
                 "the person, so it has to stand on its own",
        ),
    ),
)

_SCENARIOS = Records(
    "scenarios",
    empty_is_an_answer=False,
    help="passes through the product on real names and real numbers, beginning to end",
    shape=(
        Text("what", help="the pass itself, in a line"),
        LongText(
            "ends",
            help="what is true when it worked — a row, a number, a message that arrived. This is "
                 "what *finished* means for work nobody is watching",
        ),
        Text("said", help="the lines of the telling this comes from"),
    ),
)

_FRAMES = Records(
    "frames",
    empty_is_an_answer=False,
    help="what every feature of this evening must build alike. At least one: an evening whose "
         "features share nothing was not looked at together, and one feature on its own is a run",
    shape=(
        LongText(
            "what",
            help="the thing, and where the pattern already stands, so a feature reading it has "
                 "something to copy rather than something to interpret",
        ),
        Text(
            "at",
            required=False,
            help="where in the project's knowledge this belongs, as `file.md#anchor` — one of the "
                 "addresses the enclosed index prints, and nothing else",
        ),
        Text("said", help="the lines of the telling this comes from"),
    ),
)

_INSIDE = TextList(
    "inside", empty_is_an_answer=False, help="what this evening builds, one line each"
)
_OUTSIDE = TextList(
    "outside",
    empty_is_an_answer=False,
    help="what it does not build. This is the half nobody writes unasked, and the only thing "
         "that keeps a session at 03:00 from widening its own brief. «And so on» is not a bound",
)

#: What a project that keeps knowledge asks of a composing, and a project that
#: keeps none does not. A frame owes an address for the same reason an expensive
#: assumption does: a block nobody can find again is a block nobody closes.
_WHERE_THE_BLOCK_GOES = (("frames.at", ""),)

COMPOSING = StepDefinition(
    name="composing",
    role="composing",
    method="roles/composing.md",
    title="turn what the owner said into an evening's work",
    needs_knowledge=True,
    knowledge_requires=_WHERE_THE_BLOCK_GOES,
    contract=Contract(fields=(_FEATURES, _INSIDE, _OUTSIDE, _SCENARIOS, _FRAMES)),
)

SETTLING = StepDefinition(
    name="settling-a-batch",
    role="settling-a-batch",
    method="roles/settling-a-batch.md",
    title="compose the evening again, with what the owner answered",
    needs_knowledge=True,
    knowledge_requires=_WHERE_THE_BLOCK_GOES,
    contract=Contract(fields=(_FEATURES, _INSIDE, _OUTSIDE, _SCENARIOS, _FRAMES)),
)
