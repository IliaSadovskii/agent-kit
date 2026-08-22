"""S4 — the steps that are programs.

Question 1 of the plan's four, applied to the method itself: *can this be a
program instead?* An agent cannot lie about green tests it did not run, so the
kit runs them. The step contract does not change — an input the driver
composes, an executor, an output the driver validates — which is the point of
having frozen it at S2.
"""

import json

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.errors import ProviderError
from agent_kit.programs import build_program, program_names
from agent_kit.providers.base import ExecutorFailed, StepRequest
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStore, StepStatus
from agent_kit.steps import Contract, Registry, StepDefinition, builtin_registry
from agent_kit.steps.contract import Text


def declare(root, text):
    path = root / ".agent-kit/v3/project.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def request(root, step="verify", prior=None):
    return StepRequest(
        slug="add-vat",
        step_name=step,
        attempt=1,
        provider=f"program:{step}",
        input_text="",
        workdir=root,
        project=root,
        branch="kit/add-vat",
        brief="Money should know about VAT",
        prior=prior or {},
    )


def answer(result):
    return json.loads(result.raw)


# --- a program is an executor like any other -------------------------------


def test_the_kit_ships_the_programs_the_method_needs():
    assert "program:verify" in program_names()


def test_a_step_may_name_a_program_instead_of_a_role(tmp_path):
    declare(tmp_path, '[commands]\ntest = "true"\n')
    definition = builtin_registry().get("verify")

    assert definition.executor == "program:verify"
    assert not definition.by_agent


def test_a_program_nobody_ships_is_refused_before_anything_runs(tmp_path):
    with pytest.raises(ProviderError) as refused:
        build_program("program:invent", tmp_path)
    assert refused.value.code == "unknown-program"


# --- verify runs the project's own commands --------------------------------


def test_verify_runs_what_the_project_declared_and_records_what_it_printed(tmp_path):
    declare(tmp_path, '[commands]\nlint = "echo tidy"\ntest = "echo four passed"\n')

    said = answer(build_program("program:verify", tmp_path).execute(request(tmp_path)))

    assert said["passed"] is True
    assert [command["name"] for command in said["commands"]] == ["lint", "test"]
    assert said["commands"][1]["exit_code"] == 0
    assert "four passed" in said["commands"][1]["output"]


def test_a_command_that_fails_makes_the_step_say_so_and_keeps_what_it_printed(tmp_path):
    declare(tmp_path, '[commands]\ntest = "echo one failed >&2; exit 3"\n')

    said = answer(build_program("program:verify", tmp_path).execute(request(tmp_path)))

    assert said["passed"] is False
    assert said["commands"][0]["exit_code"] == 3
    assert said["commands"][0]["passed"] is False
    assert "one failed" in said["commands"][0]["output"]


def test_a_failing_command_stops_the_ones_after_it(tmp_path):
    declare(tmp_path, '[commands]\nlint = "exit 1"\ntest = "echo ran anyway"\n')

    said = answer(build_program("program:verify", tmp_path).execute(request(tmp_path)))

    assert [command["name"] for command in said["commands"]] == ["lint"]
    assert said["passed"] is False


def test_verify_refuses_a_project_that_never_said_how_it_is_tested(tmp_path):
    declare(tmp_path, '[project]\ndefault_branch = "main"\n')

    with pytest.raises(ExecutorFailed) as refused:
        build_program("program:verify", tmp_path).execute(request(tmp_path))
    assert refused.value.code == "no-commands"
    assert refused.value.retryable is False


def test_what_verify_returns_satisfies_the_step_it_belongs_to(tmp_path):
    declare(tmp_path, '[commands]\ntest = "echo ok"\n')
    definition = builtin_registry().get("verify")

    from agent_kit.steps.contract import parse_output

    raw = build_program("program:verify", tmp_path).execute(request(tmp_path)).raw

    assert definition.contract.check(parse_output(raw))["passed"] is True


# --- the driver runs a program step the same way it runs a session ---------


def test_the_driver_runs_a_program_step_and_records_it(tmp_path):
    declare(tmp_path, '[commands]\ntest = "echo green"\n')
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(store, registry, "add-vat", steps=["verify"], project=str(tmp_path))

    runner = StepRunner(
        store=store,
        registry=registry,
        executors={"program:verify": build_program("program:verify", tmp_path)},
    )
    outcome = runner.run_next("add-vat")

    assert outcome.passed
    assert outcome.output["passed"] is True
    run = store.load("add-vat")
    assert run.steps[0].status is StepStatus.PASSED
    assert run.steps[0].provider == "program:verify"


