"""S6 — `record`: the step that writes the knowledge, and it is a program.

The plan's sentence for this step is one line — *the model returns fields, the
driver writes the file and the mark* — and the reason it is a program rather
than a role is the same as `verify`'s: an agent that writes the file itself can
always claim it did.

It runs before `deliver` and asks the deliverable question first, so a blocking
finding stops the run before anything reaches the owner's knowledge.
"""

import json

import pytest

from agent_kit.knowledge import Knowledge, identifier
from agent_kit.programs import build_program
from agent_kit.providers.base import ExecutorFailed, StepRequest
from agent_kit.steps import builtin_registry
from agent_kit.steps.contract import parse_output

ENTITIES = """# Сущности

### Деньги
`key: money`

**Что это:** сумма в копейках

### Налог
`key: tax`

**Что это:** ставка налога
"""

WHAT = "VAT is a whole percent"

DESIGN = {
    "title": "Money learns a VAT rate",
    "summary": "Money learns a VAT rate.",
    "changes": ["money.py — with_vat"],
    "seams": ["Money is frozen"],
    "verification": ["1000 at 20% is 1200"],
    "needs_owner": [],
    "closes": [],
    "assumptions": [
        {
            "what": WHAT,
            "expensive": True,
            "because": "nothing in the sandbox uses fractions",
            "at": "entities.md#money",
            "block": "Nothing says the rate is a whole percent; took it as one, and a fraction would round.",
        }
    ],
}

BUILD = {"complete": True, "summary": "with_vat", "files": ["money.py"], "tests": ["test_vat"],
         "deviations": [], "remaining": None}
VERIFY = {"commands": [{"name": "test", "command": "true", "exit_code": 0, "passed": True, "output": ""}],
          "passed": True}
REVIEW = {"verdict": "pass", "findings": []}
BLOCKED = {"verdict": "blocked",
           "findings": [{"severity": "blocking", "what": "a negative rate is not refused"}]}


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / ".agent-kit/v3").mkdir(parents=True)
    (root / ".agent-kit/v3/project.toml").write_text(
        '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "true"\n', encoding="utf-8"
    )
    (root / "docs/knowledge").mkdir(parents=True)
    (root / "docs/knowledge/entities.md").write_text(ENTITIES, encoding="utf-8")
    return root


@pytest.fixture
def without_knowledge(tmp_path):
    root = tmp_path / "bare"
    (root / ".agent-kit/v3").mkdir(parents=True)
    (root / ".agent-kit/v3/project.toml").write_text(
        '[project]\ndefault_branch = "main"\n\n[commands]\ntest = "true"\n', encoding="utf-8"
    )
    return root


def record(root, prior=None):
    whole = {"design": DESIGN, "build": BUILD, "verify": VERIFY, "review": REVIEW, **(prior or {})}
    request = StepRequest(
        slug="add-vat", step_name="record", attempt=1, provider="program:record", input_text="",
        workdir=root, project=root, branch="kit/add-vat", brief="VAT", prior=whole,
    )
    return build_program("program:record", root).execute(request)


def entities(root):
    return (root / "docs/knowledge/entities.md").read_text(encoding="utf-8")


# --- what it writes ----------------------------------------------------------


def test_an_expensive_assumption_becomes_a_block_under_the_record_it_named(project):
    record(project)

    text = entities(project)
    assert "kit/add-vat" in text
    assert "a fraction would round" in text
    assert text.index("kit/add-vat") < text.index("### Налог")


def test_the_block_carries_the_identifier_the_same_run_would_produce_again(project):
    said = json.loads(record(project).raw)

    assert said["blocks"][0]["id"] == identifier("add-vat", WHAT)
    assert said["blocks"][0]["at"] == "entities.md#money"
    assert said["blocks"][0]["what"] == WHAT


def test_what_it_returns_satisfies_the_step_it_belongs_to(project):
    raw = record(project).raw

    output = builtin_registry().get("record").contract.check(parse_output(raw))
    assert output["files"] == ["docs/knowledge/entities.md"]


