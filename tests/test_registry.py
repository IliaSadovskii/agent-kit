"""S2 — the registry. A step name means one definition, and an unknown one is refused early."""

import pytest

from agent_kit.errors import StateError
from agent_kit.state import RunStore
from agent_kit.steps import Registry, StepDefinition, builtin_registry
from agent_kit.steps.contract import Contract, Text


def test_the_kit_ships_the_probe_step():
    registry = builtin_registry()

    probe = registry.get("probe")

    assert probe.name == "probe"
    assert probe.method  # it has prose, and the prose is on disk
    assert [field.name for field in probe.contract.fields]


def test_every_step_a_session_does_has_its_prose_on_disk():
    for definition in builtin_registry().all():
        if definition.by_agent:
            assert definition.instructions().strip(), f"{definition.name} has no method file"


def test_a_step_a_program_does_carries_no_prose_at_all():
    """Prose with no reader is not written, and nobody reads instructions to a program."""
    for definition in builtin_registry().all():
        if not definition.by_agent:
            assert definition.method == ""


def test_an_unknown_step_is_refused_by_name():
    with pytest.raises(StateError) as caught:
        builtin_registry().get("nonesuch")

    assert caught.value.code == "unknown-step"


def test_a_registry_refuses_two_definitions_of_one_name():
    definition = StepDefinition(name="probe", role="probe", method="roles/probe.md", contract=Contract((Text("x"),)))
    registry = Registry()
    registry.add(definition)

    with pytest.raises(StateError) as caught:
        registry.add(definition)

    assert caught.value.code == "step-exists"


def test_a_run_may_only_be_created_from_steps_that_exist(tmp_path):
    from agent_kit.driver import create_run

    store = RunStore(tmp_path)

    with pytest.raises(StateError) as caught:
        create_run(store, builtin_registry(), "add-login", steps=["probe", "nonesuch"])

    assert caught.value.code == "unknown-step"
    assert not store.exists("add-login")


def test_the_state_itself_knows_nothing_about_steps(tmp_path):
    """Dependencies flow one way: state, then the step contract, then the driver."""
    assert RunStore(tmp_path).create("add-login", steps=["whatever"]).steps[0].name == "whatever"


def test_the_prose_of_a_step_does_not_promise_what_the_driver_does_not_enclose():
    """`compose.py` encloses the brief and earlier outputs. Nothing else exists to promise."""
    for definition in builtin_registry().all():
        if not definition.by_agent:
            continue
        prose = definition.instructions()
        assert "knowledge are enclosed" not in prose
        assert "enclosed knowledge" not in prose


# --- which of the kit's own lists may not be empty ---------------------------


def test_a_design_that_will_prove_nothing_is_not_a_design():
    design = builtin_registry().get("design").contract

    assert design.field("verification").empty_is_an_answer is False
    assert design.field("changes").empty_is_an_answer is False


def test_a_build_that_wrote_no_file_and_no_test_did_not_build():
    build = builtin_registry().get("build").contract

    assert build.field("files").empty_is_an_answer is False
    assert build.field("tests").empty_is_an_answer is False


def test_the_questions_whose_real_answer_can_be_nothing_keep_it():
    """Considered and had nothing is an answer, and the kit turns on the difference."""
    registry = builtin_registry()
    design = registry.get("design").contract

    assert design.field("assumptions").empty_is_an_answer is True
    assert design.field("asks").empty_is_an_answer is True
    assert design.field("closes").empty_is_an_answer is True
    assert design.field("seams").empty_is_an_answer is True
    assert registry.get("build").contract.field("deviations").empty_is_an_answer is True
    assert registry.get("review").contract.field("findings").empty_is_an_answer is True


def test_what_a_program_writes_is_not_a_step_answering_nothing():
    """`record` writes no block for a feature that assumed nothing, and says so."""
    record = builtin_registry().get("record").contract

    assert record.field("blocks").empty_is_an_answer is True
    assert record.field("closed").empty_is_an_answer is True
    assert record.field("files").empty_is_an_answer is True
