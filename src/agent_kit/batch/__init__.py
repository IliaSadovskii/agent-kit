"""A batch: an evening's work as a graph of ordinary runs.

Nothing below this package knows what a batch is — not the runner, not a step,
not an adapter, not the ledger. That is the test of the shape: if anything below
had to import this, a batch would be a concept inside the driver rather than a
layer above it.
"""

from .driver import BatchDriver, BatchOutcome
from .declaration import (
    Declaration, Feature, Frame, Scenario, read_declaration, render_declaration,
)
from .gate import Unanswered, refuse_unless_answered, unanswered
from .state import (
    Batch, BatchStore, DebtState, FeatureState, FeatureStatus, FrameState, ManualState,
)

__all__ = [
    "Batch",
    "BatchDriver",
    "BatchOutcome",
    "BatchStore",
    "DebtState",
    "ManualState",
    "Declaration",
    "Feature",
    "FeatureState",
    "FeatureStatus",
    "Frame",
    "FrameState",
    "Scenario",
    "Unanswered",
    "read_declaration",
    "refuse_unless_answered",
    "render_declaration",
    "unanswered",
]
