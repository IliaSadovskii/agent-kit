"""S8 — the batch driver: what may start now, and what a feature takes with it.

It decides one thing and nothing else: which of the batch's runs may start.
Everything a run does afterwards is the driver S4 to S7a already proved, and
this suite is about the layer above it.
"""

import subprocess

import pytest

from agent_kit.batch import BatchStore, FeatureStatus, read_declaration
from agent_kit.batch.driver import BatchDriver
from agent_kit.errors import StateError
from agent_kit.machine import Ceilings, Ledger
from agent_kit.state import RunStatus, RunStore
from agent_kit.steps import builtin_registry

THREE = """
name = "vat"

[features.rates]
brief = "A table of VAT rates"

[features.quote]
brief = "Money quotes a price with VAT"
needs = ["rates"]
"""

APART = """
name = "vat"

[features.one]
brief = "The first, which waits for nothing"

[features.two]
brief = "The second, which waits for nothing either"
"""


def git(root, *argv):
    return subprocess.run(["git", *argv], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "kit@example.com")
    git(root, "config", "user.name", "kit")
    declared = root / ".agent-kit/v3/project.toml"
    declared.parent.mkdir(parents=True, exist_ok=True)
    declared.write_text('[project]\ndefault_branch = "main"\n\n[commands]\ntest = "true"\n', encoding="utf-8")
    (root / "money.py").write_text("amount = 1000\n")
    git(root, "add", "-A")
    git(root, "commit", "-m", "first")
    return root


class Spoke:
    """The owner's channel, as far as this suite is concerned."""

    def __init__(self):
        self.said = []

    def news(self, text):
        self.said.append(text)


class Scripted:
    """A child that ends the way the case says, without a process anywhere.

    The real spawning is what the bench measures — it runs the kit as a
    command. What is proved here is the layer above: who is started, when, and
    what their ending does to the rest of the batch.
    """

    def __init__(self, runs, endings, ledger=None, project=None, batch="vat"):
        self.runs = runs
        self.endings = endings
        self.ledger = ledger
        self.project = project
        self.batch = batch
        self.started = []
        self.alive = set()
        self.held = {}
        #: The most children alive at one moment. What *at once* means, measured
        #: rather than inferred from two timestamps a second apart.
        self.most_alive = 0

    def __call__(self, run, argv):
        self.started.append((run.slug, list(argv)))
        self.alive.add(run.slug)
        self.most_alive = max(self.most_alive, len(self.alive))
        # A real driver holds its run while it drives it, and a stop addressed
        # to a run nobody holds is swept — so a child that does not hold one
        # would make a stop test measure the sweep instead of the stop.
        self.held[run.slug] = self.ledger.hold_run(str(self.project), run.slug)
        return _Child(self, run.slug)


class _Child:
    """Alive for a few polls, then it ends the way the case says."""

    def __init__(self, spawn, slug):
        self.spawn = spawn
        self.slug = slug
        self.polls = 0

    def poll(self):
        self.polls += 1
        how = self.spawn.endings.get(self.slug, "done")
        if how == "stops-when-asked":
            if self.spawn.ledger.stop_pending(str(self.spawn.project), self.slug) is None:
                return None
            self.spawn.runs.stop(self.slug, "stopped-by-request: the batch was asked to stop")
            return self._gone(130)
        if how == "asks-the-batch-to-stop":
            if self.polls == 1:
                # A person, while the batch is running: the one moment a stop
                # has to be read, and the only one worth measuring.
                self.spawn.ledger.ask_stop(
                    str(self.spawn.project), self.spawn.batch, reason="enough for tonight"
                )
                return None
            if self.spawn.ledger.stop_pending(str(self.spawn.project), self.slug) is None:
                return None
            self.spawn.runs.stop(self.slug, "stopped-by-request: the batch was asked to stop")
            return self._gone(130)
        if self.polls < 2:
            return None
        if how == "done":
            _land(self.spawn.runs, self.slug)
            return self._gone(0)
        if how in UNTOUCHED:
            # A child that came back leaving its run exactly where it was. All
            # that is left of what happened is the code it came back with, and
            # the kit gives each of these one meaning.
            return self._gone(UNTOUCHED[how])
        self.spawn.runs.fail_run(self.slug, f"{self.slug}: build was refused three times")
        return self._gone(3)

    def _gone(self, code):
        self.spawn.alive.discard(self.slug)
        self.spawn.ledger.release(self.spawn.held.pop(self.slug, None))
        return code


