"""What proves a feature, and what a project checks itself for.

Two levels and one catalogue. `kinds.py` is the catalogue — the kit's, and the
only copy of it. `answers.py` is what a project says about each kind.
`owed.py` is the feature's level: what a design owes, and what `verify` walks
rather than deciding again.
"""

from .answers import (
    ANSWER_KEYS,
    Answer,
    answers_from_table,
    commands_that_prove_nothing,
    owed_by_a_feature,
    proves_nothing,
    refuse_commands_that_prove_nothing,
    render,
    unanswered,
)
from .kinds import CATALOGUE, Kind, kind_named, names

__all__ = [
    "ANSWER_KEYS",
    "Answer",
    "CATALOGUE",
    "Kind",
    "answers_from_table",
    "commands_that_prove_nothing",
    "kind_named",
    "names",
    "owed_by_a_feature",
    "proves_nothing",
    "refuse_commands_that_prove_nothing",
    "render",
    "unanswered",
]
