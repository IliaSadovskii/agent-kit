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

#: A step done by a session. Anything else names a program the kit ships, and
#: the role table is not consulted for it — see `programs/`.
AGENT = "agent"


@lru_cache(maxsize=1)
def method_root() -> Path:
    """Where `method/` lives — beside the package once installed, at the repository root in a checkout."""
    packaged = Path(__file__).resolve().parent.parent / METHOD_DIR_NAME
    if packaged.is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[3] / METHOD_DIR_NAME
    if checkout.is_dir():
        return checkout
    raise StateError("no-method", f"в этой установке нет каталога {METHOD_DIR_NAME}/ — прозы метода")


def read_method(relative: str) -> str:
    path = method_root() / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise StateError("missing-method", f"{relative} нет в методе кита: {error}") from error


@dataclass(frozen=True)
class StepDefinition:
    name: str
    role: str
    contract: Contract
    #: The role's prose. Empty for a step a program executes: nobody reads
    #: instructions to a program, and prose with no reader is not written.
    method: str = ""
    title: str = ""
    #: Prose every step carries: how an output is returned at all.
    envelope: str = "rules/output.md"
    #: `AGENT`, or the name of a program the kit ships.
    executor: str = AGENT
    #: A step that cannot be composed without knowing what is being built.
    #: `create_run` refuses a run of such steps with no brief.
    needs_brief: bool = False
    #: A boolean field of this step's own output that the run may not pass with
    #: false. The step itself succeeded — it recorded what is true — and what is
    #: true is that the run must not go on. Empty when the step gates nothing.
    gate: str = ""
    #: True when this step decides where something goes in the project's
    #: knowledge. The driver encloses an index of it; the step is never sent to
    #: go and find it, because a prescribed reading leaves no trace.
    needs_knowledge: bool = False
    #: What a project that keeps knowledge makes required of this step's output:
    #: `(path, the sibling whose truth requires it)`. Empty for every step but
    #: `design`, and it is here rather than in the contract because the contract
    #: is the kit's and this is the project's.
    knowledge_requires: tuple[tuple[str, str], ...] = ()
    #: What a project that answers a kind of verification with a command makes
    #: required of this step's output. Here rather than in the contract for the
    #: same reason `knowledge_requires` is: the contract is the kit's and this is
    #: the project's. `(path, the sibling whose truth requires it)`, and an empty
    #: answer is no answer — a feature that will prove nothing has not decided
    #: what will prove it.
    verification_requires: tuple[tuple[str, str], ...] = ()
    #: True when this step must be told which kinds of verification this project
    #: checks itself for. The driver encloses the catalogue's own words about
    #: each one, so an excuse is written against them rather than against a
    #: session's memory of what the kind is for.
    needs_kinds: bool = False
    #: Open question 5, the ceiling inside a step. A step that may be split is
    #: continued in a fresh session with what the previous one produced. A step
    #: that may not and outgrows its window is a design error, not a survival.
    splittable: bool = False

    @property
    def by_agent(self) -> bool:
        return self.executor == AGENT

    def contract_in(self, keeps_knowledge: bool, owes_kinds: bool = False) -> Contract:
        """The contract this project imposes, which is the one the agent is shown."""
        contract = self.contract
        if keeps_knowledge:
            for path, when in self.knowledge_requires:
                contract = contract.requiring(path, when=when)
        if owes_kinds:
            for path, when in self.verification_requires:
                contract = contract.requiring(path, when=when, empty_is_an_answer=False)
        return contract

    def instructions(self) -> str:
        return read_method(self.method) if self.method else ""

    def output_rules(self) -> str:
        return read_method(self.envelope)