#: Endings that touch no state at all, and the code the child comes back with.
UNTOUCHED = {"the-machine-was-full": 4, "killed": -9, "stopped-without-a-word": 130}


def _land(runs, slug):
    run = runs.load(slug)
    while not run.finished:
        runs.start_step(slug, provider="fake")
        run = runs.pass_step(slug)


def driver(repo, text=THREE, endings=None, machine=4, spoke=None, merges=None):
    store = BatchStore(repo)
    store.create(read_declaration(_declared(repo, text)))
    return another_driver(repo, store, endings=endings, machine=machine, spoke=spoke, merges=merges)


def another_driver(repo, store, endings=None, machine=4, spoke=None, merges=None):
    """The next night: a driver over a batch somebody else created."""
    runs = RunStore(repo)
    ledger = Ledger(repo / "daemon.sqlite")
    spawn = Scripted(runs, endings or {}, ledger=ledger, project=repo)
    return (
        BatchDriver(
            project=repo,
            store=store,
            runs=runs,
            registry=builtin_registry(),
            ledger=ledger,
            ceilings=Ceilings(max_sessions=machine),
            owner=spoke or Spoke(),
            spawn=spawn,
            check_merges=merges or (lambda *args, **rest: []),
            pause=lambda _: None,
        ),
        store,
        runs,
        spawn,
        ledger,
    )


def _declared(repo, text):
    path = repo / "batch.toml"
    path.write_text(text, encoding="utf-8")
    return path


# --- what may start now -----------------------------------------------------


def test_a_feature_that_needs_another_is_not_started_before_it_lands(repo):
    drive, store, runs, spawn, _ = driver(repo, THREE)

    drive.go("vat")

    assert [slug for slug, _ in spawn.started] == ["rates", "quote"]
    assert spawn.most_alive == 1  # never both, whatever room the machine had
    assert store.load("vat").landed_everything


def test_features_that_need_nothing_are_built_at_once(repo):
    """*At once* is two children alive together, not two that both finished."""
    drive, store, runs, spawn, _ = driver(repo, APART)

    drive.go("vat")

    assert sorted(slug for slug, _ in spawn.started) == ["one", "two"]
    assert spawn.most_alive == 2


def test_no_more_children_than_the_machine_could_ever_have_sessions(repo):
    """A child that cannot possibly get a slot is a process idling in a poll loop."""
    drive, store, runs, spawn, _ = driver(repo, APART, machine=1)

    drive.go("vat")

    assert [slug for slug, _ in spawn.started] == ["one", "two"]
    assert spawn.most_alive == 1


def test_a_feature_is_built_on_what_it_needs_and_in_its_own_tree(repo):
    drive, store, runs, spawn, _ = driver(repo)

    drive.go("vat")

    rates = runs.load("rates")
    quote = runs.load("quote")
    assert rates.base == "main"
    assert quote.base == "kit/rates"
    assert quote.needs == ["rates"]
    assert quote.tree.endswith("/.agent-kit/v3/trees/quote")
    assert rates.tree != quote.tree


def test_a_child_is_told_that_somebody_else_speaks_for_it(repo):
    drive, _, _, spawn, _ = driver(repo, APART)

    drive.go("vat")

    assert all("--silent" in argv for _, argv in spawn.started)


# --- what an ending does to the rest ---------------------------------------


def test_a_feature_that_did_not_land_stops_what_needed_it_without_a_session(repo):
    drive, store, runs, spawn, _ = driver(repo, endings={"rates": "failed"})

    outcome = drive.go("vat")

    assert [slug for slug, _ in spawn.started] == ["rates"]
    assert outcome.batch.feature("quote").status is FeatureStatus.STOPPED
    assert outcome.batch.feature("quote").reason == "needed-rates"
    assert not runs.exists("quote")


def test_what_did_not_need_it_still_lands(repo):
    drive, store, runs, spawn, _ = driver(repo, APART, endings={"one": "failed"})

    outcome = drive.go("vat")

    assert outcome.batch.feature("two").status is FeatureStatus.DONE
    assert outcome.batch.feature("one").status is FeatureStatus.FAILED


