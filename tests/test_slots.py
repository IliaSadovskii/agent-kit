"""S7 — the driver against the machine: a slot before a session, and never two.

The step is done when two runs on one account wait for each other correctly
instead of sleeping blind. Everything here is that sentence, taken apart.
"""

import json

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.errors import ProviderError, StateError
from agent_kit.machine import Ceilings, Ledger, Want
from agent_kit.providers.base import ExecutorFailed
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStatus, RunStore, StepStatus
from agent_kit.steps import builtin_registry

GOOD = '```json\n{"branch": "kit/add-login", "can_write": true, "notes": ["nothing odd"]}\n```'
RESET = "2026-08-24T17:00:00+00:00"


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "ledger" / "daemon.sqlite")


def build(tmp_path, ledger, replies, *, steps=("probe",), ceilings=None, wait=0, pause=None,
          executors=None, roles=None, accounts=None):
    store = RunStore(tmp_path)
    create_run(store, builtin_registry(), "add-login", steps=list(steps), project=str(tmp_path))
    fake = FakeExecutor(name="fake", replies=list(replies))
    runner = StepRunner(
        store=store,
        registry=builtin_registry(),
        executors={"fake": fake, **(executors or {})},
        roles=roles or {},
        default_provider="fake",
        ledger=ledger,
        ceilings=ceilings or Ceilings(max_sessions=1),
        accounts=accounts or {},
        wait=wait,
        pause=pause or (lambda seconds: None),
    )
    return runner, store, fake


def somebody_else(ledger, ceilings, slug="another", provider="fake", account="fake"):
    """A lease held by a driver that is not this one, and is alive."""
    return ledger.take(
        Want(account=account, provider=provider, project="/projects/elsewhere", slug=slug, step="build"),
        ceilings,
    )


# --- a slot is one live session --------------------------------------------


def test_a_session_holds_a_slot_while_it_runs_and_gives_it_back(tmp_path, ledger):
    seen = []
    runner, _, fake = build(tmp_path, ledger, [lambda request: seen.append(ledger.held()) or GOOD])

    outcome = runner.run_next("add-login")

    assert outcome.passed
    assert [(row.slug, row.step, row.provider) for row in seen[0]] == [("add-login", "probe", "fake")]
    assert ledger.held() == []


def test_the_slot_is_given_back_even_when_the_attempt_blows_up(tmp_path, ledger):
    def explodes(request):
        raise RuntimeError("the adapter did something nobody planned for")

    runner, _, _ = build(tmp_path, ledger, [explodes, explodes, explodes])

    runner.run_next("add-login")

    assert ledger.held() == []


def test_a_program_step_is_not_a_session_and_takes_no_slot(tmp_path, ledger):
    """`verify` runs the project's own command. A slot counts sessions, whose cost is quota."""
    somebody_else(ledger, Ceilings(max_sessions=1))
    store = RunStore(tmp_path)
    create_run(store, builtin_registry(), "add-login", steps=["verify"], project=str(tmp_path))
    runner = StepRunner(
        store=store,
        registry=builtin_registry(),
        executors={"program:verify": _a_program_that_answers()},
        default_provider="fake",
        ledger=ledger,
        ceilings=Ceilings(max_sessions=1),
        wait=0,
    )

    outcome = runner.run_next("add-login")

    assert outcome.passed


# --- a machine that is full -------------------------------------------------


def test_a_full_machine_refuses_by_name_and_no_session_is_started(tmp_path, ledger):
    somebody_else(ledger, Ceilings(max_sessions=1))
    runner, store, fake = build(tmp_path, ledger, [GOOD])

    with pytest.raises(ProviderError) as refused:
        runner.run_next("add-login")

    assert refused.value.code == "no-slot"
    assert "another" in refused.value.detail
    assert fake.requests == [], "the machine was full and a session was started anyway"
    run = store.load("add-login")
    assert run.steps[0].status is StepStatus.PENDING
    assert run.steps[0].attempts == 0


def test_a_machine_that_frees_up_is_waited_for_rather_than_slept_through(tmp_path, ledger):
    lease = somebody_else(ledger, Ceilings(max_sessions=1))
    freed = []

    def pause(seconds):
        ledger.release(lease)
        freed.append(seconds)

    runner, store, fake = build(tmp_path, ledger, [GOOD], wait=60, pause=pause)

    outcome = runner.run_next("add-login")

    assert outcome.passed, "the slot came free and the run did not take it"
    assert freed, "it did not wait at all, so nothing was measured"
    assert len(fake.requests) == 1


def test_a_run_that_waits_says_so_once_and_not_once_a_second(tmp_path, ledger):
    lease = somebody_else(ledger, Ceilings(max_sessions=1))
    said = []
    waits = [0]

    def pause(seconds):
        waits[0] += 1
        if waits[0] >= 3:
            ledger.release(lease)

    runner, _, _ = build(tmp_path, ledger, [GOOD], wait=60, pause=pause)
    runner.say = said.append

    runner.run_next("add-login")

    assert len([line for line in said if "no-slot" in line]) == 1


