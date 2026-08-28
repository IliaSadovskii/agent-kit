"""S6 — the project's knowledge, through the program.

The model returns fields; the program writes the file. That one sentence is
what makes the join checkable: an agent that writes the file itself can always
claim it did.
"""

from .debt import BADLY, BROKEN, LEDGER, Debt, debt_key, read_debt
from .format import ALPHABET, ASSUMED, FRAME, Anchor, Block, identifier
from .parts import DERIVED, Part, part_key, read_parts, render_part
from .store import DEFAULT_DIR, Knowledge, KnowledgeError

__all__ = [
    "ALPHABET",
    "BADLY",
    "BROKEN",
    "Debt",
    "LEDGER",
    "debt_key",
    "read_debt",
    "ASSUMED",
    "FRAME",
    "Anchor",
    "Block",
    "DERIVED",
    "Part",
    "part_key",
    "read_parts",
    "render_part",
    "DEFAULT_DIR",
    "Knowledge",
    "KnowledgeError",
    "identifier",
]