def test_the_run_s_own_ending_is_what_the_batch_records(repo):
    drive, store, runs, _, _ = driver(repo, APART)

    drive.go("vat")

    assert runs.load("one").status is RunStatus.DONE
    assert store.load("vat").feature("one").status is FeatureStatus.DONE


# --- what the child came back with ------------------------------------------


def test_a_feature_the_machine_had_no_room_for_is_left_to_be_built(repo):
    """Code 4 is the machine saying no. Nothing was attempted, so nothing failed.

    The rule a level down, at the batch's own level: a run that could not have
    a session is left exactly as it was, and this is what that means for the
    night above it — the feature is still to do, and `batch go` picks it up.
    """
    drive, store, runs, spawn, _ = driver(repo, endings={"rates": "the-machine-was-full"})

    outcome = drive.go("vat")

    assert [slug for slug, _ in spawn.started] == ["rates"]  # once, not in a loop
    assert outcome.batch.feature("rates").status is FeatureStatus.PENDING
    assert outcome.batch.feature("rates").reason  # and it says what stopped it
    assert outcome.batch.feature("quote").status is FeatureStatus.PENDING
    assert not outcome.batch.finished
    assert runs.load("rates").status is RunStatus.CREATED


def test_the_night_carries_on_with_what_the_machine_had_no_room_for(repo):
    """Resumable is measured by resuming it, not by reading a status."""
    drive, store, runs, spawn, _ = driver(repo, APART, endings={"one": "the-machine-was-full"})
    drive.go("vat")

    again, _, _, second, _ = another_driver(repo, store)
    outcome = again.go("vat")

    assert [slug for slug, _ in second.started] == ["one"]
    assert outcome.batch.landed_everything


def test_a_person_stopping_a_child_is_not_a_feature_that_failed(repo):
    """Code 130 says who ended it, and it was not the method."""
    drive, store, runs, spawn, _ = driver(repo, endings={"rates": "stopped-without-a-word"})

    outcome = drive.go("vat")

    assert outcome.batch.feature("rates").status is FeatureStatus.STOPPED
    assert outcome.batch.feature("rates").reason


def test_a_child_that_was_killed_says_so_rather_than_failing_in_silence(repo):
    drive, store, runs, spawn, _ = driver(repo, endings={"rates": "killed"})

    outcome = drive.go("vat")

    rates = outcome.batch.feature("rates")
    assert rates.status is FeatureStatus.FAILED
    assert "9" in (rates.reason or "") and "created" in (rates.reason or "")


def test_a_feature_that_could_not_be_started_does_not_take_the_batch_with_it(repo):
    """Something sitting where the second feature's tree goes: the audit's own case.

    The exception left `go` altogether, and the child already spawned went on
    building — finishing its feature and opening its pull request — against a
    record that had it running for good.
    """
    (repo / ".agent-kit/v3/trees/two").mkdir(parents=True)
    drive, store, runs, spawn, _ = driver(repo, APART)

    outcome = drive.go("vat")

    assert outcome.batch.feature("one").status is FeatureStatus.DONE
    assert outcome.batch.feature("two").status is FeatureStatus.FAILED
    assert "tree-in-the-way" in (outcome.batch.feature("two").reason or "")


def test_a_child_still_running_is_seen_off_rather_than_left_building(repo):
    """The way out through an exception, which is where the orphans came from."""
    drive, store, runs, spawn, ledger = driver(
        repo, APART, endings={"one": "stops-when-asked", "two": "stops-when-asked"}
    )
    broke = []

    def falls_over(_):
        if not broke:
            broke.append(1)
            raise RuntimeError("the batch driver broke mid-flight")

    drive.pause = falls_over

    with pytest.raises(RuntimeError):
        drive.go("vat")

    kept = store.load("vat")
    assert spawn.alive == set()  # nobody is left building
    assert [kept.feature(slug).status for slug, _ in spawn.started] == [
        FeatureStatus.STOPPED, FeatureStatus.STOPPED,
    ]


# --- a driver that never came back ------------------------------------------


