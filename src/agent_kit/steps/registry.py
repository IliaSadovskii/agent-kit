"""Which steps exist. A name means one definition, and an unknown name is refused early."""

from __future__ import annotations

from ..errors import StateError
from .contract import Bool, Contract, Enum, Int, LongText, Records, Text, TextList
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
            # Findings with a severity wait for the step that must refuse on one.
            # The contract can express them; nothing reads them until S4's deliver.
        )
    ),
)


#: design: what changes, where it meets what is already there, and — before any
#: code exists — what will prove it. The second version prescribed all three in
#: prose and checked none of them.
DESIGN = StepDefinition(
    name="design",
    role="design",
    method="roles/design.md",
    title="decide what changes, and what will prove it",
    needs_brief=True,
    contract=Contract(
        fields=(
            Text(
                "title",
                help="one line naming the feature, at most 72 characters: it becomes the commit "
                     "subject and the pull request's title, so no full stop and no essay",
            ),
            LongText("summary", help="what changes and why, in a few sentences the owner could read"),
            TextList("changes", help="each place that changes, one line each: the file and what happens to it"),
            TextList("seams", help="where this meets what is already there, and what must not break"),
            TextList(
                "verification",
                help="what will prove it works — decided here, before the code, never after",
            ),
            Records(
                "assumptions",
                required=False,
                help="what you had to take as true without checking",
                shape=(
                    Text("what", help="the assumption itself"),
                    Bool("expensive", help="true when being wrong about it would cost more than checking it"),
                    Text("because", help="why you took it as true"),
                ),
            ),
        )
    ),
)

#: build: the test first and then the code. A departure from the design is
#: allowed and must carry its cause; a departure nobody recorded is the defect.
BUILD = StepDefinition(
    name="build",
    role="build",
    method="roles/build.md",
    title="write the test, then the code that makes it pass",
    needs_brief=True,
    splittable=True,
    contract=Contract(
        fields=(
            Bool("complete", help="true only when nothing of this feature is left to write"),
            LongText("summary", help="what you did, in a few sentences"),
            TextList("files", help="every file you changed or added"),
            TextList("tests", help="the tests you wrote, by name"),
            Records(
                "deviations",
                required=False,
                help="anywhere you did not do what the design said",
                shape=(
                    Text("what", help="what you did instead"),
                    Text("because", help="why the design could not be followed here"),
                ),
            ),
            TextList(
                "remaining",
                required=False,
                help="what is still to do when `complete` is false; the next session is given this",
            ),
        )
    ),
)

#: review: a finding with no consequence is the second version's problem
#: restated. A severity is what gives it one — `blocking` refuses delivery.
REVIEW = StepDefinition(
    name="review",
    role="review",
    method="roles/review.md",
    title="read what was built against what was designed",
    needs_brief=True,
    contract=Contract(
        fields=(
            Enum(
                "verdict",
                choices=("pass", "blocked"),
                help="blocked when any finding is blocking; the program checks that they agree",
            ),
            Records(
                "findings",
                required=False,
                help="what is wrong, one record each",
                shape=(
                    Enum(
                        "severity",
                        choices=("blocking", "worth-fixing", "note"),
                        help="blocking refuses delivery; the other two ride along in the pull request",
                    ),
                    Text("what", help="the finding itself"),
                    Text("where", required=False, help="file and line, where there is one"),
                ),
            ),
        )
    ),
)

#: verify: the kit runs the project's declared commands itself. No role, no
#: session — an agent cannot lie about green tests it did not run.
VERIFY = StepDefinition(
    name="verify",
    role="verify",
    executor="program:verify",
    title="run what the project declares and record what it printed",
    gate="passed",
    contract=Contract(
        fields=(
            Records(
                "commands",
                help="each declared command, in the order it was run",
                shape=(
                    Text("name"),
                    Text("command"),
                    Int("exit_code", required=False, help="absent when it could not be run at all"),
                    Bool("passed"),
                    Text("output", required=False),
                ),
            ),
            Bool("passed", help="every command that ran came back green"),
        )
    ),
)


#: deliver: the branch, the commit, the pull request. A body composed from what
#: was already recorded cannot describe work that did not happen — which is why
#: this step, like verify, is a program and not a role.
DELIVER = StepDefinition(
    name="deliver",
    role="deliver",
    executor="program:deliver",
    title="put the work on a branch and open the pull request",
    contract=Contract(
        fields=(
            Text("branch", help="the branch the work now sits on"),
            Text("commit", help="the commit it was made in"),
            Text("pull_request", help="where the owner reads it"),
        )
    ),
)


def builtin_registry() -> Registry:
    """The steps the kit ships. S4 adds design, build, review and deliver."""
    return Registry([PROBE, DESIGN, BUILD, VERIFY, REVIEW, DELIVER])
