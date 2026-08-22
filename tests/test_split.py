"""S4 — open question 5: the ceiling inside a step.

A step declares whether it may be split. If it may, a session that runs out of
room returns what it did and says it is not finished; the driver starts the next
one with the same input plus what the previous produced. If it may not, a step
that outgrows its window is a design error to fix, not a night to survive.

A continuation is not a refusal. The work is real, it is kept, and the words for
the two events are different — the same distinction the state already draws
between refusing one attempt and failing a step.
"""

import json

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.driver.workspace import StepWorkspace
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStatus, RunStore, StepStatus
from agent_kit.steps import builtin_registry

BRIEF = "Money should know about VAT"

PART = {
    "complete": False,
    "summary": "The test is written and one half of the code.",
    "files": ["tests/test_money.py"],
    "tests": ["test_vat_is_added_to_the_amount"],
    "remaining": ["the negative rate is still unrefused"],
}

WHOLE = {
    "complete": True,
    "summary": "The test, and all of the code.",
    "files": ["tests/test_money.py", "src/kit_sandbox/money.py"],
    "tests": ["test_vat_is_added_to_the_amount", "test_a_negative_rate_is_refused"],
}


def fenced(data):
    return "```json\n" + json.dumps(data) + "\n```"


def build(tmp_path, replies, continuations=3):
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(store, registry, "add-vat", steps=["build"], project=str(tmp_path), brief=BRIEF)
    fake = FakeExecutor(replies=replies)
    runner = StepRunner(
        store=store,
        registry=registry,
        executors={"fake": fake},
        default_provider="fake",
        continuations_allowed=continuations,
    )
    return runner, store, fake


def parts_of(tmp_path):
    return StepWorkspace(tmp_path / ".agent-kit/v3/runs/add-vat", 0, "build").read_parts()


# --- a step that may be split -----------------------------------------------


def test_a_build_that_did_not_finish_is_continued_not_refused(tmp_path):
    runner, store, fake = build(tmp_path, [fenced(PART), fenced(WHOLE)])

    outcome = runner.run_next("add-vat")

    assert outcome.passed
    assert outcome.output["complete"] is True
    assert store.load("add-vat").steps[0].status is StepStatus.PASSED
    assert len(fake.requests) == 2


def test_the_next_session_is_handed_what_the_last_one_did(tmp_path):
    runner, _, fake = build(tmp_path, [fenced(PART), fenced(WHOLE)])

    runner.run_next("add-vat")

    carried = fake.requests[1].input_text
    assert "the negative rate is still unrefused" in carried
    assert "The test is written and one half" in carried
    assert BRIEF in carried


def test_every_part_is_kept_and_not_only_the_last(tmp_path):
    runner, _, _ = build(tmp_path, [fenced(PART), fenced(WHOLE)])

    runner.run_next("add-vat")

    kept = parts_of(tmp_path)
    assert [part["complete"] for part in kept] == [False, True]


def test_a_continuation_does_not_spend_the_attempts_a_refusal_would(tmp_path):
    """Two parts and one refusal between them still leave the step room to pass."""
    runner, store, _ = build(tmp_path, [fenced(PART), "not json at all", fenced(WHOLE)])

    outcome = runner.run_next("add-vat")

    assert outcome.passed
    assert store.load("add-vat").steps[0].status is StepStatus.PASSED


def test_a_step_that_never_finishes_stops_the_run_and_says_so(tmp_path):
    runner, store, _ = build(tmp_path, [fenced(PART)] * 4, continuations=2)

    outcome = runner.run_next("add-vat")

    assert not outcome.passed
    assert "outgrew" in outcome.reason
    run = store.load("add-vat")
    assert run.status is RunStatus.FAILED
    assert "outgrew" in run.reason


def test_a_step_it_may_not_split_is_never_continued(tmp_path):
    """design has no `complete` field at all: nothing about it can ask for more room."""
    assert not builtin_registry().get("design").splittable


def test_the_input_of_a_splittable_step_says_it_may_stop_short(tmp_path):
    runner, _, fake = build(tmp_path, [fenced(WHOLE)])

    runner.run_next("add-vat")

    assert "may be split" in fake.requests[0].input_text


def test_the_input_of_a_step_that_may_not_be_split_says_nothing_about_it(tmp_path):
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(store, registry, "look", steps=["probe"], project=str(tmp_path))
    fake = FakeExecutor(replies=['```json\n{"branch": "main", "can_write": true}\n```'])

    StepRunner(store=store, registry=registry, executors={"fake": fake}, default_provider="fake").run_next("look")

    assert "may be split" not in fake.requests[0].input_text


# --- the words for it --------------------------------------------------------


def test_a_continuation_is_written_down_in_different_words_than_a_refusal(tmp_path):
    runner, store, _ = build(tmp_path, [fenced(PART), fenced(PART)], continuations=1)

    runner.run_next("add-vat")

    with pytest.raises(Exception):
        # the run is over; what matters is the word left behind on the way
        runner.run_next("add-vat")
    assert "refused" not in (store.load("add-vat").steps[0].reason or "")
