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


def test_every_shipped_step_has_its_prose_on_disk():
    for definition in builtin_registry().all():
        assert definition.instructions().strip(), f"{definition.name} has no method file"


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
