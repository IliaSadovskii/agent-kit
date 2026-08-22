"""S4 — the steps a session does: design, build, review.

Each one's contract is the trace it leaves. Question 2 of the plan's four: a
step whose skipping is invisible is not a step, it is a hope. So what the
second version prescribed in prose and checked nowhere — decide the kinds of
verification before the code, name the seams, record a departure and its cause —
is a required field here, and a missing one refuses the step.
"""

import json

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.errors import StateError
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import DEFAULT_STEPS, RunStore
from agent_kit.steps import builtin_registry
from agent_kit.steps.contract import ContractRefusal

DESIGN = {
    "title": "Money learns a VAT rate",
    "summary": "Money learns a VAT rate, so a price can be quoted with tax.",
    "changes": ["src/kit_sandbox/money.py — a with_vat method"],
    "seams": ["Money is frozen, so with_vat returns a new one"],
    "verification": ["a test that 1000 at 20% is 1200", "a test that a negative rate is refused"],
    "assumptions": [{"what": "VAT is a whole percent", "expensive": False, "because": "the sandbox has no fractions"}],
}

BUILD = {
    "complete": True,
    "summary": "with_vat, and the two tests that were decided before it.",
    "files": ["src/kit_sandbox/money.py", "tests/test_money.py"],
    "tests": ["test_vat_is_added_to_the_amount"],
    "deviations": [],
}

REVIEW = {"verdict": "pass", "findings": []}


def fenced(data):
    return "```json\n" + json.dumps(data) + "\n```"


def contract(name):
    return builtin_registry().get(name).contract


def refuse(name, data):
    with pytest.raises(ContractRefusal) as refused:
        contract(name).check(data)
    return refused.value.code


# --- a run of a feature is five steps ---------------------------------------


def test_a_run_that_says_nothing_else_designs_builds_verifies_reviews_and_delivers():
    assert list(DEFAULT_STEPS) == ["design", "build", "verify", "review", "deliver"]
    for name in DEFAULT_STEPS:
        builtin_registry().get(name)


def test_a_run_that_designs_a_feature_is_refused_without_a_brief(tmp_path):
    store = RunStore(tmp_path)

    with pytest.raises(StateError) as refused:
        create_run(store, builtin_registry(), "add-vat", steps=["design"])
    assert refused.value.code == "no-brief"


def test_a_run_of_steps_that_need_no_brief_may_have_none(tmp_path):
    create_run(RunStore(tmp_path), builtin_registry(), "look", steps=["probe"])


# --- design: what will prove it, decided before the code --------------------


def test_design_returns_the_seams_and_what_will_prove_it():
    checked = contract("design").check(DESIGN)

    assert checked["seams"]
    assert checked["verification"]
    assert checked["assumptions"][0]["expensive"] is False


def test_a_design_that_does_not_say_what_will_prove_it_is_refused():
    assert refuse("design", {**DESIGN, "verification": None}) == "output-missing-field: verification"


def test_a_design_that_names_no_seams_is_refused():
    assert refuse("design", {**DESIGN, "seams": None}) == "output-missing-field: seams"


def test_an_assumption_that_does_not_say_whether_it_is_expensive_is_refused():
    damaged = {**DESIGN, "assumptions": [{"what": "VAT is a whole percent", "because": "no fractions"}]}

    assert refuse("design", damaged) == "output-missing-field: assumptions[0].expensive"


# --- build: the test first, and a departure carries its cause ---------------


def test_build_says_whether_it_finished_and_what_it_changed():
    checked = contract("build").check(BUILD)

    assert checked["complete"] is True
    assert checked["files"]
    assert checked["tests"]


def test_a_build_that_does_not_say_whether_it_finished_is_refused():
    assert refuse("build", {**BUILD, "complete": None}) == "output-missing-field: complete"


def test_a_departure_from_the_design_must_carry_its_cause():
    damaged = {**BUILD, "deviations": [{"what": "put it on a free function instead"}]}

    assert refuse("build", damaged) == "output-missing-field: deviations[0].because"


def test_a_build_may_be_split_and_the_step_says_so():
    assert builtin_registry().get("build").splittable
    assert not builtin_registry().get("design").splittable


# --- review: a finding has a severity, and one of them blocks ---------------


def test_a_finding_carries_a_severity_the_program_can_act_on():
    checked = contract("review").check(
        {"verdict": "blocked", "findings": [{"severity": "blocking", "what": "the rate is not checked"}]}
    )

    assert checked["findings"][0]["severity"] == "blocking"


def test_a_severity_the_kit_does_not_know_is_refused():
    damaged = {"verdict": "pass", "findings": [{"severity": "quite bad", "what": "hmm"}]}

    assert refuse("review", damaged) == "output-bad-field: findings[0].severity"


def test_a_verdict_that_is_not_one_of_the_two_is_refused():
    assert refuse("review", {"verdict": "probably", "findings": []}) == "output-bad-field: verdict"


# --- the driver runs them in order, each enclosing the last ------------------


def test_each_step_is_handed_what_the_one_before_it_returned(tmp_path):
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(
        store, registry, "add-vat", steps=["design", "build", "review"],
        project=str(tmp_path), brief="Money should know about VAT",
    )
    fake = FakeExecutor(replies=[fenced(DESIGN), fenced(BUILD), fenced(REVIEW)])
    runner = StepRunner(store=store, registry=registry, executors={"fake": fake}, default_provider="fake")

    for _ in range(3):
        runner.run_next("add-vat")

    build_input = fake.requests[1].input_text
    review_input = fake.requests[2].input_text

    assert "a with_vat method" in build_input  # the design arrived enclosed
    assert "Money should know about VAT" in build_input  # and so did the brief
    assert "test_vat_is_added_to_the_amount" in review_input
    assert "1000 at 20% is 1200" in review_input  # what design said would prove it


def test_a_design_that_gives_no_subject_line_is_refused():
    assert refuse("design", {**DESIGN, "title": None}) == "output-missing-field: title"