def test_a_feature_left_running_by_a_driver_that_never_came_back_is_taken_up_again(repo):
    """The same reading as a step left running one level down: nobody is on it."""
    drive, store, runs, spawn, _ = driver(repo, APART)
    left = store.load("vat")
    left.starting("one", tree=str(repo / ".agent-kit/v3/trees/one"))
    store.save(left)

    outcome = drive.go("vat")

    assert sorted(slug for slug, _ in spawn.started) == ["one", "two"]
    assert outcome.batch.landed_everything


def test_a_feature_whose_orphan_finished_it_is_read_back_rather_than_built_again(repo):
    """A child outlives the driver that spawned it, and it may have landed."""
    from agent_kit.driver import create_run

    drive, store, runs, spawn, _ = driver(repo, APART)
    left = store.load("vat")
    left.starting("one", tree=str(repo / ".agent-kit/v3/trees/one"))
    store.save(left)
    create_run(runs, builtin_registry(), "one", project=str(repo), brief="The first", base="main")
    _land(runs, "one")

    outcome = drive.go("vat")

    assert [slug for slug, _ in spawn.started] == ["two"]
    assert outcome.batch.feature("one").status is FeatureStatus.DONE


def test_a_feature_somebody_is_still_driving_is_left_alone(repo):
    drive, store, runs, spawn, ledger = driver(repo, APART)
    left = store.load("vat")
    left.starting("one", tree=str(repo / ".agent-kit/v3/trees/one"))
    store.save(left)
    ledger.hold_run(str(repo), "one", pid=1)

    outcome = drive.go("vat")

    assert [slug for slug, _ in spawn.started] == ["two"]
    assert outcome.batch.feature("one").status is FeatureStatus.RUNNING


# --- a person, mid-batch ----------------------------------------------------


def test_a_skip_before_it_starts_takes_what_needed_it_and_starts_nothing(repo):
    drive, store, runs, spawn, ledger = driver(repo)
    ledger.hold_batch(str(repo), "vat")
    ledger.ask_skip(str(repo), "vat", "rates", reason="the rates table is not settled")

    outcome = drive.go("vat")

    assert spawn.started == []
    assert outcome.batch.feature("rates").status is FeatureStatus.SKIPPED
    assert outcome.batch.feature("quote").status is FeatureStatus.SKIPPED
    assert outcome.batch.feature("quote").reason == "needed-rates"


def test_a_stop_stops_the_children_and_leaves_the_rest_pending(repo):
    """Asked for while it runs, which is the only moment a stop means anything."""
    drive, store, runs, spawn, ledger = driver(
        repo, endings={"rates": "asks-the-batch-to-stop"},
    )

    outcome = drive.go("vat")

    assert outcome.interrupted
    assert [slug for slug, _ in spawn.started] == ["rates"]
    assert runs.load("rates").status is RunStatus.STOPPED
    assert outcome.batch.feature("rates").status is FeatureStatus.STOPPED
    assert outcome.batch.feature("quote").status is FeatureStatus.PENDING


def test_a_batch_that_is_over_does_not_start_again(repo):
    drive, store, runs, _, _ = driver(repo, APART)
    drive.go("vat")

    with pytest.raises(StateError) as refused:
        drive.go("vat")

    assert refused.value.code == "batch-finished"


def test_two_drivers_on_one_batch_are_refused_by_name(repo):
    drive, store, runs, _, ledger = driver(repo, APART)
    ledger.hold_batch(str(repo), "vat", pid=1)

    with pytest.raises(StateError) as refused:
        drive.go("vat")

    assert refused.value.code == "batch-held-elsewhere"


# --- the owner hears once ---------------------------------------------------


def test_the_owner_is_woken_once_for_the_whole_batch(repo):
    spoke = Spoke()
    drive, store, runs, _, _ = driver(repo, APART, spoke=spoke)

    drive.go("vat")

    assert len(spoke.said) == 1
    assert "one" in spoke.said[0] and "two" in spoke.said[0]


def test_what_will_not_merge_is_named_where_the_owner_reads_it(repo):
    from agent_kit.batch.merge import Conflict

    spoke = Spoke()
    drive, store, runs, _, _ = driver(
        repo, APART, spoke=spoke,
        merges=lambda *args, **rest: [Conflict(slug="two", branch="kit/two", files=["money.py"])],
    )

    outcome = drive.go("vat")

    assert [conflict.slug for conflict in outcome.conflicts] == ["two"]
    assert "money.py" in spoke.said[0]


