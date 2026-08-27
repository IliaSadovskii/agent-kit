"""S1 — the state. A run is data; it advances only through the program."""

import json

import pytest

from agent_kit import __version__
from agent_kit.errors import StateError
from agent_kit.state import DEFAULT_STEPS, SCHEMA_VERSION, RunStatus, RunStore, StepStatus


@pytest.fixture
def store(tmp_path):
    return RunStore(tmp_path)


def test_a_new_run_starts_pending_on_every_step(store):
    run = store.create("add-login")

    assert run.slug == "add-login"
    assert run.status is RunStatus.CREATED
    assert run.branch == "kit/add-login"
    assert [step.name for step in run.steps] == list(DEFAULT_STEPS)
    assert all(step.status is StepStatus.PENDING for step in run.steps)


def test_it_writes_where_the_second_version_does_not_look(store, tmp_path):
    store.create("add-login")

    assert (tmp_path / ".agent-kit/v3/runs/add-login/run.json").is_file()
    assert not (tmp_path / ".agent-kit/runs").exists()


def test_the_kit_does_not_dirty_the_tree_it_works_in(store, tmp_path):
    """Run state is not repository content, and the project should not have to say so."""
    store.create("add-login")

    ignore = tmp_path / ".agent-kit/v3/runs/.gitignore"
    assert ignore.read_text().strip().splitlines()[-1] == "*"


def test_the_file_carries_the_schema_and_the_kit_that_wrote_it(store, tmp_path):
    store.create("add-login")

    data = json.loads((tmp_path / ".agent-kit/v3/runs/add-login/run.json").read_text())

    assert data["schema"] == SCHEMA_VERSION
    assert data["kit"] == __version__


def test_a_run_is_read_back_exactly(store):
    created = store.create("add-login", steps=["design", "build"], project="beeplish")

    assert store.load("add-login").to_dict() == created.to_dict()


def test_two_runs_of_one_slug_are_refused(store):
    store.create("add-login")

    with pytest.raises(StateError) as caught:
        store.create("add-login")

    assert caught.value.code == "run-exists"


def test_a_slug_that_is_not_a_directory_name_is_refused(store):
    with pytest.raises(StateError) as caught:
        store.create("../escape")

    assert caught.value.code == "bad-slug"


def test_list_is_sorted_and_names_only_real_runs(store, tmp_path):
    store.create("fix-clock")
    store.create("add-login")
    (tmp_path / ".agent-kit/v3/runs/leftover").mkdir()

    assert store.list() == ["add-login", "fix-clock"]


def test_an_unknown_run_is_named_not_guessed(store):
    with pytest.raises(StateError) as caught:
        store.load("nonesuch")

    assert caught.value.code == "unknown-run"


# --- advancing -------------------------------------------------------------


def test_starting_advances_the_run_and_the_step(store):
    store.create("add-login")

    run = store.start_step("add-login")

    assert run.status is RunStatus.RUNNING
    assert run.steps[0].status is StepStatus.RUNNING
    assert run.steps[0].attempts == 1
    assert run.steps[0].started_at is not None
    assert store.load("add-login").current_step == 0


def test_a_second_start_while_one_runs_is_refused(store):
    store.create("add-login")
    store.start_step("add-login")

    with pytest.raises(StateError) as caught:
        store.start_step("add-login")

    assert caught.value.code == "step-already-running"


def test_passing_moves_to_the_next_step(store):
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")

    run = store.pass_step("add-login")

    assert run.steps[0].status is StepStatus.PASSED
    assert run.steps[0].ended_at is not None
    assert run.status is RunStatus.RUNNING
    assert run.current_step is None


def test_passing_the_last_step_finishes_the_run(store):
    store.create("add-login", steps=["design"])
    store.start_step("add-login")

    run = store.pass_step("add-login")

    assert run.status is RunStatus.DONE
    assert run.finished_at is not None


def test_a_finished_run_does_not_start_again(store):
    store.create("add-login", steps=["design"])
    store.start_step("add-login")
    store.pass_step("add-login")

    with pytest.raises(StateError) as caught:
        store.start_step("add-login")

    assert caught.value.code == "run-finished"


def test_passing_with_no_step_running_is_refused(store):
    store.create("add-login")

    with pytest.raises(StateError) as caught:
        store.pass_step("add-login")

    assert caught.value.code == "no-step-running"


