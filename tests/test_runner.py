"""S2 — the driver runs one step: compose, execute, validate, record.

Three of these are the step's reason to exist: a missing output leaves the step
unpassed, an output that does not satisfy the contract is refused, and a valid
one is recorded with its trace.
"""

import json

import pytest

from agent_kit.driver import StepRunner
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStatus, RunStore, StepStatus
from agent_kit.steps import builtin_registry

GOOD = '```json\n{"branch": "kit/add-login", "can_write": true, "notes": ["nothing odd"]}\n```'
NO_BRANCH = '```json\n{"can_write": true}\n```'
NOT_JSON = "I had a look around and everything seems fine."


def runner(tmp_path, replies, roles=None, executors=None):
    store = RunStore(tmp_path, registry=builtin_registry())
    store.create("add-login", steps=["probe"], project=str(tmp_path))
    fake = FakeExecutor(name="fake", replies=replies)
    return (
        StepRunner(
            store=store,
            registry=builtin_registry(),
            executors={"fake": fake, **(executors or {})},
            roles=roles or {},
            default_provider="fake",
        ),
        store,
        fake,
    )


def step_dir(tmp_path, attempt=None):
    root = tmp_path / ".agent-kit/v3/runs/add-login/steps/0-probe"
    return root if attempt is None else root / f"attempt-{attempt}"


# --- the three the step exists for -----------------------------------------


def test_a_valid_output_is_recorded_with_its_trace(tmp_path):
    run_step, store, _ = runner(tmp_path, [GOOD])

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert outcome.output["branch"] == "kit/add-login"
    run = store.load("add-login")
    assert run.steps[0].status is StepStatus.PASSED
    assert run.steps[0].provider == "fake"
    assert run.status is RunStatus.DONE

    assert json.loads((step_dir(tmp_path) / "output.json").read_text())["can_write"] is True
    assert (step_dir(tmp_path, 1) / "input.md").is_file()
    assert (step_dir(tmp_path, 1) / "raw.txt").read_text() == GOOD
    meta = json.loads((step_dir(tmp_path, 1) / "meta.json").read_text())
    assert meta["provider"] == "fake" and meta["attempt"] == 1


def test_an_output_that_does_not_satisfy_the_contract_is_refused(tmp_path):
    run_step, store, _ = runner(tmp_path, [NO_BRANCH, NO_BRANCH, NO_BRANCH])

    outcome = run_step.run_next("add-login")

    assert not outcome.passed
    assert "output-missing-field: branch" in outcome.reason
    assert store.load("add-login").steps[0].status is StepStatus.FAILED
    assert not (step_dir(tmp_path) / "output.json").exists()


def test_a_missing_output_leaves_the_step_unpassed(tmp_path):
    run_step, store, _ = runner(tmp_path, [NOT_JSON, NOT_JSON, NOT_JSON])

    outcome = run_step.run_next("add-login")

    assert not outcome.passed
    assert "output-not-json" in outcome.reason or "output-missing" in outcome.reason
    assert store.load("add-login").status is RunStatus.FAILED


# --- what happens when a step fails (open question 4) ----------------------


def test_three_attempts_and_each_one_is_told_why_the_last_was_refused(tmp_path):
    run_step, _, fake = runner(tmp_path, [NO_BRANCH, NO_BRANCH, GOOD])

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert [attempt.provider for attempt in outcome.attempts] == ["fake", "fake", "fake"]
    assert "output-missing-field: branch" in fake.requests[1].input_text
    assert "output-missing-field: branch" in fake.requests[2].input_text
    assert "The previous attempt was refused" not in fake.requests[0].input_text


def test_an_attempt_that_repeats_the_same_input_is_not_an_attempt(tmp_path):
    run_step, _, fake = runner(tmp_path, [NO_BRANCH, NO_BRANCH, NO_BRANCH])

    run_step.run_next("add-login")

    inputs = [request.input_text for request in fake.requests]
    assert len(set(inputs)) == len(inputs)


