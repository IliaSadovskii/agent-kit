"""A batch: an evening's work as a graph of ordinary runs.

Nothing below this package knows what a batch is — not the runner, not a step,
not an adapter, not the ledger. That is the test of the shape: if anything below
had to import this, a batch would be a concept inside the driver rather than a
layer above it.
"""

from .driver import BatchDriver, BatchOutcome
from .declaration import Declaration, Feature, read_declaration
from .state import Batch, BatchStore, FeatureState, FeatureStatus

__all__ = [
    "Batch",
    "BatchDriver",
    "BatchOutcome",
    "BatchStore",
    "Declaration",
    "Feature",
    "FeatureState",
    "FeatureStatus",
    "read_declaration",
]
