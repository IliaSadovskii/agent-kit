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
    "proves": [],
    "asks": [],
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


def record(root, prior=None, tree=None):
    whole = {"design": DESIGN, "build": BUILD, "verify": VERIFY, "review": REVIEW, **(prior or {})}
    request = StepRequest(
        slug="add-vat", step_name="record", attempt=1, provider="program:record", input_text="",
        workdir=root, project=root, tree=tree, branch="kit/add-vat", brief="VAT", prior=whole,
    )
    return build_program("program:record", root).execute(request)


@pytest.fixture
def tree(tmp_path):
    """The working copy this run builds in: a worktree of the same repository.

    It holds the repository's content and none of the kit's paperwork — the run
    state and the declaration stay in the project — which is why the knowledge
    is here and `project.toml` is not.
    """
    where = tmp_path / "project/.agent-kit/v3/trees/add-vat"
    (where / "docs/knowledge").mkdir(parents=True)
    (where / "docs/knowledge/entities.md").write_text(ENTITIES, encoding="utf-8")
    return where


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


# --- what a careful read of it found -----------------------------------------


def test_nothing_is_written_until_every_address_has_resolved(project):
    """A half-written knowledge is worse than an unwritten one.

    Two expensive assumptions, and the second names a record that is not there.
    Writing as it goes would leave the first block on disk under a run that
    failed, in a working copy nobody will look at again.
    """
    two = dict(
        DESIGN,
        assumptions=[
            DESIGN["assumptions"][0],
            dict(DESIGN["assumptions"][0], what="the tax is charged once", at="entities.md#ghost"),
        ],
    )

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": two})

    assert refused.value.code == "no-such-record"
    assert "kit/add-vat" not in entities(project)


def test_nothing_is_closed_until_every_address_has_resolved(project):
    record(project)
    standing = entities(project)
    both = dict(DESIGN, assumptions=[], closes=[identifier("add-vat", WHAT), "zzzzzz"])

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": both})

    assert refused.value.code == "no-such-block"
    assert entities(project) == standing


# --- what the review round found ---------------------------------------------


def test_two_assumptions_worded_the_same_get_two_blocks(project):
    """The identifier is derived from the run and the words, so siblings collide.

    Reusing it made the second block delete the first, and the step still
    reported two — the record lying about the knowledge, which is the one thing
    a step that exists to leave a trace may not do.
    """
    twice = dict(
        DESIGN,
        assumptions=[
            DESIGN["assumptions"][0],
            dict(DESIGN["assumptions"][0], at="entities.md#tax"),
        ],
    )

    said = json.loads(record(project, {"design": twice}).raw)

    ids = [block["id"] for block in said["blocks"]]
    assert len(set(ids)) == 2, ids
    text = entities(project)
    assert text.count("kit/add-vat") == 2
    assert all(id in text for id in ids)


def test_the_same_two_assumptions_written_again_are_still_two(project):
    twice = dict(
        DESIGN,
        assumptions=[DESIGN["assumptions"][0], dict(DESIGN["assumptions"][0], at="entities.md#tax")],
    )
    first = json.loads(record(project, {"design": twice}).raw)

    again = json.loads(record(project, {"design": twice}).raw)

    assert [b["id"] for b in again["blocks"]] == [b["id"] for b in first["blocks"]]
    assert entities(project).count("kit/add-vat") == 2


def test_the_same_identifier_named_twice_in_closes_is_closed_once(project):
    record(project)
    wanted = identifier("add-vat", WHAT)

    said = json.loads(record(project, {"design": dict(DESIGN, assumptions=[], closes=[wanted, wanted])}).raw)

    assert said["closed"] == [wanted]
    assert "kit/add-vat" not in entities(project)


def test_a_block_that_moved_to_another_file_names_both_of_them(project):
    (project / "docs/knowledge/stack.md").write_text(
        "# Стек\n\n## Вызовы модели\n\nвсё через шлюз\n", encoding="utf-8"
    )
    record(project)

    moved = dict(DESIGN, assumptions=[dict(DESIGN["assumptions"][0], at="stack.md#Вызовы модели")])
    said = json.loads(record(project, {"design": moved}).raw)

    assert sorted(said["files"]) == ["docs/knowledge/entities.md", "docs/knowledge/stack.md"]
    assert "kit/add-vat" not in entities(project)


# --- which working copy it writes into ---------------------------------------
#
# A run builds in its own worktree, and the knowledge is repository content: the
# block belongs in the tree, so `deliver` commits it onto the branch. Written
# into the project's own checkout it reaches neither the branch nor the owner —
# it is an uncommitted edit on whatever they had checked out.


def test_the_block_is_written_in_the_tree_the_run_builds_in(project, tree):
    record(project, tree=tree)

    assert "kit/add-vat" in entities(tree)
    assert "kit/add-vat" not in entities(project)


def test_closing_takes_the_block_out_of_the_tree_and_leaves_the_project_alone(project, tree):
    record(project, tree=tree)
    wanted = identifier("add-vat", WHAT)
    planted = entities(project)

    said = json.loads(record(project, {"design": dict(DESIGN, assumptions=[], closes=[wanted])}, tree=tree).raw)

    assert said["closed"] == [wanted]
    assert "kit/add-vat" not in entities(tree)
    assert entities(project) == planted


