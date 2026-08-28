"""S8e — the feature's level: what a design owes, and what verify walks.

`design` returns one record per kind whose answer is a command: the command
this change owes, or the `why` it cannot apply here. `verify` walks that list
rather than deciding again. Silence about a kind is a refusal, not a pass; a
never-skippable kind cannot be excused; and the review's judgement of an excuse
may only name a file the commands were actually measured over.
"""

import pytest

from agent_kit.errors import ExitCode
from agent_kit.project import PROJECT_FILE, require_project
from agent_kit.steps import builtin_registry
from agent_kit.steps.contract import Contract, ContractRefusal, Text, TextList
from agent_kit.verification.owed import (
    UnprovedKind,
    excused,
    proving,
    recount_the_proofs,
    refuse_unless_every_kind_is_answered,
)


def declare(root, text):
    path = root / ".agent-kit/v3" / PROJECT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path):
    declare(
        tmp_path,
        '[commands]\ntest = "sh check.sh"\n\n'
        '[verification.suite]\ncommand = "sh check.sh"\n\n'
        '[verification.types]\ncommand = "sh types.sh"\n',
    )
    return require_project(tmp_path)


@pytest.fixture
def asks_nothing(tmp_path):
    declare(tmp_path, '[commands]\ntest = "sh check.sh"\n')
    return require_project(tmp_path)


PROVED = {
    "proves": [
        {"kind": "suite", "command": "sh check.sh"},
        {"kind": "types", "why": "this change adds no code, only prose"},
    ]
}


# --- the walk, and its four refusals ----------------------------------------


def test_a_design_that_answers_every_kind_it_owes_is_let_through(project):
    refuse_unless_every_kind_is_answered(PROVED, project)


def test_a_project_that_owes_nothing_asks_nothing_of_a_design(asks_nothing):
    refuse_unless_every_kind_is_answered({}, asks_nothing)


def test_silence_about_a_kind_is_a_refusal_and_not_a_pass(project):
    silent = {"proves": [{"kind": "suite", "command": "sh check.sh"}]}

    with pytest.raises(UnprovedKind) as refused:
        refuse_unless_every_kind_is_answered(silent, project)

    assert refused.value.code == "kind-unproved: types"
    assert refused.value.exit_code == ExitCode.STATE


def test_a_record_with_neither_a_command_nor_a_reason_is_the_same_silence(project):
    empty = {"proves": [{"kind": "suite", "command": "sh check.sh"}, {"kind": "types"}]}

    with pytest.raises(UnprovedKind) as refused:
        refuse_unless_every_kind_is_answered(empty, project)

    assert refused.value.code == "kind-unproved: types"


def test_a_record_that_both_commands_and_excuses_is_not_a_decision(project):
    both = {
        "proves": [
            {"kind": "suite", "command": "sh check.sh"},
            {"kind": "types", "command": "sh types.sh", "why": "no types here"},
        ]
    }

    with pytest.raises(UnprovedKind) as refused:
        refuse_unless_every_kind_is_answered(both, project)

    assert refused.value.code == "kind-excused-and-commanded: types"


def test_a_kind_the_catalogue_never_lets_go_cannot_be_excused(project):
    excusing = {
        "proves": [
            {"kind": "suite", "why": "there is nothing to test here"},
            {"kind": "types", "command": "sh types.sh"},
        ]
    }

    with pytest.raises(UnprovedKind) as refused:
        refuse_unless_every_kind_is_answered(excusing, project)

    assert refused.value.code == "kind-cannot-be-excused: suite"


def test_a_record_for_a_kind_nobody_owes_may_not_ride_along(project):
    invented = {
        "proves": [
            {"kind": "suite", "command": "sh check.sh"},
            {"kind": "types", "command": "sh types.sh"},
            {"kind": "end-to-end", "command": "sh e2e.sh"},
        ]
    }

    with pytest.raises(UnprovedKind) as refused:
        refuse_unless_every_kind_is_answered(invented, project)

    assert refused.value.code == "kind-not-owed: end-to-end"