def test_a_program_step_gets_one_attempt_not_three(tmp_path):
    declare(tmp_path, '[commands]\ntest = "exit 1"\n')
    store = RunStore(tmp_path)
    registry = Registry(
        [
            StepDefinition(
                name="verify",
                role="verify",
                executor="program:verify",
                contract=Contract(fields=(Text("nothing_like_this"),)),
            )
        ]
    )
    create_run(store, registry, "add-vat", steps=["verify"], project=str(tmp_path))

    runner = StepRunner(
        store=store,
        registry=registry,
        executors={"program:verify": build_program("program:verify", tmp_path)},
    )
    outcome = runner.run_next("add-vat")

    assert not outcome.passed
    assert len(outcome.attempts) == 1  # a program refused once is refused the same way twice


def test_a_program_is_handed_what_earlier_steps_returned_as_data(tmp_path):
    declare(tmp_path, '[commands]\ntest = "true"\n')
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(store, registry, "add-vat", steps=["probe", "verify"], project=str(tmp_path))

    seen = {}

    class Watching:
        name = "program:verify"

        def execute(self, incoming):
            seen.update(incoming.prior)
            return build_program("program:verify", tmp_path).execute(incoming)

    runner = StepRunner(
        store=store,
        registry=registry,
        executors={
            "fake": FakeExecutor(replies=['```json\n{"branch": "main", "can_write": true}\n```']),
            "program:verify": Watching(),
        },
        default_provider="fake",
    )
    runner.run_next("add-vat")
    runner.run_next("add-vat")

    assert seen["probe"]["branch"] == "main"


def test_a_program_is_told_the_branch_and_the_brief_without_reading_prose(tmp_path):
    declare(tmp_path, '[commands]\ntest = "true"\n')
    store = RunStore(tmp_path)
    registry = builtin_registry()
    create_run(store, registry, "add-vat", steps=["verify"], project=str(tmp_path))
    store.update("add-vat", lambda run: setattr(run, "brief", "VAT"))

    seen = {}

    class Watching:
        name = "program:verify"

        def execute(self, incoming):
            seen["branch"] = incoming.branch
            seen["brief"] = incoming.brief
            return build_program("program:verify", tmp_path).execute(incoming)

    StepRunner(
        store=store, registry=registry, executors={"program:verify": Watching()}
    ).run_next("add-vat")

    assert seen == {"branch": "kit/add-vat", "brief": "VAT"}


def test_a_program_does_not_pretend_to_be_a_model(tmp_path):
    """`run show` reads meta.model to say who did the work. No program did."""
    declare(tmp_path, '[commands]\ntest = "true"\n')

    meta = build_program("program:verify", tmp_path).execute(request(tmp_path)).meta

    assert "model" not in meta
    assert meta["commands_run"] == 1


def test_a_command_that_hangs_takes_its_children_with_it(tmp_path):
    """`make test` is `docker compose exec`. A build left running spends a shared machine."""
    from agent_kit.programs.verify import Verify

    mark = tmp_path / "still-alive"
    declare(tmp_path, f'[commands]\ntest = "(while true; do echo x >> {mark}; sleep 0.2; done) & sleep 30"\n')

    said = answer(Verify(tmp_path, timeout=2).execute(request(tmp_path)))

    assert said["passed"] is False
    assert said["commands"][0]["exit_code"] is None
    grew = mark.stat().st_size if mark.exists() else 0
    __import__("time").sleep(1.5)
    assert (mark.stat().st_size if mark.exists() else 0) == grew


def test_verify_waits_as_long_as_the_project_said_and_no_longer(tmp_path):
    """The kit's hour is a default, not a rule: a project knows its own suite."""
    from agent_kit.programs.verify import Verify

    mark = tmp_path / "still-alive"
    declare(
        tmp_path,
        "[project]\ncommand_timeout = 2\n\n"
        f'[commands]\ntest = "(while true; do echo x >> {mark}; sleep 0.2; done) & sleep 30"\n',
    )

    said = answer(Verify(tmp_path).execute(request(tmp_path)))

    assert said["passed"] is False
    assert "2 seconds" in said["commands"][0]["output"]
