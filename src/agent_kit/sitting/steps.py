"""The two turns of a sitting, declared the way every step of the kit is.

They are `StepDefinition`s and they are deliberately **not** in the builtin
registry: nothing about a run may order one, and `run new` refuses a step it
does not know. What they borrow is everything else — the contract, the input
the driver composes, the envelope, the workspace, the chain of attempts.

Two turns and no more. The first reads the telling against what is written
down; the second settles only what the owner was asked about. A third would be
a conversation, and every handover in this kit is a file.
"""

from __future__ import annotations

from ..steps.contract import Contract, Enum, LongText, Records, Text
from ..steps.definition import StepDefinition

NEW = "new"
REFINES = "refines"
CONTRADICTS = "contradicts"
UNCHANGED = "unchanged"
VERDICTS = (NEW, REFINES, CONTRADICTS, UNCHANGED)

BADLY = "badly"
BROKEN = "broken"

#: Every field below has a reader, and the readers are the program that writes
#: the files and the program that asks the owner. `key` finds the line to
#: replace; `name` and `says` are the line; `said` is the range of the telling
#: the line came from, which is what makes the record traceable; `verdict`
#: decides between writing, replacing, leaving alone and asking; `question` is
#: what is put to the owner. Nothing here is printed and left at that.
_PARTS = Records(
    "parts",
    help="one record for every part of the product this project has written down — all of "
         "them, including the ones this telling did not move — and one more for every part "
         "the telling adds",
    shape=(
        Text(
            "key",
            required=False,
            help="the key of the part, copied from the enclosed index. Leave it out for a "
                 "part that is new: the program derives one from the name",
        ),
        Enum(
            "verdict",
            choices=VERDICTS,
            help="new — the telling adds this part; refines — it says more about a part that "
                 "is written down; contradicts — it says something the written part denies; "
                 "unchanged — the telling did not touch it, and saying so is the work",
        ),
        Text("name", required=False, help="the part's own name, in the project's language; not needed when unchanged"),
        LongText(
            "says",
            required=False,
            help="what the part should now say, one line's worth; not needed when unchanged",
        ),
        Text(
            "said",
            required=False,
            help="the lines of the telling this comes from, as `L12` or `L12-L14`. Not needed "
                 "when unchanged, and required for everything else: a part nobody can point "
                 "at in the telling is a part nobody told",
        ),
        Text(
            "question",
            required=False,
            help="required when the verdict is contradicts, and pointless otherwise: one line "
                 "the owner can answer, naming what is written down and what they just said",
        ),
    ),
)

READING = StepDefinition(
    name="reading",
    role="reading",
    method="roles/reading.md",
    title="read what the owner just said against what is written down",
    needs_knowledge=True,
    contract=Contract(
        fields=(
            _PARTS,
            Records(
                "ledger",
                help="what the telling says about work that exists and is wrong — not about what "
                     "the product must do. Empty is a real answer",
                shape=(
                    Text("what", help="the one thing, in a line"),
                    Enum(
                        "kind",
                        choices=(BADLY, BROKEN),
                        help="badly — it does what it should and does it badly; broken — it does "
                             "not work at all",
                    ),
                    Text("said", help="the lines of the telling this comes from, as `L12` or `L12-L14`"),
                ),
            ),
        )
    ),
)

SETTLING = StepDefinition(
    name="settling",
    role="settling",
    method="roles/settling.md",
    title="settle the contradictions the owner has now answered",
    needs_knowledge=True,
    contract=Contract(fields=(_PARTS,)),
)
