"""What a step is, declared.

A definition is data: which role does it, which prose it carries, what it must
return. The driver reads all three; nothing about a provider appears here.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..errors import StateError
from .contract import Contract

#: The prose the driver encloses. Shipped with the kit, read from disk.
METHOD_DIR_NAME = "method"


@lru_cache(maxsize=1)
def method_root() -> Path:
    """Where `method/` lives — beside the package once installed, at the repository root in a checkout."""
    packaged = Path(__file__).resolve().parent.parent / METHOD_DIR_NAME
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[3] / METHOD_DIR_NAME
    if checkout.is_dir():
        return checkout
    raise StateError("no-method", f"the kit's {METHOD_DIR_NAME}/ directory is missing from this installation")


def read_method(relative: str) -> str:
    path = method_root() / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise StateError("missing-method", f"{relative} is not in the kit's method: {error}") from error


@dataclass(frozen=True)
class StepDefinition:
    name: str
    role: str
    method: str
    contract: Contract
    title: str = ""
    #: Prose every step carries: how an output is returned at all.
    envelope: str = "rules/output.md"

    def instructions(self) -> str:
        return read_method(self.method)

    def output_rules(self) -> str:
        return read_method(self.envelope)