def test_after_three_the_role_s_fallback_provider_gets_one(tmp_path):
    from agent_kit.config import RoleConfig

    spare = FakeExecutor(name="spare", replies=[GOOD])
    run_step, store, fake = runner(
        tmp_path,
        [NO_BRANCH, NO_BRANCH, NO_BRANCH],
        roles={"probe": RoleConfig(name="probe", provider="fake", fallback=["spare"])},
        executors={"spare": spare},
    )

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert [attempt.provider for attempt in outcome.attempts] == ["fake", "fake", "fake", "spare"]
    assert len(spare.requests) == 1
    assert store.load("add-login").steps[0].provider == "spare"


def test_when_the_fallback_fails_too_the_run_stops_and_says_what_was_missing(tmp_path):
    from agent_kit.config import RoleConfig

    spare = FakeExecutor(name="spare", replies=[NO_BRANCH])
    run_step, store, _ = runner(
        tmp_path,
        [NO_BRANCH, NO_BRANCH, NO_BRANCH],
        roles={"probe": RoleConfig(name="probe", provider="fake", fallback=["spare"])},
        executors={"spare": spare},
    )

    outcome = run_step.run_next("add-login")

    assert not outcome.passed
    assert len(outcome.attempts) == 4
    run = store.load("add-login")
    assert run.status is RunStatus.FAILED
    assert "probe" in run.reason and "output-missing-field: branch" in run.reason


def test_a_provider_that_dies_is_an_attempt_like_any_other(tmp_path):
    from agent_kit.driver.executor import ExecutorFailed

    def die(_request):
        raise ExecutorFailed("session-died", "the CLI exited with status 1")

    run_step, _, _ = runner(tmp_path, [die, GOOD])

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert outcome.attempts[0].refusal.startswith("session-died")


def test_a_failed_attempt_keeps_its_raw_text_for_reading_afterwards(tmp_path):
    run_step, _, _ = runner(tmp_path, [NOT_JSON, GOOD])

    run_step.run_next("add-login")

    assert (step_dir(tmp_path, 1) / "raw.txt").read_text() == NOT_JSON
    assert "output-not-json" in (step_dir(tmp_path, 1) / "refusal.txt").read_text()
    assert (step_dir(tmp_path, 2) / "raw.txt").read_text() == GOOD


# --- what the runner refuses to start --------------------------------------


def test_a_run_with_nothing_pending_is_refused(tmp_path):
    run_step, _, _ = runner(tmp_path, [GOOD])
    run_step.run_next("add-login")

    from agent_kit.errors import StateError

    with pytest.raises(StateError) as caught:
        run_step.run_next("add-login")

    assert caught.value.code == "run-finished"


def test_a_provider_nobody_configured_is_refused_before_anything_runs(tmp_path):
    from agent_kit.config import RoleConfig
    from agent_kit.errors import ProviderError

    run_step, store, _ = runner(
        tmp_path, [GOOD], roles={"probe": RoleConfig(name="probe", provider="codex")}
    )

    with pytest.raises(ProviderError) as caught:
        run_step.run_next("add-login")

    assert caught.value.code == "unknown-provider"
    assert store.load("add-login").steps[0].status is StepStatus.PENDING


def test_the_output_of_an_earlier_step_is_enclosed_in_the_next(tmp_path):
    store = RunStore(tmp_path, registry=builtin_registry())
    store.create("twice", steps=["probe", "probe"], project=str(tmp_path))
    fake = FakeExecutor(name="fake", replies=[GOOD, GOOD])
    run_step = StepRunner(
        store=store, registry=builtin_registry(), executors={"fake": fake}, roles={}, default_provider="fake"
    )

    run_step.run_next("twice")
    run_step.run_next("twice")

    assert "kit/add-login" in fake.requests[1].input_text
    assert "0-probe" in fake.requests[1].input_text
