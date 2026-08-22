"""S2 — composing a step's input. Reading is never an instruction; it arrives enclosed."""

from agent_kit.driver.compose import compose_input
from agent_kit.state import RunStore
from agent_kit.steps import builtin_registry


def build(tmp_path, **kwargs):
    run = RunStore(tmp_path).create("add-login", steps=["probe"], project=str(tmp_path))
    return compose_input(run=run, definition=builtin_registry().get("probe"), **kwargs)


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


def test_an_enclosure_that_holds_a_fence_does_not_break_the_input(tmp_path):
    body = "```json\n{\"a\": 1}\n```"

    text = build(tmp_path, attempt=1, provider="fake", enclosures=[("an earlier step", body)])

    assert "````" in text  # a longer fence than the one inside


def test_a_retry_encloses_why_the_last_attempt_was_refused(tmp_path):
    text = build(tmp_path, attempt=2, provider="fake", refusal="output-missing-field: branch")

    assert "attempt 2" in text
    assert "output-missing-field: branch" in text


def test_a_first_attempt_says_nothing_about_refusals(tmp_path):
    assert "The previous attempt was refused" not in build(tmp_path, attempt=1, provider="fake")


# --- S4: the brief is what the whole run is for ----------------------------


def test_the_brief_is_enclosed_so_no_step_has_to_be_told_what_it_is_building(tmp_path):
    run = RunStore(tmp_path).create(
        "add-vat", steps=["probe"], project=str(tmp_path), brief="Money should know about VAT"
    )

    text = compose_input(
        run=run, definition=builtin_registry().get("probe"), attempt=1, provider="fake"
    )

    assert "Money should know about VAT" in text


def test_a_run_with_no_brief_says_nothing_about_one(tmp_path):
    text = build(tmp_path, attempt=1, provider="fake")

    assert "What this run is for" not in text


def test_a_program_step_is_given_a_record_not_instructions(tmp_path):
    """Nobody reads prose to a program. Its input.md is what it was handed."""
    run = RunStore(tmp_path).create("add-vat", steps=["verify"], project=str(tmp_path), brief="VAT")

    text = compose_input(
        run=run,
        definition=builtin_registry().get("verify"),
        attempt=1,
        provider="program:verify",
        enclosures=[("0-design returned", '{"summary": "add a rate"}')],
    )

    assert "What you must return" not in text
    assert "add a rate" in text
    assert "VAT" in text


def test_the_input_tells_a_session_the_branch_is_not_its_business(tmp_path):
    """A session that reads `branch:` as an instruction creates it, and deliver then refuses."""
    run = RunStore(tmp_path).create("add-vat", steps=["probe"], project=str(tmp_path), brief="VAT")

    text = compose_input(
        run=run, definition=builtin_registry().get("probe"), attempt=1, provider="fake"
    )

    assert "do not create it" in text