def test_where_the_knowledge_lives_is_the_project_s_word_about_the_tree(project, tree):
    (project / ".agent-kit/v3/project.toml").write_text(
        '[project]\ndefault_branch = "main"\nknowledge = "docs/wisdom"\n\n[commands]\ntest = "true"\n',
        encoding="utf-8",
    )
    (tree / "docs/wisdom").mkdir(parents=True)
    (tree / "docs/wisdom/entities.md").write_text(ENTITIES, encoding="utf-8")

    said = json.loads(record(project, tree=tree).raw)

    assert said["files"] == ["docs/wisdom/entities.md"]
    assert "kit/add-vat" in (tree / "docs/wisdom/entities.md").read_text(encoding="utf-8")


# --- S8f: what the review found, and what the work answers -------------------
#
# `record` reads the ledger and writes none of it. The file has one writer — the
# night of a batch, once, when there is nothing left to build — because two
# features branching from one base and appending to one section is two branches
# that will not merge: measured, 200 of 200. What this step does is name the
# lines: their keys, derived, so the evening writes what the feature decided.

WORTH_FIXING = {
    "verdict": "pass",
    "findings": [
        {"severity": "worth-fixing", "what": "the retry loop swallows the reason", "where": "money.py:90"},
        {"severity": "note", "what": "the name could be shorter"},
    ],
}


def ledger_of(root):
    from agent_kit.knowledge import Knowledge

    return Knowledge(root / "docs/knowledge")


def with_a_ledger(root, *lines):
    from agent_kit.knowledge.debt import BADLY

    held = ledger_of(root)
    for what in lines:
        held.write_debt(what, BADLY)
    return held


def test_a_worth_fixing_finding_is_named_with_the_key_the_kit_derives(project):
    from agent_kit.knowledge.debt import debt_key

    said = json.loads(record(project, {"review": WORTH_FIXING}).raw)

    assert said["debt"] == [
        {"key": debt_key("the retry loop swallows the reason (money.py:90)"),
         "what": "the retry loop swallows the reason (money.py:90)"}
    ]


def test_a_note_is_not_debt(project):
    """It costs nothing and blocks nothing; a line in the owner's ledger costs something."""
    said = json.loads(record(project, {"review": WORTH_FIXING}).raw)

    assert "the name could be shorter" not in json.dumps(said, ensure_ascii=False)


def test_two_findings_worded_alike_are_two_lines(project):
    """A set answering for two is the blocker S6 paid for, in the ledger's terms."""
    twice = {"verdict": "pass", "findings": [
        {"severity": "worth-fixing", "what": "the same thing"},
        {"severity": "worth-fixing", "what": "the same thing"},
    ]}
    said = json.loads(record(project, {"review": twice}).raw)

    assert len({one["key"] for one in said["debt"]}) == 2


def test_the_step_writes_no_line_of_the_ledger_itself(project):
    record(project, {"review": WORTH_FIXING})

    assert not (project / "docs/knowledge/debt.md").exists()


def test_the_work_names_the_debt_it_does(project):
    from agent_kit.knowledge.debt import debt_key

    with_a_ledger(project, "отчёт считает вручную", "почта уходит дважды")
    design = {**DESIGN, "fixes": [debt_key("отчёт считает вручную")]}

    said = json.loads(record(project, {"design": design}).raw)

    assert said["fixed"] == [debt_key("отчёт считает вручную")]
    # And the line is still there: the evening takes it away, not the feature.
    assert "отчёт считает вручную" in (project / "docs/knowledge/debt.md").read_text(encoding="utf-8")


def test_a_key_no_line_carries_stops_the_run_by_name(project):
    with_a_ledger(project, "отчёт считает вручную")
    design = {**DESIGN, "fixes": ["zzzzzz"]}

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": design})

    assert refused.value.code == "no-such-debt"
    # Nothing resolved, so nothing was written: not the block either.
    assert "kit/add-vat" not in entities(project)


def test_a_project_that_keeps_no_knowledge_owes_no_ledger(without_knowledge):
    said = json.loads(record(without_knowledge, {"review": WORTH_FIXING}).raw)

    assert said["debt"] == []
    assert said["fixed"] == []


def test_a_project_that_keeps_no_knowledge_cannot_be_told_it_fixed_a_line(without_knowledge):
    design = {**DESIGN, "fixes": ["zzzzzz"], "assumptions": []}

    with pytest.raises(ExecutorFailed) as refused:
        record(without_knowledge, {"design": design})

    assert refused.value.code == "no-knowledge"


# --- S8f: which ledger is the authority --------------------------------------
#
# The blocks a run writes go into its own worktree and `deliver` commits them.
# The ledger is never committed by anybody: the evening writes it into the
# owner's checkout and the owner reads the diff. So the copy in a run's tree is
# the base of its branch — older by exactly the lines the last night laid — and
# asking it whether a line exists refuses the run for a line that is standing.