def test_an_assumption_that_is_not_expensive_owes_nothing(project):
    cheap = dict(DESIGN, assumptions=[{"what": "the file is utf-8", "expensive": False, "because": "it is"}])

    said = json.loads(record(project, {"design": cheap}).raw)

    assert said["blocks"] == []
    assert said["files"] == []
    assert "kit/add-vat" not in entities(project)


def test_running_it_twice_leaves_one_block(project):
    record(project)
    record(project)

    assert entities(project).count("kit/add-vat") == 1


def test_a_program_does_not_pretend_to_be_a_model(project):
    assert "model" not in record(project).meta


# --- the join ----------------------------------------------------------------


def test_an_expensive_assumption_with_no_block_stops_the_run(project):
    naked = dict(DESIGN, assumptions=[{"what": WHAT, "expensive": True, "because": "it is"}])

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": naked})

    assert refused.value.code == "assumption-with-no-block"
    assert WHAT in refused.value.detail
    assert refused.value.retryable is False


def test_the_join_binds_a_project_that_keeps_knowledge_and_not_one_that_keeps_none(without_knowledge):
    naked = dict(DESIGN, assumptions=[{"what": WHAT, "expensive": True, "because": "it is"}])

    said = json.loads(record(without_knowledge, {"design": naked}).raw)

    assert said["blocks"] == []
    assert said["files"] == []


def test_an_address_that_resolves_to_nothing_is_refused_rather_than_guessed(project):
    astray = dict(DESIGN, assumptions=[dict(DESIGN["assumptions"][0], at="entities.md#ghost")])

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": astray})

    assert refused.value.code == "no-such-record"
    assert "kit/add-vat" not in entities(project)


# --- closing -----------------------------------------------------------------


def test_it_closes_what_the_design_named(project):
    record(project)
    wanted = identifier("add-vat", WHAT)

    said = json.loads(record(project, {"design": dict(DESIGN, assumptions=[], closes=[wanted])}).raw)

    assert said["closed"] == [wanted]
    assert "kit/add-vat" not in entities(project)


def test_closing_an_identifier_the_knowledge_does_not_hold_stops_the_run(project):
    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": dict(DESIGN, assumptions=[], closes=["zzzzzz"])})

    assert refused.value.code == "no-such-block"


def test_closing_in_a_project_that_keeps_no_knowledge_is_refused(without_knowledge):
    with pytest.raises(ExecutorFailed) as refused:
        record(without_knowledge, {"design": dict(DESIGN, assumptions=[], closes=["zzzzzz"])})

    assert refused.value.code == "no-knowledge"


# --- it refuses before it writes ---------------------------------------------


def test_a_blocking_finding_stops_the_run_before_the_knowledge_is_touched(project):
    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"review": BLOCKED})

    assert refused.value.code == "blocked-by-review"
    assert refused.value.expected is True
    assert "kit/add-vat" not in entities(project)


def test_a_red_suite_stops_the_run_before_the_knowledge_is_touched(project):
    red = {"commands": [{"name": "test", "command": "false", "exit_code": 1, "passed": False, "output": ""}],
           "passed": False}

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"verify": red})

    assert refused.value.code == "not-verified"
    assert "kit/add-vat" not in entities(project)


def test_a_build_that_never_finished_stops_the_run_before_the_knowledge_is_touched(project):
    half = dict(BUILD, complete=False, remaining=["the rounding"])

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"build": half})

    assert refused.value.code == "build-unfinished"
    assert "kit/add-vat" not in entities(project)


def test_it_refuses_when_the_steps_it_reads_never_ran(project):
    request = StepRequest(
        slug="add-vat", step_name="record", attempt=1, provider="program:record", input_text="",
        workdir=project, project=project, branch="kit/add-vat", brief="VAT", prior={},
    )

    with pytest.raises(ExecutorFailed) as refused:
        build_program("program:record", project).execute(request)

    assert refused.value.code == "nothing-to-read"
