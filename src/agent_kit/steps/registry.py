"""Which steps exist. A name means one definition, and an unknown name is refused early."""

from __future__ import annotations

from ..errors import StateError
from .contract import Bool, Contract, Enum, Records, Text, TextList
from .definition import StepDefinition


class Registry:
    def __init__(self, definitions: list[StepDefinition] | None = None) -> None:
        self._by_name: dict[str, StepDefinition] = {}
        for definition in definitions or []:
            self.add(definition)

    def add(self, definition: StepDefinition) -> StepDefinition:
        if definition.name in self._by_name:
            raise StateError("step-exists", f"{definition.name} is already a step")
        self._by_name[definition.name] = definition
        return definition

    def get(self, name: str) -> StepDefinition:
        try:
            return self._by_name[name]
        except KeyError:
            raise StateError(
                "unknown-step", f"{name!r} is not a step this kit knows: {', '.join(sorted(self._by_name)) or 'none'}"
            ) from None

    def has(self, name: str) -> bool:
        return name in self._by_name

    def all(self) -> list[StepDefinition]:
        return [self._by_name[name] for name in sorted(self._by_name)]

    def names(self) -> list[str]:
        return sorted(self._by_name)


#: The probe: what a session can see from where it landed. It is also the rung
#: `provider check` will stand on — a one-shot job that returns something.
PROBE = StepDefinition(
    name="probe",
    role="probe",
    method="roles/probe.md",
    title="report what you can see from here",
    contract=Contract(
        fields=(
            Text("branch", help="the git branch this working copy has checked out"),
            Bool("can_write", help="whether you could create a file here and delete it again"),
            TextList("notes", required=False, help="anything a longer job would trip over"),
            Records(
                "findings",
                required=False,
                help="what you found, each with what it would cost",
                shape=(
                    Text("what", help="the finding, in one sentence"),
                    Enum(
                        "severity",
                        choices=("note", "advice", "blocking"),
                        help="blocking means no further work should be attempted here",
                    ),
                ),
            ),
        )
    ),
)


def builtin_registry() -> Registry:
    """The steps the kit ships. S4 adds design, build, verify and deliver."""
    return Registry([PROBE])
