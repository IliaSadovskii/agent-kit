"""S2 — the driver runs one step: compose, execute, validate, record.

Three of these are the step's reason to exist: a missing output leaves the step
unpassed, an output that does not satisfy the contract is refused, and a valid
one is recorded with its trace.
"""

import json

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStatus, RunStore, StepStatus
from agent_kit.steps import builtin_registry

GOOD = '```json\n{"branch": "kit/add-login", "can_write": true, "notes": ["nothing odd"]}\n```'
NO_BRANCH = '```json\n{"can_write": true}\n```'
NOT_JSON = "I had a look around and everything seems fine."


#: The chain waits thirty seconds after a refused attempt and doubles from
#: there. Three tests here are about the seconds themselves and hand in a pause
#: of their own that records them; every other test is about what the run
#: decided, and a real minute of sleeping measures the clock rather than the
#: decision. So the helper's default asks for the pause and does not take it.
def no_pause(_seconds):
    return None


def runner(tmp_path, replies, roles=None, executors=None, pause=None):
    store = RunStore(tmp_path)
    create_run(store, builtin_registry(), "add-login", steps=["probe"], project=str(tmp_path))
    fake = FakeExecutor(name="fake", replies=replies)
    return (
        StepRunner(
            store=store,
            registry=builtin_registry(),
            executors={"fake": fake, **(executors or {})},
            roles=roles or {},
            default_provider="fake",
            pause=pause or no_pause,
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
    run_step, _, fake = runner(tmp_path, [NO_BRANCH, NOT_JSON, NO_BRANCH])

    run_step.run_next("add-login")

    inputs = [request.input_text for request in fake.requests]
    assert len(set(inputs)) == len(inputs)
    # each retry carries the reason the previous one was refused, not just a counter
    assert "output-missing-field: branch" in inputs[1]
    assert "output-not-json" in inputs[2]


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
    from agent_kit.providers.base import ExecutorFailed

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


def test_the_fallback_attempt_is_not_told_it_is_the_fourth_of_three(tmp_path):
    """One number rendered as one fact: attempts are counted per provider."""
    from agent_kit.config import RoleConfig

    spare = FakeExecutor(name="spare", replies=[GOOD])
    run_step, _, _ = runner(
        tmp_path,
        [NO_BRANCH, NO_BRANCH, NO_BRANCH],
        roles={"probe": RoleConfig(name="probe", provider="fake", fallback=["spare"])},
        executors={"spare": spare},
    )

    run_step.run_next("add-login")

    assert "attempt 1 of 3" in spare.requests[0].input_text
    assert "attempt 4" not in spare.requests[0].input_text


def test_a_fallback_that_repeats_the_primary_is_not_a_fallback(tmp_path):
    from agent_kit.config import RoleConfig

    run_step, _, fake = runner(
        tmp_path,
        [NO_BRANCH, NO_BRANCH, NO_BRANCH],
        roles={"probe": RoleConfig(name="probe", provider="fake", fallback=["fake"])},
    )

    outcome = run_step.run_next("add-login")

    assert len(outcome.attempts) == 3


def test_a_failed_run_is_not_quietly_resumed(tmp_path):
    """Three refusals, the fallback, then a stop — and `run_next` again does not undo that."""
    run_step, store, _ = runner(tmp_path, [NOT_JSON, NOT_JSON, NOT_JSON])
    run_step.run_next("add-login")

    from agent_kit.errors import StateError

    with pytest.raises(StateError) as caught:
        run_step.run_next("add-login")

    assert caught.value.code == "run-finished"
    run = store.load("add-login")
    assert run.status is RunStatus.FAILED
    assert "refused 3 times" in run.reason


def test_a_finished_run_is_refused_by_name(tmp_path):
    run_step, _, _ = runner(tmp_path, [GOOD])
    run_step.run_next("add-login")

    from agent_kit.errors import StateError

    with pytest.raises(StateError) as caught:
        run_step.run_next("add-login")

    assert caught.value.code == "run-finished"


# --- a provider that misbehaves, and a driver that vanished ---------------


def test_a_provider_that_raises_something_unexpected_is_still_only_an_attempt(tmp_path):
    """An adapter is somebody else's code. A surprise from it must not wedge the run."""

    def explode(_request):
        raise RuntimeError("the CLI wrote something nobody parsed")

    run_step, store, _ = runner(tmp_path, [explode, GOOD])

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert "provider-crashed" in outcome.attempts[0].refusal
    assert "RuntimeError" in outcome.attempts[0].refusal
    assert store.load("add-login").status is RunStatus.DONE


def test_a_run_is_left_advanceable_when_something_escapes_mid_step(tmp_path):
    """Whatever breaks, the state must not be left holding a step nobody can move."""
    from agent_kit.driver import runner as runner_module

    run_step, store, _ = runner(tmp_path, [GOOD])
    original = runner_module.StepWorkspace.write_raw

    def refuse_to_write(*_args, **_kwargs):
        raise OSError("disk full")

    runner_module.StepWorkspace.write_raw = refuse_to_write
    try:
        with pytest.raises(OSError):
            run_step.run_next("add-login")
    finally:
        runner_module.StepWorkspace.write_raw = original

    run = store.load("add-login")
    assert run.steps[0].status is StepStatus.PENDING
    assert run.current_step is None
    assert "disk full" in run.steps[0].reason


def test_a_step_left_running_by_a_dead_driver_is_picked_up_again(tmp_path):
    """A killed driver leaves a step RUNNING. The next run says so and tries again."""
    run_step, store, _ = runner(tmp_path, [GOOD])
    store.start_step("add-login", provider="fake")  # nobody ever came back

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert store.load("add-login").steps[0].attempts == 2


def test_a_failure_that_cannot_come_right_does_not_get_three_paid_attempts(tmp_path):
    """Three tries at a missing binary is three times nothing. With a real
    provider each attempt is a session, and a session is money."""
    from agent_kit.config import RoleConfig
    from agent_kit.providers.base import ExecutorFailed

    def hopeless(_request):
        raise ExecutorFailed("binary-missing", "claude is not on PATH", retryable=False)

    spare = FakeExecutor(name="spare", replies=[GOOD])
    run_step, _, fake = runner(
        tmp_path,
        [hopeless, hopeless, hopeless],
        roles={"probe": RoleConfig(name="probe", provider="fake", fallback=["spare"])},
        executors={"spare": spare},
    )

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert len(fake.requests) == 1  # asked once, believed the first time
    assert [attempt.provider for attempt in outcome.attempts] == ["fake", "spare"]


def test_a_limited_account_is_not_asked_again_it_is_left_alone(tmp_path):
    from agent_kit.providers.base import ExecutorFailed

    def limited(_request):
        raise ExecutorFailed("provider-limited", "resets at 5pm", retryable=False)

    run_step, store, fake = runner(tmp_path, [limited, limited, limited])

    outcome = run_step.run_next("add-login")

    assert not outcome.passed
    assert len(fake.requests) == 1
    assert "5pm" in store.load("add-login").reason


def test_what_a_refused_attempt_cost_is_written_down(tmp_path):
    from agent_kit.providers.base import ExecutorFailed, SessionFacts

    def costly(_request):
        raise ExecutorFailed(
            "session-error", "it went wrong", facts=SessionFacts(session="s-1", cost_usd=0.12)
        )

    run_step, _, _ = runner(tmp_path, [costly, GOOD])

    run_step.run_next("add-login")

    meta = json.loads((step_dir(tmp_path, 1) / "meta.json").read_text())
    assert meta["cost_usd"] == 0.12
    assert meta["session"] == "s-1"


def test_a_run_with_nothing_pending_is_refused(tmp_path):
    """The message must name what is true: nothing pending is not the same as finished."""
    from agent_kit.errors import StateError
    from agent_kit.state import RunStatus as Status

    run_step, store, _ = runner(tmp_path, [GOOD])
    run_step.run_next("add-login")
    store.update("add-login", lambda run: setattr(run, "status", Status.RUNNING))

    with pytest.raises(StateError) as caught:
        run_step.run_next("add-login")

    assert caught.value.code == "no-step-pending"


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


def test_a_session_is_run_in_the_project_not_in_the_step_s_own_directory(tmp_path):
    """The step directory is where the driver keeps its paperwork, not where work happens."""
    run_step, _, fake = runner(tmp_path, [GOOD])

    run_step.run_next("add-login")

    assert fake.requests[0].project == tmp_path


def test_a_run_created_without_a_project_still_knows_where_it_is(tmp_path):
    from agent_kit.driver import create_run

    store = RunStore(tmp_path)
    run = create_run(store, builtin_registry(), "unstated", steps=["probe"])

    assert run.project == str(tmp_path)


def test_the_output_of_an_earlier_step_is_enclosed_in_the_next(tmp_path):
    store = RunStore(tmp_path)
    create_run(store, builtin_registry(), "twice", steps=["probe", "probe"], project=str(tmp_path))
    fake = FakeExecutor(name="fake", replies=[GOOD, GOOD])
    run_step = StepRunner(
        store=store, registry=builtin_registry(), executors={"fake": fake}, roles={}, default_provider="fake"
    )

    run_step.run_next("twice")
    run_step.run_next("twice")

    assert "kit/add-login" in fake.requests[1].input_text
    assert "0-probe" in fake.requests[1].input_text


# --- пауза между попытками --------------------------------------------------
#
# Провайдер, которого на минуту завалило, отвечает так же и через секунду. Цепь
# без паузы тратит все свои попытки внутри той минуты, за которую беда прошла
# бы сама: три сессии подряд, потом запасной, потом прогон провален.


def test_a_session_the_tool_refused_is_not_asked_again_at_once(tmp_path):
    from agent_kit.driver.runner import BACKOFF
    from agent_kit.providers.base import ExecutorFailed

    def die(_request):
        raise ExecutorFailed("session-died", "the CLI exited with status 1")

    waited = []
    run_step, _, _ = runner(tmp_path, [die, die, GOOD], pause=waited.append)

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert waited == [BACKOFF, BACKOFF * 2]  # растёт с номером попытки


def test_the_last_refusal_is_not_followed_by_a_pause(tmp_path):
    """Пауза — это ожидание перед следующей попыткой. Следующей нет — и ждать нечего."""
    from agent_kit.driver.runner import BACKOFF
    from agent_kit.providers.base import ExecutorFailed

    def die(_request):
        raise ExecutorFailed("session-died", "the CLI exited with status 1")

    waited = []
    run_step, _, _ = runner(tmp_path, [die, die, die], pause=waited.append)

    outcome = run_step.run_next("add-login")

    assert not outcome.passed
    assert waited == [BACKOFF, BACKOFF * 2]


def test_a_provider_that_cannot_be_asked_again_is_left_without_a_pause(tmp_path):
    """Ждать нечего: этот отказ повторится тем же самым, и цепь идёт к следующему."""
    from agent_kit.config import RoleConfig
    from agent_kit.providers.base import ExecutorFailed

    def missing(_request):
        raise ExecutorFailed("binary-missing", "no such binary", retryable=False)

    spare = FakeExecutor(name="spare", replies=[GOOD])
    waited = []
    run_step, _, _ = runner(
        tmp_path,
        [missing],
        roles={"probe": RoleConfig(name="probe", provider="fake", fallback=["spare"])},
        executors={"spare": spare},
        pause=waited.append,
    )

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert waited == []


def test_an_answer_that_failed_the_contract_is_asked_again_at_once(tmp_path):
    """Пауза лечит инструмент, а не ответ: модель, написавшую не то, чинит вложенная причина."""
    waited = []
    run_step, _, _ = runner(tmp_path, [NO_BRANCH, GOOD], pause=waited.append)

    outcome = run_step.run_next("add-login")

    assert outcome.passed
    assert waited == []