def test_one_kind_may_not_have_two_records(project):
    twice = {
        "proves": [
            {"kind": "suite", "command": "sh check.sh"},
            {"kind": "suite", "command": "sh other.sh"},
            {"kind": "types", "command": "sh types.sh"},
        ]
    }

    with pytest.raises(UnprovedKind) as refused:
        refuse_unless_every_kind_is_answered(twice, project)

    assert refused.value.code == "kind-named-twice: suite"


def test_what_the_walk_will_run_and_what_it_will_not(project):
    assert proving(PROVED) == [("suite", "sh check.sh")]
    assert excused(PROVED) == {"types": "this change adds no code, only prose"}


# --- the design's contract, which the project makes stricter ----------------


def test_a_project_that_owes_nothing_leaves_the_design_contract_alone():
    definition = builtin_registry().get("design")

    assert definition.contract_in(False, False).field("proves").required is False


def test_a_project_that_owes_a_kind_makes_the_record_required_and_non_empty():
    definition = builtin_registry().get("design")

    field = definition.contract_in(False, True).field("proves")

    assert field.required is True
    assert field.empty_is_an_answer is False


def test_the_design_no_longer_carries_a_field_whose_reader_is_a_printer():
    # `verification` was a list of sentences whose only reader was the printer
    # that folded it into the pull request. `proves` replaced it, and rule 5
    # deletes rather than documents.
    assert builtin_registry().get("design").contract.field("verification") is None


def test_making_a_field_required_keeps_the_kind_of_contract_it_was_asked_of():
    class Stricter(Contract):
        pass

    contract = Stricter(fields=(TextList("proves"),))

    assert isinstance(contract.requiring("proves"), Stricter)


def test_a_field_can_be_made_one_an_empty_answer_does_not_satisfy():
    contract = Contract(fields=(TextList("proves"),)).requiring("proves", empty_is_an_answer=False)

    with pytest.raises(ContractRefusal) as refused:
        contract.check({"proves": []})

    assert refused.value.code == "output-empty-field: proves"


def test_a_contract_can_be_checked_against_something_it_was_measured_over():
    from agent_kit.steps.contract import CheckedAgainst

    def recount(output):
        raise ContractRefusal("where-nobody-measured: types", "money.py was not measured")

    contract = CheckedAgainst(fields=(Text("kind"),), recount=recount)

    with pytest.raises(ContractRefusal) as refused:
        contract.check({"kind": "types"})

    assert refused.value.code == "where-nobody-measured: types"


# --- the review's judgement of an excuse ------------------------------------


VERIFIED = {
    "proved_at": "abc123",
    "proved_over": [" M 0123456789abcdef money.py", "?? fedcba9876543210 notes.txt"],
}


def test_an_excuse_the_diff_leaves_standing_is_let_through():
    recount_the_proofs(
        {"proofs": [{"kind": "types", "verdict": "stands"}]}, PROVED, VERIFIED
    )


def test_a_contradiction_may_only_name_a_file_the_commands_ran_over():
    contradicted = {
        "proofs": [
            {"kind": "types", "verdict": "contradicted", "where": "invented.py", "because": "it types things"}
        ]
    }

    with pytest.raises(ContractRefusal) as refused:
        recount_the_proofs(contradicted, PROVED, VERIFIED)

    assert refused.value.code == "where-nobody-measured: types"


def test_a_contradiction_naming_a_measured_file_is_a_judgement_and_not_a_bad_answer():
    contradicted = {
        "proofs": [
            {"kind": "types", "verdict": "contradicted", "where": "money.py", "because": "it adds annotations"}
        ]
    }

    recount_the_proofs(contradicted, PROVED, VERIFIED)


def test_a_run_that_measured_nothing_cannot_carry_a_contradiction():
    contradicted = {
        "proofs": [
            {"kind": "types", "verdict": "contradicted", "where": "money.py", "because": "it adds annotations"}
        ]
    }

    with pytest.raises(ContractRefusal) as refused:
        recount_the_proofs(contradicted, PROVED, {})

    assert refused.value.code == "nothing-was-measured: types"


def test_a_judgement_of_a_kind_nobody_excused_may_not_ride_along():
    with pytest.raises(ContractRefusal) as refused:
        recount_the_proofs({"proofs": [{"kind": "suite", "verdict": "stands"}]}, PROVED, VERIFIED)

    assert refused.value.code == "kind-not-owed: suite"