# --- the trees ---------------------------------------------------------------


def test_a_tree_is_taken_away_when_its_feature_lands_and_kept_when_it_did_not(repo):
    from agent_kit.driver.tree import tree_for

    drive, store, runs, _, _ = driver(repo, APART, endings={"one": "failed"})

    drive.go("vat")

    assert tree_for(repo, "one").is_dir()
    assert not tree_for(repo, "two").exists()


# --- S8b: the frame, handed down and closed when the night is over ----------

FRAMED = """
name = "vat"

[[frames]]
what = "the rate lives in one place"
id = "fr4me1"

[features.one]
brief = "The first"

[features.two]
brief = "The second"
"""


def knowledge_holding_a_frame(repo, id="fr4me1", run="vat"):
    where = repo / "docs/knowledge"
    where.mkdir(parents=True, exist_ok=True)
    (where / "product.md").write_text(
        "# Продукт\n"
        "\n"
        "### Налог\n"
        "`key: tax`\n"
        "\n"
        "Как считается налог.\n"
        "\n"
        f"> **[{'frame'} 2026-08-27 · {run} · id: {id}]** the rate lives in one place\n",
        encoding="utf-8",
    )
    return where / "product.md"


def test_every_feature_is_handed_the_frame_of_the_work_it_belongs_to(repo):
    knowledge_holding_a_frame(repo)
    held, store, runs, spawn, _ = driver(repo, text=FRAMED)

    held.go("vat")

    assert [runs.load(slug).frame for slug in ("one", "two")] == [
        ["the rate lives in one place"]
    ] * 2


def test_the_frame_is_closed_by_the_evening_that_wrote_it(repo):
    path = knowledge_holding_a_frame(repo)
    held, store, _, _, _ = driver(repo, text=FRAMED)

    # The trap first: the block really is standing before the night runs.
    assert "id: fr4me1" in path.read_text(encoding="utf-8")

    held.go("vat")

    assert "id: fr4me1" not in path.read_text(encoding="utf-8")
    assert "Как считается налог" in path.read_text(encoding="utf-8")
    assert store.load("vat").frames[0].id == ""


def test_a_night_a_person_stopped_leaves_its_frames_standing(repo):
    """`batch go` again carries on with what is pending, and it is still held to them."""
    path = knowledge_holding_a_frame(repo)
    held, store, _, _, _ = driver(
        repo, text=FRAMED, endings={"one": "asks-the-batch-to-stop", "two": "stops-when-asked"},
        machine=1,
    )

    held.go("vat")

    assert "id: fr4me1" in path.read_text(encoding="utf-8")


def test_a_frame_another_evening_wrote_is_left_where_it_stands(repo):
    path = knowledge_holding_a_frame(repo, run="last-week")
    held, store, _, _, _ = driver(repo, text=FRAMED)

    held.go("vat")

    assert "id: fr4me1" in path.read_text(encoding="utf-8")
    assert store.load("vat").frames[0].id == "fr4me1"


def test_a_block_that_is_gone_does_not_fail_a_night_that_landed(repo):
    knowledge_holding_a_frame(repo)
    held, store, _, _, _ = driver(repo, text=FRAMED)
    (repo / "docs/knowledge/product.md").write_text("# Продукт\n\n### Налог\n`key: tax`\n", encoding="utf-8")

    outcome = held.go("vat")

    assert all(feature.status is FeatureStatus.DONE for feature in outcome.batch.features)


def test_frames_left_standing_are_closed_by_the_next_batch_go(repo):
    """Closing had one attempt: it stood after the `try/finally`, and `go` refuses a
    finished batch on the way in. A night that died, or a knowledge that could not be
    read, left the blocks standing with nothing able to come back for them."""
    held, store, _, _, _ = driver(repo, text=FRAMED)
    held.go("vat")  # no knowledge at all: nothing to close, and the ids are kept
    assert store.load("vat").frames[0].id == "fr4me1"

    path = knowledge_holding_a_frame(repo)
    again, store, _, _, _ = another_driver(repo, store)
    with pytest.raises(StateError) as refused:
        again.go("vat")

    assert refused.value.code == "batch-finished"
    assert "id: fr4me1" not in path.read_text(encoding="utf-8")
    assert store.load("vat").frames[0].id == ""