def test_a_failure_keeps_its_reason_and_stops_the_run(store):
    store.create("add-login")
    store.start_step("add-login")

    run = store.fail_step("add-login", "output-missing-field: seams")

    assert run.steps[0].status is StepStatus.FAILED
    assert run.steps[0].reason == "output-missing-field: seams"
    assert run.status is RunStatus.FAILED
    assert run.finished


def test_a_failed_run_does_not_quietly_resume(store):
    """The plan: the run stops and says why. A resumption that erases the reason is the defect."""
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")
    store.fail_step("add-login", "output-missing-field: seams")

    with pytest.raises(StateError) as caught:
        store.start_step("add-login")

    assert caught.value.code == "run-finished"
    assert store.load("add-login").reason == "output-missing-field: seams"


def test_a_run_can_fail_after_its_step_was_refused(store):
    """The driver's policy is exhausted: no step is running, and the run still stops."""
    store.create("add-login")
    store.start_step("add-login")
    store.refuse_step("add-login", "probe on fake: output-not-json")

    run = store.fail_run("add-login", "probe was refused 4 times, last on spare")

    assert run.status is RunStatus.FAILED
    assert run.steps[0].status is StepStatus.FAILED
    assert "4 times" in run.reason


def test_a_failure_without_a_reason_is_refused(store):
    store.create("add-login")
    store.start_step("add-login")

    with pytest.raises(StateError) as caught:
        store.fail_step("add-login", "  ")

    assert caught.value.code == "reason-required"


def test_a_refused_step_is_retried_and_the_attempts_are_counted(store):
    store.create("add-login")
    store.start_step("add-login")
    store.refuse_step("add-login", "output-missing-field: seams")

    run = store.start_step("add-login")

    assert run.steps[0].status is StepStatus.RUNNING
    assert run.steps[0].attempts == 2
    assert run.status is RunStatus.RUNNING


def test_a_failure_with_no_step_running_does_not_rewrite_the_last_one(store):
    """A step that demonstrably passed, with its output on disk, is not the failure."""
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")
    store.pass_step("add-login")

    with pytest.raises(StateError) as caught:
        store.fail_step("add-login", "gave up")

    assert caught.value.code == "no-step-running"
    assert store.load("add-login").steps[0].status is StepStatus.PASSED


def test_a_run_that_fails_after_a_refusal_blames_the_step_it_reached(store):
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")
    store.pass_step("add-login")
    store.start_step("add-login")
    store.refuse_step("add-login", "output-not-json")

    run = store.fail_run("add-login", "build was refused 3 times")

    assert run.steps[0].status is StepStatus.PASSED
    assert run.steps[1].status is StepStatus.FAILED


def test_a_refusal_leaves_the_run_running_and_keeps_its_reason(store):
    store.create("add-login")
    store.start_step("add-login")

    run = store.refuse_step("add-login", "output-not-json")

    assert run.status is RunStatus.RUNNING
    assert run.steps[0].status is StepStatus.PENDING
    assert run.steps[0].reason == "output-not-json"
    assert not run.finished


def test_a_run_can_be_stopped_and_says_why(store):
    store.create("add-login")
    store.start_step("add-login")

    run = store.stop("add-login", "asked by the owner")

    assert run.status is RunStatus.STOPPED
    assert run.reason == "asked by the owner"
    assert run.steps[0].status is StepStatus.PENDING


# --- a stopped run, and the morning after ----------------------------------


def test_a_stopped_run_goes_on_from_the_step_it_stopped_on(store):
    """`stopped` is where an ordinary night ends, and a person puts it right."""
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")
    store.pass_step("add-login")
    store.start_step("add-login")
    store.stop("add-login", "asked by the owner")

    run = store.reopen("add-login")

    assert run.status is RunStatus.RUNNING
    assert run.finished_at is None
    assert not run.finished
    assert run.steps[0].status is StepStatus.PASSED
    assert run.steps[1].status is StepStatus.PENDING
    assert store.start_step("add-login").current.name == "build"


def test_a_gate_that_closed_is_the_step_the_run_goes_on_from(store):
    """`halt` leaves the gating step `passed` — it did its work — and stops the run.

    What the owner then changes by hand is exactly what that step recorded, so
    the run has to measure it again. Going on from the step after it would
    carry the red suite forward and stop on it a second time.
    """
    store.create("add-login", steps=["design", "verify", "deliver"])
    store.start_step("add-login")
    store.pass_step("add-login")
    store.start_step("add-login")
    store.pass_step("add-login")
    store.halt("add-login", "gate-closed: verify passed and recorded passed as false")

    run = store.reopen("add-login")

    assert run.steps[0].status is StepStatus.PASSED
    assert run.steps[1].status is StepStatus.PENDING
    assert run.next_pending() == 1


