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


def test_a_kit_that_does_not_know_asking_refuses_the_file(store, tmp_path):
    """An older kit meeting `asking` must say so rather than guess what it means."""
    store.create("add-vat", steps=["design"])
    path = tmp_path / ".agent-kit/v3/runs/add-vat/run.json"
    data = json.loads(path.read_text())
    data["schema"] = SCHEMA_VERSION + 1
    path.write_text(json.dumps(data))

    with pytest.raises(StateError) as refused:
        store.load("add-vat")

    assert refused.value.code == "schema-too-new"