def test_a_frame_that_could_not_be_closed_reaches_the_owner(repo):
    knowledge_holding_a_frame(repo, run="last-week")
    spoke = Spoke()
    held, store, _, _, _ = driver(repo, text=FRAMED, spoke=spoke)

    held.go("vat")

    assert any("fr4me1" in line for line in spoke.said), spoke.said


# --- S8f: the ledger, written once by the evening ---------------------------
#
# Every feature of one batch branches from the same base, and a line appended to
# the same section of the same file by two of them is two branches that will not
# merge — 200 of 200, measured before this was built. So the feature names its
# lines in `record`, and the evening lays them: one writer, one point, one
# moment, in the owner's own checkout and uncommitted, the way the frames and
# the sitting's description already are.

from agent_kit.driver.workspace import StepWorkspace


def a_record_that_said(runs, slug, debt=(), fixed=()):
    """What the feature's `record` step left behind, which is what the evening reads."""
    run = runs.load(slug)
    index = [one.name for one in run.steps].index("record")
    StepWorkspace(runs.run_root(slug), index, "record").accept(
        1, {"blocks": [], "closed": [], "files": [], "debt": list(debt), "fixed": list(fixed)}, {}
    )


def ledger_text(repo):
    path = repo / "docs/knowledge/debt.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def described(repo):
    """A project somebody has written down. A night never creates the knowledge
    directory: a run carrying `design` in a project that declares one and has
    written nothing in it is refused before its first session."""
    where = repo / "docs/knowledge"
    where.mkdir(parents=True, exist_ok=True)
    (where / "product.md").write_text("# Продукт\n\n## Части\n\n- деньги — сумма — `walked: 2026-08-20`\n",
                                      encoding="utf-8")
    return where


def a_ledger_holding(repo, *lines):
    from agent_kit.knowledge import Knowledge

    held = Knowledge(repo / "docs/knowledge")
    for what in lines:
        held.write_debt(what, "badly")
    return held


class WhenItLands:
    """A child that writes the feature's papers the moment its run lands."""

    def __init__(self, spawn, said):
        self.spawn, self.said = spawn, said

    def __call__(self, run, argv):
        child = self.spawn(run, argv)
        poll = child.poll

        def and_then():
            code = poll()
            if code == 0 and run.slug in self.said:
                a_record_that_said(self.spawn.runs, run.slug, **self.said[run.slug])
            return code

        child.poll = and_then
        return child


def with_papers(held, spawn, said):
    held.spawn = WhenItLands(spawn, said)
    return held


def test_the_evening_lays_a_line_for_what_the_review_found(repo):
    described(repo)
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_papers(held, spawn, {
        "one": {"debt": [{"key": "aaaaaa", "what": "the retry loop swallows the reason"}]},
        "two": {"debt": [{"key": "bbbbbb", "what": "the counter is off by one"}]},
    })

    held.go("vat")

    text = ledger_text(repo)
    assert "the retry loop swallows the reason" in text
    assert "the counter is off by one" in text
    assert "`key: aaaaaa`" in text and "`run: one`" in text


def test_one_line_for_a_thing_two_features_both_found(repo):
    described(repo)
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_papers(held, spawn, {
        "one": {"debt": [{"key": "aaaaaa", "what": "the same thing"}]},
        "two": {"debt": [{"key": "aaaaaa", "what": "the same thing"}]},
    })

    held.go("vat")

    assert ledger_text(repo).count("the same thing") == 1


def test_the_evening_takes_away_the_lines_the_work_answered(repo):
    from agent_kit.knowledge.debt import debt_key

    described(repo)
    a_ledger_holding(repo, "отчёт считает вручную", "почта уходит дважды")
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_papers(held, spawn, {"one": {"fixed": [debt_key("отчёт считает вручную")]}})

    held.go("vat")

    assert "отчёт считает вручную" not in ledger_text(repo)
    assert "почта уходит дважды" in ledger_text(repo)
    assert "## Работает плохо" in ledger_text(repo)