def test_a_stop_read_between_steps_leaves_what_passed_alone(store):
    """A person's stop is read at a step boundary, so the step before it passed.

    That step is not what stopped the run and nobody changed what it recorded:
    sending it back would buy a second session and nothing else. Only a gate
    that closed makes the step it is on worth measuring again.
    """
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")
    store.pass_step("add-login")
    store.stop("add-login", "stopped-by-request: enough for tonight")

    run = store.reopen("add-login")

    assert run.steps[0].status is StepStatus.PASSED
    assert run.steps[0].attempts == 1
    assert run.next_pending() == 1


def test_the_step_a_reopened_run_stands_on_says_why_it_had_stopped(store):
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")
    store.stop("add-login", "stopped-by-request: the owner said so")

    run = store.reopen("add-login")

    assert "stopped-by-request: the owner said so" in run.steps[0].reason


def test_a_run_stopped_before_anything_started_reopens_at_its_first_step(store):
    store.create("add-login", steps=["design", "build"])
    store.stop("add-login", "asked by the owner")

    run = store.reopen("add-login")

    assert run.next_pending() == 0
    assert all(step.status is StepStatus.PENDING for step in run.steps)


def test_a_failed_run_stays_final(store):
    """The one status this refuses, and it was argued for: `failed` does not resume."""
    store.create("add-login", steps=["design", "build"])
    store.start_step("add-login")
    store.fail_step("add-login", "output-missing-field: seams")

    with pytest.raises(StateError) as caught:
        store.reopen("add-login")

    assert caught.value.code == "run-not-stopped"
    assert store.load("add-login").status is RunStatus.FAILED


@pytest.mark.parametrize("bring_it_to", ["created", "running", "done"])
def test_only_a_stopped_run_is_reopened(store, bring_it_to):
    store.create("add-login", steps=["design"])
    if bring_it_to != "created":
        store.start_step("add-login")
    if bring_it_to == "done":
        store.pass_step("add-login")

    with pytest.raises(StateError) as caught:
        store.reopen("add-login")

    assert caught.value.code == "run-not-stopped"


# --- what may not be written ----------------------------------------------


