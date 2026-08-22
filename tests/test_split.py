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

#: The second session answers for what *it* did. Nothing makes it repeat the
#: first part's list, and a test whose second reply happens to hold both is a
#: test that cannot fail — which is how this defect survived the first round.
WHOLE = {
    "complete": True,
    "summary": "And the rest of the code.",
    "files": ["src/kit_sandbox/money.py"],
    "tests": ["test_a_negative_rate_is_refused"],
    "deviations": [{"what": "a free function", "because": "Money is frozen"}],
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
    """One attempt per provider: without the reset, the part would use it up."""
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(store, registry, "add-vat", steps=["build"], project=str(tmp_path), brief=BRIEF)
    runner = StepRunner(
        store=store,
        registry=registry,
        executors={"fake": FakeExecutor(replies=[fenced(PART), fenced(WHOLE)])},
        default_provider="fake",
        attempts_per_provider=1,
    )

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
    """A `complete: false` from a step that may not be split is a field nobody reads."""
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(store, registry, "look", steps=["probe"], project=str(tmp_path))
    fake = FakeExecutor(replies=['```json\n{"branch": "main", "can_write": true, "complete": false}\n```'])

    outcome = StepRunner(
        store=store, registry=registry, executors={"fake": fake}, default_provider="fake"
    ).run_next("look")

    assert outcome.passed
    assert len(fake.requests) == 1  # it was not carried on
    assert store.load("look").steps[0].status is StepStatus.PASSED


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


def test_a_continuation_leaves_no_refusal_behind_and_says_its_own_word(tmp_path):
    from agent_kit.state.schema import Run

    runner, _, _ = build(tmp_path, [fenced(PART), fenced(WHOLE)])
    runner.run_next("add-vat")

    # The first attempt did real work, so nothing about it was refused.
    attempt = tmp_path / ".agent-kit/v3/runs/add-vat/steps/0-build/attempt-1"
    assert (attempt / "input.md").is_file()
    assert not (attempt / "refusal.txt").exists()

    # And the state has a word for it that is neither refusing nor failing.
    run = Run.new("x", steps=["build"], brief="b")
    run.start_step("p")
    run.continue_step("build part 1 is done and it goes on: the negative rate")
    assert run.status is RunStatus.RUNNING
    assert run.steps[0].status is StepStatus.PENDING
    assert "goes on" in run.steps[0].reason


def test_a_step_that_outgrew_its_room_says_so_on_the_step_and_not_only_on_the_run(tmp_path):
    runner, store, _ = build(tmp_path, [fenced(PART)] * 4, continuations=1)

    runner.run_next("add-vat")

    step = store.load("add-vat").steps[0]
    assert step.status is StepStatus.FAILED
    assert step.reason and "outgrew" in step.reason


def test_every_part_reaches_the_step_after_it_and_not_only_the_last(tmp_path):
    """What review and deliver read is the step's output, and a split step has more than one."""
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(
        store, registry, "add-vat", steps=["build", "review"], project=str(tmp_path), brief=BRIEF
    )
    fake = FakeExecutor(
        replies=[fenced(PART), fenced(WHOLE), '```json\n{"verdict": "pass", "findings": []}\n```']
    )
    runner = StepRunner(store=store, registry=registry, executors={"fake": fake}, default_provider="fake")

    outcome = runner.run_next("add-vat")
    runner.run_next("add-vat")

    assert outcome.output["files"] == ["tests/test_money.py", "src/kit_sandbox/money.py"]
    assert outcome.output["tests"] == [
        "test_vat_is_added_to_the_amount",
        "test_a_negative_rate_is_refused",
    ]
    assert outcome.output["complete"] is True
    assert "tests/test_money.py" in fake.requests[2].input_text  # the reviewer sees all of it