def test_a_line_the_owner_has_deleted_is_not_laid_a_second_time(repo):
    described(repo)
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_papers(held, spawn, {"one": {"debt": [{"key": "aaaaaa", "what": "the retry loop swallows"}]}})
    held.go("vat")
    assert store.load("vat").debt[0].key == "aaaaaa"

    (repo / "docs/knowledge/debt.md").write_text("# Технический долг\n", encoding="utf-8")
    again, store, _, _, _ = another_driver(repo, store)
    # `go` refuses a finished batch on the way in, and the ledger is written
    # before that refusal — the same recovery the frames were given.
    with pytest.raises(StateError) as refused:
        again.go("vat")

    assert refused.value.code == "batch-finished"
    assert "the retry loop swallows" not in ledger_text(repo)


def test_the_ledger_does_not_fail_the_night(repo):
    """The work landed and the pull requests are open; bookkeeping does not undo that."""
    described(repo)
    (repo / "docs/knowledge/debt.md").write_text("- строка · `key: aaaaaa`\n- другая · `key: aaaaaa`\n",
                                                 encoding="utf-8")
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_papers(held, spawn, {"one": {"debt": [{"key": "bbbbbb", "what": "the retry loop swallows"}]}})

    outcome = held.go("vat")

    assert [one.status for one in outcome.batch.features] == [FeatureStatus.DONE, FeatureStatus.DONE]


def test_a_night_that_is_not_over_lays_nothing_yet(repo):
    described(repo)
    held, store, runs, spawn, _ = driver(
        repo, text=APART, endings={"one": "asks-the-batch-to-stop", "two": "stops-when-asked"}, machine=1,
    )
    with_papers(held, spawn, {"one": {"debt": [{"key": "aaaaaa", "what": "the retry loop swallows"}]}})

    held.go("vat")

    assert "the retry loop swallows" not in ledger_text(repo)


def test_a_feature_that_did_not_land_lays_nothing(repo):
    """Its findings are about code that is going nowhere: a line in the owner's
    ledger naming a run nobody merged is work nobody can act on."""
    described(repo)
    held, store, runs, spawn, _ = driver(repo, text=APART, endings={"two": "failed"})
    with_papers(held, spawn, {"one": {"debt": [{"key": "aaaaaa", "what": "the one that landed"}]}})

    held.go("vat")
    # Its papers as they would be for a feature whose `record` ran and whose
    # `deliver` then refused: the step left an output, and the run failed after.
    a_record_that_said(runs, "two", debt=[{"key": "bbbbbb", "what": "the one that did not"}])
    held._write_the_ledger(store.load("vat"))

    assert "the one that landed" in ledger_text(repo)
    assert "the one that did not" not in ledger_text(repo)


# --- S8g: the manual actions, laid by the same writer as the ledger ---------
#
# Same measurement, same answer: two features of one batch appending to one
# insertion point are two branches that will not merge. The feature names its
# actions in `record`, and the evening lays them — in the owner's own checkout,
# uncommitted, when there is nothing left to build.


def a_record_that_needs_a_person(runs, slug, manual=()):
    run = runs.load(slug)
    index = [one.name for one in run.steps].index("record")
    StepWorkspace(runs.run_root(slug), index, "record").accept(
        1, {"blocks": [], "closed": [], "files": [], "debt": [], "fixed": [],
            "manual": list(manual)}, {}
    )


class WhenItLandsWithChores:
    def __init__(self, spawn, said):
        self.spawn, self.said = spawn, said

    def __call__(self, run, argv):
        child = self.spawn(run, argv)
        poll = child.poll

        def and_then():
            code = poll()
            if code == 0 and run.slug in self.said:
                a_record_that_needs_a_person(self.spawn.runs, run.slug, **self.said[run.slug])
            return code

        child.poll = and_then
        return child


def with_chores(held, spawn, said):
    held.spawn = WhenItLandsWithChores(spawn, said)
    return held


def manual_text(repo):
    path = repo / ".agent-kit/v3/manual.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def test_the_evening_lays_the_line_a_feature_named(repo):
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить STRIPE_KEY",
                            "proof": "sh ops/key.sh", "by_hand": ""}]},
        "two": {"manual": [{"key": "bbbbbb", "what": "направить домен",
                            "proof": "", "by_hand": "нужен человек у панели"}]},
    })

    held.go("vat")

    text = manual_text(repo)
    assert "положить STRIPE_KEY" in text and "`key: aaaaaa`" in text
    assert "`proof: sh ops/key.sh`" in text
    assert "`by-hand: нужен человек у панели`" in text