def test_the_state_is_written_whole_never_in_place(store, tmp_path, monkeypatch):
    """Open question 2: write beside, rename over — a killed writer leaves the old file."""
    store.create("add-login")
    path = tmp_path / ".agent-kit/v3/runs/add-login/run.json"
    before = path.read_text()

    import agent_kit.state.store as store_module

    monkeypatch.setattr(store_module.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        store.start_step("add-login")

    assert path.read_text() == before
    assert list(path.parent.glob("*.tmp*")) == []


def test_a_file_from_a_newer_kit_is_refused_by_its_kit_version(store, tmp_path):
    """Open question 3: the kit that wrote a file is a field with a reader."""
    store.create("add-login")
    path = tmp_path / ".agent-kit/v3/runs/add-login/run.json"
    data = json.loads(path.read_text())
    data["kit"] = "9.9.0"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(StateError) as caught:
        store.load("add-login")

    assert caught.value.code == "kit-too-new"
    assert "9.9.0" in caught.value.detail


def test_a_file_from_an_older_kit_of_the_same_schema_is_read(store, tmp_path):
    store.create("add-login")
    path = tmp_path / ".agent-kit/v3/runs/add-login/run.json"
    data = json.loads(path.read_text())
    data["kit"] = "1.0.0"
    path.write_text(json.dumps(data), encoding="utf-8")

    assert store.load("add-login").kit == "1.0.0"


def test_a_file_from_a_newer_schema_is_refused_not_guessed(store, tmp_path):
    store.create("add-login")
    path = tmp_path / ".agent-kit/v3/runs/add-login/run.json"
    data = json.loads(path.read_text())
    data["schema"] = SCHEMA_VERSION + 1
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(StateError) as caught:
        store.load("add-login")

    assert caught.value.code == "schema-too-new"


def test_a_file_from_an_older_kit_is_migrated_on_the_way_in(store, tmp_path, monkeypatch):
    """Registering a migration is the whole of it — no second constant to remember."""
    import agent_kit.state.migrations as migrations

    monkeypatch.setitem(migrations.MIGRATIONS, 0, lambda data: {**data, "slug": data.pop("name")})
    store.create("add-login")
    path = tmp_path / ".agent-kit/v3/runs/add-login/run.json"
    data = json.loads(path.read_text())
    data["schema"] = 0
    data["name"] = data.pop("slug")
    path.write_text(json.dumps(data), encoding="utf-8")

    run = store.load("add-login")

    assert run.slug == "add-login"
    assert run.schema == SCHEMA_VERSION


def test_how_old_a_file_may_be_follows_from_the_migrations_themselves(monkeypatch):
    import agent_kit.state.migrations as migrations

    assert migrations.oldest_schema() == min(migrations.MIGRATIONS)

    monkeypatch.setitem(migrations.MIGRATIONS, 0, lambda data: data)

    assert migrations.oldest_schema() == 0


@pytest.mark.parametrize(
    "written, readable",
    [("3.0.0.dev0", True), ("3.0.0", True), ("v3.0.0", True), ("2.28.0", True), ("v9.0.0", False)],
)
def test_the_kit_version_is_read_the_way_people_write_it(store, tmp_path, written, readable):
    store.create("add-login")
    path = tmp_path / ".agent-kit/v3/runs/add-login/run.json"
    data = json.loads(path.read_text()) | {"kit": written}
    path.write_text(json.dumps(data), encoding="utf-8")

    if readable:
        assert store.load("add-login").kit == written
    else:
        with pytest.raises(StateError) as caught:
            store.load("add-login")
        assert caught.value.code == "kit-too-new"


def test_a_damaged_file_is_refused_with_its_reason(store, tmp_path):
    store.create("add-login")
    (tmp_path / ".agent-kit/v3/runs/add-login/run.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(StateError) as caught:
        store.load("add-login")

    assert caught.value.code == "unreadable-run"


@pytest.mark.parametrize(
    "damage, code",
    [
        ({"status": "flying"}, "bad-field: status"),
        ({"steps": "design"}, "bad-field: steps"),
        ({"slug": ""}, "bad-field: slug"),
        ({"current_step": 9}, "bad-field: current_step"),
    ],
)
def test_an_invalid_state_is_refused_field_by_field(store, tmp_path, damage, code):
    store.create("add-login")
    path = tmp_path / ".agent-kit/v3/runs/add-login/run.json"
    data = json.loads(path.read_text()) | damage
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(StateError) as caught:
        store.load("add-login")

    assert caught.value.code == code


# --- S4: a run says what it is for -----------------------------------------


def test_a_run_carries_the_brief_it_was_created_for(store):
    store.create("add-vat", steps=["probe"], brief="Money should know about VAT")

    assert store.load("add-vat").brief == "Money should know about VAT"


def test_a_brief_that_is_not_text_is_refused(store, tmp_path):
    store.create("add-vat", steps=["probe"])
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    data = json.loads(path.read_text())
    data["brief"] = 7
    path.write_text(json.dumps(data))

    with pytest.raises(StateError) as refused:
        store.load("add-vat")
    assert refused.value.code == "bad-field: brief"


def test_a_run_file_from_schema_1_gains_an_empty_brief(store, tmp_path):
    store.create("add-vat", steps=["probe"])
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    data = json.loads(path.read_text())
    data["schema"] = 1
    data.pop("brief", None)
    path.write_text(json.dumps(data))

    run = store.load("add-vat")

    assert run.brief is None
    assert run.schema == SCHEMA_VERSION


# --- S7a: a step that is waiting for a person ------------------------------


def test_a_running_step_can_be_asking(store):
    store.create("add-vat", steps=["design"])
    store.start_step("add-vat")

    run = store.ask_step("add-vat", "asking the owner about the rate")

    assert run.steps[0].status is StepStatus.ASKING
    assert run.status is RunStatus.RUNNING
    assert run.current_step == 0
    assert run.steps[0].reason == "asking the owner about the rate"


def test_only_a_running_step_asks(store):
    store.create("add-vat", steps=["design"])

    with pytest.raises(StateError) as refused:
        store.ask_step("add-vat", "asking about nothing")

    assert refused.value.code == "no-step-running"


def test_an_answer_sends_the_step_back_to_be_run_again(store):
    """Not a refusal and not a part: the owner answered, so the step is done again."""
    store.create("add-vat", steps=["design"])
    store.start_step("add-vat")
    store.ask_step("add-vat", "asking the owner about the rate")

    run = store.answered("add-vat", "the owner answered: one rate")

    assert run.steps[0].status is StepStatus.PENDING
    assert run.steps[0].attempts == 1
    assert run.steps[0].reason == "the owner answered: one rate"
    assert run.current_step is None


def test_a_step_that_never_asked_cannot_be_answered(store):
    store.create("add-vat", steps=["design"])
    store.start_step("add-vat")

    with pytest.raises(StateError) as refused:
        store.answered("add-vat", "an answer to nothing")

    assert refused.value.code == "no-step-asking"


def test_nobody_answered_and_the_step_passes_from_asking(store):
    """The default was taken. The step did its work and the run goes on."""
    store.create("add-vat", steps=["design"])
    store.start_step("add-vat")
    store.ask_step("add-vat", "asking the owner about the rate")

    run = store.pass_step("add-vat")

    assert run.steps[0].status is StepStatus.PASSED
    assert run.status is RunStatus.DONE


def test_an_asking_step_survives_being_written_and_read_back(store):
    store.create("add-vat", steps=["design"])
    store.start_step("add-vat")
    store.ask_step("add-vat", "asking the owner about the rate")

    run = store.load("add-vat")

    assert run.steps[0].status is StepStatus.ASKING
    assert run.current.name == "design"


def test_current_step_must_point_at_a_step_that_is_doing_something(store, tmp_path):
    store.create("add-vat", steps=["design"])
    store.start_step("add-vat")
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    data = json.loads(path.read_text())
    data["steps"][0]["status"] = "passed"
    path.write_text(json.dumps(data))

    with pytest.raises(StateError) as refused:
        store.load("add-vat")

    assert refused.value.code == "bad-field: current_step"


def test_a_run_file_from_schema_2_is_read(store, tmp_path):
    """Nothing in a schema 2 file changes. What the bump buys is the refusal below."""
    store.create("add-vat", steps=["design"])
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    data = json.loads(path.read_text())
    data["schema"] = 2
    path.write_text(json.dumps(data))

    run = store.load("add-vat")

    assert run.schema == SCHEMA_VERSION


def test_a_kit_that_does_not_know_asking_refuses_the_file(store, tmp_path, monkeypatch):
    """Кит, не знающий `asking`, обязан сказать это, а не гадать.

    Прежняя версия ставила номер схемы на единицу больше и слова `asking` в
    файл не писала вовсе — то есть была дословным дублем соседнего случая и
    была бы зелёной ещё до S7a.
    """
    store.create("add-vat", steps=["design"])
    store.start_step("add-vat")
    store.ask_step("add-vat", "design is asking the owner one thing")
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    assert '"asking"' in path.read_text()

    # Тот самый кит: он знает схему на единицу меньше и статуса ещё не видел.
    monkeypatch.setattr("agent_kit.state.migrations.SCHEMA_VERSION", SCHEMA_VERSION - 1)

    with pytest.raises(StateError) as refused:
        store.load("add-vat")

    assert refused.value.code == "schema-too-new"


# --- S8: what a run learns when it is one of several ------------------------


def test_a_run_on_its_own_names_no_tree_no_base_and_needs_nothing(store):
    """The run S4 to S7a proved, unchanged: it works in the project, off the trunk."""
    run = store.create("add-vat", steps=["design"])

    assert run.tree is None
    assert run.base == ""
    assert run.needs == []


def test_a_run_can_say_what_it_builds_on_and_where(store, tmp_path):
    run = store.create(
        "quote", steps=["design"], base="kit/rates", tree=str(tmp_path / "trees/quote"), needs=["rates"],
    )

    read = store.load("quote")

    assert read.base == "kit/rates"
    assert read.tree == str(tmp_path / "trees/quote")
    assert read.needs == ["rates"]
    assert read.to_dict() == run.to_dict()


def test_what_a_run_needs_must_be_run_names(store):
    with pytest.raises(StateError) as refused:
        store.create("quote", steps=["design"], needs=["Rates!"])

    assert refused.value.code == "bad-slug"


def test_needs_must_be_a_list(store, tmp_path):
    store.create("quote", steps=["design"])
    path = tmp_path / ".agent-kit/v3/runs/quote/run.json"
    data = json.loads(path.read_text())
    data["needs"] = "rates"
    path.write_text(json.dumps(data))

    with pytest.raises(StateError) as refused:
        store.load("quote")

    assert refused.value.code == "bad-field: needs"


def test_a_run_may_not_need_itself(store):
    with pytest.raises(StateError) as refused:
        store.create("quote", steps=["design"], needs=["quote"])

    assert refused.value.code == "bad-field: needs"


def test_a_run_file_from_schema_3_gains_a_tree_it_never_had(store, tmp_path):
    store.create("add-vat", steps=["design"])
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    data = json.loads(path.read_text())
    data["schema"] = 3
    for gone in ("tree", "base", "needs"):
        data.pop(gone, None)
    path.write_text(json.dumps(data))

    run = store.load("add-vat")

    assert run.schema == SCHEMA_VERSION
    assert (run.tree, run.base, run.needs) == (None, "", [])


def test_a_kit_that_does_not_know_a_tree_refuses_the_file(store, tmp_path, monkeypatch):
    """A run built in a worktree must not be read by a kit that would run it in the project.

    Not a duplicate of its neighbour: the file really names a tree, and a kit
    that does not know the field would work in the project itself — which is
    two runs in one working copy, the thing S8 exists to make impossible.
    """
    store.create("quote", steps=["design"], tree=str(tmp_path / "trees/quote"))
    path = tmp_path / ".agent-kit/v3/runs/quote/run.json"
    assert "trees/quote" in path.read_text()

    monkeypatch.setattr("agent_kit.state.migrations.SCHEMA_VERSION", SCHEMA_VERSION - 1)

    with pytest.raises(StateError) as refused:
        store.load("quote")

    assert refused.value.code == "schema-too-new"


# --- the order of the steps is an argument ----------------------------------
#
# A `verify` before `build` runs the project's suite over a tree with no new
# code. It comes back green by construction, and every later reader — the
# review, the pull request, the owner — sees `passed: true`. The order a run
# holds is a claim about what measured what, so it is checked where a run is
# made and not left to whoever typed it.


def test_a_verify_before_the_build_it_would_measure_is_refused(store):
    with pytest.raises(StateError) as refused:
        store.create("add-vat", steps=["design", "verify", "build", "review", "record", "deliver"])

    assert refused.value.code == "steps-out-of-order"
    assert "verify" in refused.value.detail and "build" in refused.value.detail


def test_a_step_asked_for_twice_is_refused(store):
    with pytest.raises(StateError) as refused:
        store.create("add-vat", steps=["verify", "verify"])

    assert refused.value.code == "step-twice"
    assert "verify" in refused.value.detail


def test_a_run_refused_at_its_creation_leaves_nothing_behind(store):
    with pytest.raises(StateError):
        store.create("add-vat", steps=["deliver", "design"])

    assert store.exists("add-vat") is False


def test_the_steps_the_kit_runs_by_itself_are_in_an_order_that_means_something(store):
    run = store.create("add-vat")

    assert [step.name for step in run.steps] == list(DEFAULT_STEPS)


def test_some_of_the_steps_in_their_own_order_is_a_run(store):
    """A run of a few steps is ordinary — a design and a build, and no more."""
    run = store.create("add-vat", steps=["design", "build"])

    assert [step.name for step in run.steps] == ["design", "build"]


def test_a_step_outside_the_sequence_is_not_placed_in_it(store):
    """`probe` measures a provider rather than building a feature.

    It is a step the kit ships and no part of the method's order: two of them
    is two sessions asked what they can see, which is what `provider check`
    and the bench's slot cases do.
    """
    run = store.create("add-vat", steps=["probe", "probe"])

    assert [step.name for step in run.steps] == ["probe", "probe"]


# --- S8b: a run carries the frame of the work it belongs to -----------------


def test_a_run_started_by_hand_carries_no_frame(store):
    """A frame is what several features build alike, and one run alone has none."""
    run = store.create("add-vat")

    assert run.frame == []


def test_a_run_carries_the_frame_it_was_created_with(store):
    run = store.create("add-vat", frame=["the rate lives in one place"])

    assert store.load("add-vat").frame == ["the rate lives in one place"]


def test_a_frame_must_be_lines_of_text(store, tmp_path):
    store.create("add-vat")
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    held = json.loads(path.read_text())
    held["frame"] = [{"what": "not a line"}]
    path.write_text(json.dumps(held))

    with pytest.raises(StateError) as refused:
        store.load("add-vat")
    assert refused.value.code == "bad-field: frame"


def test_a_run_written_before_frames_reads_as_having_none(store, tmp_path):
    """Schema 4 knew nothing of a frame, and none of its runs had one."""
    store.create("add-vat")
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    held = json.loads(path.read_text())
    held["schema"] = 4
    held.pop("frame")
    path.write_text(json.dumps(held))

    run = store.load("add-vat")
    assert run.frame == []
    assert run.schema == SCHEMA_VERSION


def test_the_schema_is_five(store):
    assert SCHEMA_VERSION == 5
