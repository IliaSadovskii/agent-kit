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


#: Four lists below are required and may be empty, which is not the same as
#: absent: an empty list is a step saying it considered the question and had
#: nothing, and a missing field is a step that did not answer. The measurement
#: caught the second version on exactly that gap — 14% of assumptions with
#: `expensive` unanswered, and nobody able to tell which were which.
#:
#: Three others say `empty_is_an_answer=False` outright, because for them nothing
#: is not something to have found: `changes` here, `files` and `tests` in the
#: build. A fourth, `proves`, is made that way by the project rather than by the
#: field — `verification_requires` below, on a project that answers a kind with a
#: command. A design that will prove nothing has not decided what will prove it,
#: and a build that wrote no test wrote no test.
#:
#: design: what changes, where it meets what is already there, and — before any
#: code exists — what will prove it. The second version prescribed all three in
#: prose and checked none of them.
DESIGN = StepDefinition(
    name="design",
    role="design",
    method="roles/design.md",
    title="decide what changes, and what will prove it",
    needs_brief=True,
    needs_knowledge=True,
    needs_kinds=True,
    # What a project that answers a kind of verification with a command asks of
    # a design: a record for every one of them. A project that answers none asks
    # nothing, which is every project written before this existed.
    verification_requires=(("proves", ""),),
    # What a project that keeps knowledge asks of a design, and a project that
    # keeps none does not. The join the second version never made lives here:
    # an expensive assumption owes a block, and a block owes an address.
    knowledge_requires=(
        ("assumptions.block", "expensive"),
        ("assumptions.at", "expensive"),
        # A default taken is an expensive assumption, so a question owes the
        # knowledge exactly what one does. Required outright rather than on a
        # sibling's truth: every question can end with nobody answering.
        ("asks.block", ""),
        ("asks.at", ""),
        ("closes", ""),
    ),
    contract=Contract(
        fields=(
            Text(
                "title",
                help="one line naming the feature, at most 72 characters: it becomes the commit "
                     "subject and the pull request's title, so no full stop and no essay",
            ),
            LongText("summary", help="what changes and why, in a few sentences the owner could read"),
            TextList(
                "changes",
                empty_is_an_answer=False,
                help="each place that changes, one line each: the file and what happens to it",
            ),
            TextList("seams", help="where this meets what is already there, and what must not break"),
            Records(
                "proves",
                required=False,
                help="one record per kind of verification this project answers with a command — "
                     "they are enclosed above, with what each one catches. The command this change "
                     "owes under that kind, or the `why` it cannot apply here. Decided now, before "
                     "the code: chosen afterwards, this list is written by somebody who already "
                     "knows what they built and is looking for a reason to be finished",
                shape=(
                    Text("kind", help="one of the kinds enclosed above, copied, not invented"),
                    Text(
                        "command",
                        required=False,
                        help="the command that proves this change under that kind, as it will be "
                             "run. `verify` runs it and records what it printed",
                    ),
                    Text(
                        "why",
                        required=False,
                        help="why this kind cannot apply to this change, against what the enclosed "
                             "catalogue says it does not apply to. The review reads it against the "
                             "diff, so a reason the change contradicts stops the run",
                    ),
                ),
            ),
            Records(
                "asks",
                help="anything only the owner can decide; empty when there is nothing. Each one "
                     "goes to their phone and waits; what you return must already work if "
                     "nobody answers",
                shape=(
                    Text("question", help="one line, answerable from a phone"),
                    Text(
                        "default",
                        help="what is taken if nobody answers — and what the rest of this output "
                             "was designed around. A question with no default is not a question, "
                             "it is this step refusing to finish",
                    ),
                    Text("because", required=False, help="why that default is the safe one"),
                    Text(
                        "at",
                        required=False,
                        help="where in the project's knowledge the taken default belongs, as "
                             "`file.md#anchor`, from the enclosed index",
                    ),
                    LongText(
                        "block",
                        required=False,
                        help="what the knowledge should say if the default is taken: what nobody "
                             "answered, what was taken, and what it costs to be wrong",
                    ),
                ),
            ),
            TextList(
                "fixes",
                required=False,
                help="keys of lines in the project's ledger of debt — they are in the enclosed "
                     "index — that this feature does the work of. The evening takes those lines "
                     "away when it is over; a key no line carries stops the run",
            ),
            Records(
                "manual",
                required=False,
                help="what a person must do by hand for this work to be of any use: place a "
                     "secret, apply a migration, create an account, point a domain. Empty when "
                     "there is nothing, which is a real answer. The evening writes each one into "
                     "`.agent-kit/v3/manual.md`, where it survives this machine",
                shape=(
                    Text("what", help="the action itself, one line, in the project's language"),
                    Text(
                        "proof",
                        required=False,
                        help="the command that comes back zero once this has been done — the key "
                             "is in the environment, the migration is applied, the endpoint "
                             "answers. `agent-kit manual check` runs it and takes the line away "
                             "when it passes, so nobody has to remember to tick anything. A "
                             "command that cannot fail — `true`, `:`, `yes` — is refused",
                    ),
                    Text(
                        "by_hand",
                        required=False,
                        help="why no command can prove this one, where none can: it needs a "
                             "person holding a phone. Such a line stays until somebody deletes "
                             "it, so this is the expensive answer and the short list",
                    ),
                ),
            ),
            TextList(
                "closes",
                required=False,
                help="identifiers of blocks in the project's knowledge this feature makes untrue; "
                     "the program deletes them. Empty is a real answer, and an identifier the "
                     "knowledge does not hold stops the run",
            ),
            Records(
                "assumptions",
                help="what you had to take as true without checking; empty when there was nothing",
                shape=(
                    Text("what", help="the assumption itself"),
                    Bool("expensive", help="true when being wrong about it would cost more than checking it"),
                    Text("because", help="why you took it as true"),
                    Text(
                        "at",
                        required=False,
                        help="where in the project's knowledge this belongs, as `file.md#anchor` — "
                             "one of the addresses the enclosed index prints, and nothing else",
                    ),
                    LongText(
                        "block",
                        required=False,
                        help="what the knowledge should say about it, in the project's own language: "
                             "what the record does not say, what you took, and what it costs to be "
                             "wrong. The program writes it; you do not touch the file",
                    ),
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
            TextList("files", empty_is_an_answer=False, help="every file you changed or added"),
            TextList("tests", empty_is_an_answer=False, help="the tests you wrote, by name"),
            Records(
                "deviations",
                help="anywhere you did not do what the design said; empty when you followed it",
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
                help="blocked when any finding is blocking, and pass otherwise. Delivery reads "
                     "this as well as the findings, and refuses if the two disagree",
            ),
            Records(
                "findings",
                help="what is wrong, one record each; empty when you found nothing, which is a real answer",
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
            Records(
                "proofs",
                required=False,
                help="one record per kind of verification the design excused — they are enclosed "
                     "above with the reason each one gave. This is the one thing no record can do "
                     "for itself: every other pass reads the design, and only you read the change",
                shape=(
                    Text("kind", help="the kind excused, copied from the list enclosed above"),
                    Enum(
                        "verdict",
                        choices=("stands", "contradicted"),
                        help="stands when the change leaves that reason true; contradicted when it "
                             "does not, and then the run stops here",
                    ),
                    Text(
                        "where",
                        required=False,
                        help="the file that contradicts the reason, from the enclosed list of what "
                             "the commands were measured over. Required when contradicted, and one "
                             "the list does not hold is not an answer",
                    ),
                    Text(
                        "because",
                        required=False,
                        help="what that file does that the reason says nothing here does",
                    ),
                ),
            ),
        )
    ),
    needs_kinds=True,
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
            Records(
                "kinds",
                required=False,
                help="every kind of verification this feature owed, and what proving it printed. "
                     "A kind proved by a command the project had already run in this step carries "
                     "that same result rather than a second run of the same line",
                shape=(
                    Text("kind"),
                    Text("name"),
                    Text("command"),
                    Int("exit_code", required=False),
                    Bool("passed"),
                    Text("output", required=False),
                ),
            ),
            Bool("passed", help="every command that ran came back green, the kinds included"),
            # What the result is a claim about. Its reader is `deliver`, which
            # refuses a commit that is not the tree these commands ran over.
            Text(
                "proved_at",
                required=False,
                help="the commit the working copy stood on; absent where it is no repository",
            ),
            TextList(
                "proved_over",
                required=False,
                help="every change the tree held that its commit did not, as `<state> <digest> <path>`",
            ),
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


#: record: the model returns fields, the program writes the file. S6's whole
#: sentence. It is a step of its own rather than a half of `deliver` because a
#: step leaves an output naming what it wrote, and a run that never had the step
#: is visible in its own record — where the same work folded into delivery would
#: leave a line in a log.
#:
#: It asks the deliverable question before it writes anything, so a blocking
#: finding stops the run before it reaches the owner's knowledge.
RECORD = StepDefinition(
    name="record",
    role="record",
    executor="program:record",
    title="write what was decided into the project's knowledge",
    contract=Contract(
        fields=(
            Records(
                "blocks",
                help="every block written, in the order they were written",
                shape=(
                    Text("id", help="the identifier it carries, derived from the run and the assumption"),
                    Text("at", help="the address it was written to"),
                    Text("what", help="the assumption it answers"),
                ),
            ),
            TextList("closed", help="the identifiers removed"),
            TextList("files", help="the knowledge files this changed; delivery commits them beside the code"),
            Records(
                "debt",
                required=False,
                help="what the review found, does not block, and nobody would read twice: one "
                     "record per `worth-fixing` finding, with the key its line will carry. Named "
                     "here and written by the evening, which is the one writer that file has",
                shape=(
                    Text("key", help="the key the line carries, derived from its own words"),
                    Text("what", help="the finding, as the line will say it"),
                ),
            ),
            Records(
                "manual",
                required=False,
                help="what a person must do by hand, one record per action the design named, "
                     "with the key its line will carry. Named here and written by the evening, "
                     "which is the one writer that file has",
                shape=(
                    Text("key", help="the key the line carries, derived from its own words"),
                    Text("what", help="the action, as the line will say it"),
                    Text("proof", required=False, help="the command that closes it"),
                    Text("by_hand", required=False, help="why no command can close it"),
                ),
            ),
            TextList(
                "fixed",
                required=False,
                help="the keys of the ledger's lines this feature did the work of; the evening "
                     "takes them away when there is nothing left to build",
            ),
        )
    ),
)


def builtin_registry() -> Registry:
    """The steps the kit ships. S4 added design, build, review and deliver; S6, record."""
    return Registry([PROBE, DESIGN, BUILD, VERIFY, REVIEW, RECORD, DELIVER])