def test_an_excuse_the_review_said_nothing_about_is_refused():
    with pytest.raises(ContractRefusal) as refused:
        recount_the_proofs({"proofs": []}, PROVED, VERIFIED)

    assert refused.value.code == "excuse-unjudged: types"


def test_a_feature_that_excused_nothing_owes_the_review_no_rows():
    recount_the_proofs({}, {"proves": [{"kind": "suite", "command": "sh check.sh"}]}, VERIFIED)


# --- and the contradiction stops the run, rather than being asked again -----


def test_a_contradicted_excuse_stops_the_run_where_a_blocking_finding_would():
    from agent_kit.programs.deliverable import refuse_unless_deliverable
    from agent_kit.providers.base import ExecutorFailed

    review = {
        "verdict": "pass",
        "findings": [],
        "proofs": [
            {"kind": "types", "verdict": "contradicted", "where": "money.py", "because": "it adds annotations"}
        ],
    }

    with pytest.raises(ExecutorFailed) as refused:
        refuse_unless_deliverable({"complete": True}, {"passed": True}, review)

    assert refused.value.code == "why-the-diff-contradicts: types"
    assert refused.value.expected is True
    assert refused.value.retryable is False


# --- and the same command is not paid for twice -----------------------------


def test_a_kind_proved_by_a_command_the_project_already_ran_is_not_run_again(tmp_path):
    """On a real project `[commands].test` and the answer to `suite` are one line.

    A feature that paid for it twice would pay every night. What it costs is a
    record in which the same command stands against the project and against the
    kind, which is what makes the two agreeing visible rather than accidental.
    """
    import json
    import subprocess

    from agent_kit.programs.verify import Verify
    from agent_kit.providers.base import StepRequest

    declare(
        tmp_path,
        '[commands]\ntest = "sh check.sh"\n\n'
        '[verification.suite]\ncommand = "sh check.sh"\n\n'
        '[verification.types]\ncommand = "sh types.sh"\n',
    )
    (tmp_path / "check.sh").write_text("#!/bin/sh\necho ran-the-suite\n")
    (tmp_path / "types.sh").write_text("#!/bin/sh\nexit 0\n")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)

    output = Verify(tmp_path).execute(
        StepRequest(
            slug="s", step_name="verify", attempt=1, provider="program", input_text="",
            workdir=tmp_path, project=tmp_path,
            prior={"design": {"proves": [
                {"kind": "suite", "command": "sh check.sh"},
                {"kind": "types", "command": "sh types.sh"},
            ]}},
        )
    )

    said = json.loads(output.raw)
    suite = next(kind for kind in said["kinds"] if kind["kind"] == "suite")
    assert suite["name"] == "test"  # the declared command that proved it
    assert suite["command"] == "sh check.sh"
    assert said["passed"] is True
    # Two commands were run, not three, and the record says two.
    assert output.meta["commands_run"] == 2


def test_a_kind_whose_command_comes_back_red_is_a_verify_that_did_not_pass(tmp_path):
    import json
    import subprocess

    from agent_kit.programs.verify import Verify
    from agent_kit.programs.deliverable import refuse_unless_deliverable
    from agent_kit.providers.base import ExecutorFailed, StepRequest

    declare(
        tmp_path,
        '[commands]\ntest = "sh check.sh"\n\n[verification.types]\ncommand = "sh types.sh"\n',
    )
    (tmp_path / "check.sh").write_text("#!/bin/sh\nexit 0\n")
    (tmp_path / "types.sh").write_text("#!/bin/sh\nexit 1\n")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)

    said = json.loads(
        Verify(tmp_path).execute(
            StepRequest(
                slug="s", step_name="verify", attempt=1, provider="program", input_text="",
                workdir=tmp_path, project=tmp_path,
                prior={"design": {"proves": [{"kind": "types", "command": "sh types.sh"}]}},
            )
        ).raw
    )

    assert said["passed"] is False

    # And delivery names the kind rather than saying no command ran.
    with pytest.raises(ExecutorFailed) as refused:
        refuse_unless_deliverable({"complete": True}, said, {"verdict": "pass", "findings": []})
    assert refused.value.code == "not-verified"
    assert "types" in refused.value.detail