def test_a_project_that_keeps_no_knowledge_still_gets_its_chores(repo):
    """The ledger is silent for such a project by design; this file is not, and
    that is why it does not live in the knowledge directory."""
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh", "by_hand": ""}]},
    })

    held.go("vat")

    assert "положить ключ" in manual_text(repo)


def test_one_line_for_a_chore_two_features_both_named(repo):
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh", "by_hand": ""}]},
        "two": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh", "by_hand": ""}]},
    })

    held.go("vat")

    assert manual_text(repo).count("положить ключ") == 1


def test_the_evening_does_not_commit_what_it_laid(repo):
    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh", "by_hand": ""}]},
    })

    held.go("vat")

    said = subprocess.run(
        ["git", "status", "--porcelain", "--", ".agent-kit/v3/manual.md"],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    assert said.stdout.strip()


def test_what_the_evening_laid_reaches_the_owner_in_one_message(repo):
    spoke = Spoke()
    held, store, runs, spawn, _ = driver(repo, text=APART, spoke=spoke)
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh", "by_hand": ""}]},
    })

    held.go("vat")

    assert any("положить ключ" in line for line in spoke.said), spoke.said


def test_a_second_batch_go_does_not_resurrect_a_line_the_proof_took_away(repo):
    from agent_kit.manual import Manual

    held, store, runs, spawn, _ = driver(repo, text=APART)
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh", "by_hand": ""}]},
    })
    held.go("vat")
    Manual(repo).close("aaaaaa")

    again, store, _, _, _ = another_driver(repo, store)
    with pytest.raises(StateError):
        again.go("vat")

    assert "положить ключ" not in manual_text(repo)


def test_a_feature_that_did_not_land_hands_nobody_a_chore(repo):
    """A chore that belongs to code nobody merged is work the owner cannot act
    on. Asked the way the ledger's guard is: the papers of the feature that
    failed are written after the fact, so what refuses is the guard and not the
    absence of an output."""
    held, store, runs, spawn, _ = driver(repo, text=APART, endings={"two": "fails"})
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "то, что приземлилось", "proof": "sh a.sh"}]},
    })

    held.go("vat")
    a_record_that_needs_a_person(
        runs, "two", manual=[{"key": "bbbbbb", "what": "то, что не приземлилось", "proof": "sh b.sh"}]
    )
    held._lay_the_manual_actions(store.load("vat"))

    assert "то, что приземлилось" in manual_text(repo)
    assert "то, что не приземлилось" not in manual_text(repo)


def test_a_night_that_is_not_over_hands_over_nothing_yet(repo):
    """Its own copy of the guard the ledger has, so it gets its own test: a batch
    a person stopped keeps features pending, and `batch go` carries on with them."""
    held, store, runs, spawn, _ = driver(
        repo, text=APART, endings={"one": "asks-the-batch-to-stop", "two": "stops-when-asked"}, machine=1,
    )
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh"}]},
    })

    held.go("vat")

    assert "положить ключ" not in manual_text(repo)


def test_a_file_the_repository_ignores_does_not_fail_the_night_and_is_said_out_loud(repo):
    """The kit of S0 to S3 wrote `.agent-kit/v3/.gitignore` = `*`, and only `init`
    clears it. A chore written into a file nobody commits dies with this machine —
    which is the defect this whole file exists against — so it is refused by name."""
    heard = []
    (repo / ".gitignore").write_text(".agent-kit/\n", encoding="utf-8")
    held, store, runs, spawn, _ = driver(repo, text=APART)
    held.say = heard.append
    with_chores(held, spawn, {
        "one": {"manual": [{"key": "aaaaaa", "what": "положить ключ", "proof": "sh a.sh", "by_hand": ""}]},
    })

    outcome = held.go("vat")

    assert all(feature.status is FeatureStatus.DONE for feature in outcome.batch.features)
    assert any("manual-ignored" in line for line in heard), heard
    assert not (repo / ".agent-kit/v3/manual.md").exists()