def test_a_line_the_owner_has_not_committed_is_a_line(project, tree):
    from agent_kit.knowledge.debt import debt_key

    with_a_ledger(project, "отчёт по периодам считается вручную")  # the checkout only
    design = {**DESIGN, "fixes": [debt_key("отчёт по периодам считается вручную")]}

    said = json.loads(record(project, {"design": design}, tree=tree).raw)

    assert said["fixed"] == [debt_key("отчёт по периодам считается вручную")]


def test_a_line_only_the_run_s_own_tree_holds_is_not_one(project, tree):
    """The tree is a copy; the owner's checkout is where the ledger lives."""
    from agent_kit.knowledge import Knowledge
    from agent_kit.knowledge.debt import BADLY, debt_key

    Knowledge(tree / "docs/knowledge").write_debt("что-то, чего в чекауте нет", BADLY)
    design = {**DESIGN, "fixes": [debt_key("что-то, чего в чекауте нет")]}

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": design}, tree=tree)

    assert refused.value.code == "no-such-debt"


def test_the_key_of_a_finding_is_derived_against_the_owner_s_ledger(project, tree):
    """One writer, one authority: the key this feature names is the key the
    evening will look for in the file it writes."""
    from agent_kit.knowledge.debt import debt_key

    with_a_ledger(project, "the retry loop swallows the reason")
    said = json.loads(record(project, {"review": WORTH_FIXING}, tree=tree).raw)

    assert said["debt"][0]["key"] == debt_key("the retry loop swallows the reason (money.py:90)")


# --- S8g: the manual actions a night names and cannot do --------------------
#
# The names, and not the file: the ledger's division exactly. `record` derives
# the key against the owner's own checkout, the evening lays the line. What is
# new here is that this half does not depend on the knowledge at all — the file
# lives in `.agent-kit/v3/`, so a project that keeps no knowledge still hands
# its owner the key it needs placing.


def a_design_that_needs_a_person(**row):
    return {**DESIGN, "assumptions": [], "manual": [{"what": "положить STRIPE_KEY", **row}]}


def test_a_manual_action_is_named_with_the_key_its_line_will_carry(project):
    from agent_kit.manual import manual_key

    said = json.loads(record(project, {"design": a_design_that_needs_a_person(proof="sh ops/key.sh")}).raw)

    assert said["manual"] == [
        {"key": manual_key("положить STRIPE_KEY"), "what": "положить STRIPE_KEY",
         "proof": "sh ops/key.sh", "by_hand": ""}
    ]


def test_the_action_is_named_and_never_written_by_the_run(project):
    record(project, {"design": a_design_that_needs_a_person(proof="sh ops/key.sh")})

    assert not (project / ".agent-kit/v3/manual.md").exists()


def test_a_project_that_keeps_no_knowledge_still_names_what_a_person_must_do(without_knowledge):
    """The early return that answers *nothing is owed* stands after this, not before
    it: a manual action does not live in the knowledge, and the project the kit knows
    least about is the one whose secret nobody would otherwise be told to place."""
    said = json.loads(
        record(without_knowledge, {"design": a_design_that_needs_a_person(proof="sh ops/key.sh")}).raw
    )

    assert [one["what"] for one in said["manual"]] == ["положить STRIPE_KEY"]


def test_the_key_is_derived_against_the_owners_checkout_and_not_this_runs_tree(project, tree):
    """The same divergence S8f paid for. Nobody commits the file, so a line laid last
    night stands only in the owner's checkout — and a key derived against the copy
    frozen in this run's tree would collide with it."""
    from agent_kit.manual import Manual, manual_key

    standing = Manual(project)
    standing.write("положить STRIPE_KEY", proof="sh ops/old.sh")

    said = json.loads(
        record(project, {"design": a_design_that_needs_a_person(proof="sh ops/key.sh")}, tree=tree).raw
    )

    assert said["manual"][0]["key"] == manual_key("положить STRIPE_KEY")
    assert [one.key for one in standing.actions()] == [said["manual"][0]["key"]]


def test_two_actions_worded_alike_are_two_lines(project):
    design = {**DESIGN, "assumptions": [], "manual": [
        {"what": "положить ключ", "proof": "sh a.sh"},
        {"what": "положить ключ", "proof": "sh b.sh"},
    ]}

    said = json.loads(record(project, {"design": design}).raw)

    keys = [one["key"] for one in said["manual"]]
    assert len(set(keys)) == 2


def test_an_action_that_could_not_be_written_back_stops_the_step_by_name(project):
    design = a_design_that_needs_a_person(proof="sh -c 'echo `date`'")

    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": design})

    assert refused.value.code.startswith("action-that-cannot-be-written")


def test_an_action_with_no_answer_stops_the_step_by_name(project):
    with pytest.raises(ExecutorFailed) as refused:
        record(project, {"design": a_design_that_needs_a_person()})

    assert refused.value.code.startswith("action-unproved")


def test_a_blocking_finding_stops_the_run_before_a_person_is_given_a_chore(project):
    with pytest.raises(ExecutorFailed):
        record(project, {"design": a_design_that_needs_a_person(proof="sh a.sh"), "review": BLOCKED})
