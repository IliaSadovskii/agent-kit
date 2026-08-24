"""S6 — reading the knowledge is not an instruction, and the contract a project imposes.

Two mechanisms, and they answer the same measured defect from two sides. The
design step decides where a block goes, so it must know what the knowledge holds
— and it is told by enclosure rather than by being sent to look. And what a
project keeps makes its contract stricter, so the agent is told about the join
in the form the program checks rather than in prose beside it.
"""

import json

import pytest

from agent_kit.driver import StepRunner, create_run
from agent_kit.providers.fake import FakeExecutor
from agent_kit.state import RunStore
from agent_kit.steps import builtin_registry

ENTITIES = """# Сущности

### Деньги
`key: money`

**Что это:** сумма в копейках
"""

DESIGN = {
    "title": "Money learns a VAT rate",
    "summary": "Money learns a VAT rate.",
    "changes": ["money.py — with_vat"],
    "seams": ["Money is frozen"],
    "verification": ["1000 at 20% is 1200"],
    "asks": [],
    "closes": [],
    # It names where the block goes and not what it says: the join is about the
    # block, and a design missing both would be refused for the address first.
    "assumptions": [
        {"what": "the rate is whole", "expensive": True, "because": "it is", "at": "entities.md#money"}
    ],
}


def reply(design):
    return "```json\n" + json.dumps(design, ensure_ascii=False) + "\n```"


def project(tmp_path, knowledge: bool):
    (tmp_path / ".agent-kit/v3").mkdir(parents=True)
    (tmp_path / ".agent-kit/v3/project.toml").write_text(
        '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "true"\n', encoding="utf-8"
    )
    if knowledge:
        (tmp_path / "docs/knowledge").mkdir(parents=True)
        (tmp_path / "docs/knowledge/entities.md").write_text(ENTITIES, encoding="utf-8")
    return tmp_path


def runner(root, replies):
    store = RunStore(root)
    create_run(store, builtin_registry(), "add-vat", steps=["design"], project=str(root),
               brief="Money should quote a price with VAT")
    return StepRunner(
        store=store, registry=builtin_registry(),
        executors={"fake": FakeExecutor(name="fake", replies=replies)},
        default_provider="fake",
    ), store


def input_of(root, attempt=1):
    return (root / f".agent-kit/v3/runs/add-vat/steps/0-design/attempt-{attempt}/input.md").read_text()


# --- what is enclosed --------------------------------------------------------


def test_the_design_step_is_handed_the_knowledge_it_must_address(tmp_path):
    root = project(tmp_path, knowledge=True)
    run_step, _ = runner(root, [reply(dict(DESIGN, assumptions=[]))])

    run_step.run_next("add-vat")

    assert "entities.md#money" in input_of(root)


def test_a_project_that_keeps_no_knowledge_says_so_in_the_input(tmp_path):
    root = project(tmp_path, knowledge=False)
    run_step, _ = runner(root, [reply(dict(DESIGN, assumptions=[]))])

    run_step.run_next("add-vat")

    assert "keeps no knowledge" in input_of(root)


def test_a_step_that_does_not_address_the_knowledge_is_not_handed_it(tmp_path):
    root = project(tmp_path, knowledge=True)
    store = RunStore(root)
    create_run(store, builtin_registry(), "look", steps=["probe"], project=str(root))
    StepRunner(
        store=store, registry=builtin_registry(),
        executors={"fake": FakeExecutor(name="fake", replies=['```json\n{"branch": "x", "can_write": true}\n```'])},
        default_provider="fake",
    ).run_next("look")

    text = (root / ".agent-kit/v3/runs/look/steps/0-probe/attempt-1/input.md").read_text()
    assert "entities.md#money" not in text


# --- the contract a project imposes ------------------------------------------


def test_an_expensive_assumption_with_no_block_is_refused_where_a_retry_is_cheap(tmp_path):
    root = project(tmp_path, knowledge=True)
    run_step, store = runner(root, [reply(DESIGN)] * 3)

    outcome = run_step.run_next("add-vat")

    assert not outcome.passed
    assert "output-missing-field: assumptions[0].block" in outcome.attempts[0].refusal
    assert store.load("add-vat").status.value == "failed"


def test_the_same_design_passes_in_a_project_that_keeps_no_knowledge(tmp_path):
    root = project(tmp_path, knowledge=False)
    run_step, _ = runner(root, [reply(DESIGN)])

    assert run_step.run_next("add-vat").passed


def test_the_requirement_is_in_the_input_the_agent_reads(tmp_path):
    root = project(tmp_path, knowledge=True)
    run_step, _ = runner(root, [reply(DESIGN)] * 3)

    run_step.run_next("add-vat")

    assert "required when `expensive`" in input_of(root)


def test_the_second_attempt_is_told_which_field_was_missing(tmp_path):
    root = project(tmp_path, knowledge=True)
    run_step, _ = runner(root, [reply(DESIGN)] * 3)

    run_step.run_next("add-vat")

    assert "assumptions[0].block" in input_of(root, attempt=2)