def test_a_run_that_waits_registers_itself_so_the_queue_keeps_its_order(tmp_path, ledger):
    lease = somebody_else(ledger, Ceilings(max_sessions=1))
    queued = []

    def pause(seconds):
        queued.append([row.slug for row in ledger.queue()])
        ledger.release(lease)

    runner, _, _ = build(tmp_path, ledger, [GOOD], wait=60, pause=pause)

    runner.run_next("add-login")

    assert queued[0] == ["add-login"]
    assert ledger.queue() == [], "the waiter row outlived the wait"


# --- limits -----------------------------------------------------------------


def test_a_limit_in_the_ledger_costs_no_session_at_all(tmp_path, ledger):
    ledger.limit("fake", until=RESET, said_by="another/build")
    runner, store, fake = build(tmp_path, ledger, [GOOD])

    with pytest.raises(ProviderError) as refused:
        runner.run_next("add-login")

    assert refused.value.code == "provider-limited"
    assert RESET in refused.value.detail
    assert fake.requests == [], "the account was known to be limited and a session was paid for anyway"


def test_a_limit_a_session_found_outlives_the_session(tmp_path, ledger):
    def limited(request):
        raise ExecutorFailed("provider-limited", "the account is limited", retryable=False, until=RESET)

    runner, store, _ = build(tmp_path, ledger, [limited])

    runner.run_next("add-login")

    (held,) = ledger.limits()
    assert (held.account, held.until) == ("fake", RESET)
    assert held.said_by == "add-login/probe"
    assert not held.guessed


def test_a_limit_with_no_hour_is_still_written_down(tmp_path, ledger):
    def limited(request):
        raise ExecutorFailed("provider-limited", "the account is limited", retryable=False)

    runner, _, _ = build(tmp_path, ledger, [limited])

    runner.run_next("add-login")

    (held,) = ledger.limits()
    assert held.guessed


def test_the_account_and_not_the_provider_is_what_is_limited(tmp_path, ledger):
    """Two providers on one subscription share one quota, and `account` is how it is said."""
    ledger.limit("anthropic", until=RESET, said_by="another/build")
    runner, _, fake = build(tmp_path, ledger, [GOOD], accounts={"fake": "anthropic"})

    with pytest.raises(ProviderError) as refused:
        runner.run_next("add-login")

    assert refused.value.code == "provider-limited"


def test_a_limited_provider_falls_back_to_one_that_is_not(tmp_path, ledger):
    from agent_kit.config import RoleConfig

    ledger.limit("fake", until=RESET, said_by="another/build")
    spare = FakeExecutor(name="spare", replies=[GOOD])
    runner, store, fake = build(
        tmp_path,
        ledger,
        [GOOD],
        executors={"spare": spare},
        roles={"probe": RoleConfig(name="probe", provider="fake", fallback=["spare"])},
    )
    runner.default_provider = None

    outcome = runner.run_next("add-login")

    assert outcome.passed
    assert fake.requests == [] and len(spare.requests) == 1


# --- stop -------------------------------------------------------------------


def test_a_stop_is_read_at_a_step_boundary_and_the_run_stops_there(tmp_path, ledger):
    runner, store, fake = build(tmp_path, ledger, [GOOD], steps=["probe", "probe"])
    runner.run_next("add-login")
    ledger.ask_stop(str(tmp_path), "add-login", reason="the owner said so")

    outcome = runner.run_next("add-login")

    assert not outcome.passed
    assert outcome.interrupted
    assert "stopped-by-request" in outcome.reason and "the owner said so" in outcome.reason
    run = store.load("add-login")
    assert run.status is RunStatus.STOPPED
    assert run.steps[1].status is StepStatus.PENDING
    assert len(fake.requests) == 1, "a session was started after the run was told to stop"


def test_a_stop_is_read_once(tmp_path, ledger):
    runner, store, _ = build(tmp_path, ledger, [GOOD])
    ledger.ask_stop(str(tmp_path), "add-login", reason="the owner said so")
    runner.run_next("add-login")

    assert ledger.stop_asked(str(tmp_path), "add-login") is None


# --- one driver per run ------------------------------------------------------


def test_a_run_another_driver_holds_is_refused(tmp_path, ledger):
    ledger.hold_run(str(tmp_path), "add-login", pid=1)
    runner, _, fake = build(tmp_path, ledger, [GOOD])

    with pytest.raises(StateError) as refused:
        runner.run_next("add-login")

    assert refused.value.code == "run-held-elsewhere"
    assert fake.requests == []


def test_the_driver_that_holds_the_run_lets_it_go_when_the_run_is_over(tmp_path, ledger):
    runner, _, _ = build(tmp_path, ledger, [GOOD])

    runner.run_next("add-login")

    assert ledger.runs() == []


def test_a_run_that_is_not_over_is_still_held(tmp_path, ledger):
    runner, _, _ = build(tmp_path, ledger, [GOOD], steps=["probe", "probe"])

    runner.run_next("add-login")

    assert [row.slug for row in ledger.runs()] == ["add-login"]


# --- helpers ----------------------------------------------------------------


def _a_program_that_answers():
    from agent_kit.driver.executor import ExecutorResult

    class Program:
        name = "program:verify"

        def execute(self, request):
            return ExecutorResult(
                raw=json.dumps({"commands": [], "passed": True})
            )

    return Program()
