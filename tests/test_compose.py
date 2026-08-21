"""S2 — composing a step's input. Reading is never an instruction; it arrives enclosed."""

from agent_kit.driver.compose import compose_input
from agent_kit.state import RunStore
from agent_kit.steps import builtin_registry


def build(tmp_path, **kwargs):
    store = RunStore(tmp_path, registry=builtin_registry())
    run = store.create("add-login", steps=["probe"], project=str(tmp_path))
    registry = builtin_registry()
    return compose_input(run=run, step=run.steps[0], definition=registry.get("probe"), **kwargs)


def test_the_input_carries_the_facts_of_the_run(tmp_path):
    text = build(tmp_path, attempt=1, provider="fake")

    assert "add-login" in text
    assert "kit/add-login" in text
    assert "fake" in text
    assert "attempt 1" in text


def test_the_input_carries_the_role_prose(tmp_path):
    text = build(tmp_path, attempt=1, provider="fake")

    assert builtin_registry().get("probe").instructions().splitlines()[0].strip("# ") in text


def test_the_input_carries_the_contract_and_the_envelope(tmp_path):
    text = build(tmp_path, attempt=1, provider="fake")

    assert "```json" in text  # how to return an output
    for field in builtin_registry().get("probe").contract.fields:
        assert field.name in text


def test_what_must_be_read_is_enclosed_not_asked_for(tmp_path):
    text = build(
        tmp_path,
        attempt=1,
        provider="fake",
        enclosures=[("the design step said", '{"seams": ["the clock"]}')],
    )

    assert "the design step said" in text
    assert '"seams"' in text


def test_a_retry_encloses_why_the_last_attempt_was_refused(tmp_path):
    text = build(tmp_path, attempt=2, provider="fake", refusal="output-missing-field: branch")

    assert "attempt 2" in text
    assert "output-missing-field: branch" in text


def test_a_first_attempt_says_nothing_about_refusals(tmp_path):
    assert "The previous attempt was refused" not in build(tmp_path, attempt=1, provider="fake")
