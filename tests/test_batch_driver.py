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

    def __init__(self, runs, endings, ledger=None, project=None):
        self.runs = runs
        self.endings = endings
        self.ledger = ledger
        self.project = project
        self.started = []

    def __call__(self, run, argv):
        self.started.append((run.slug, list(argv)))
        return _Child(self, run.slug)


class _Child:
    def __init__(self, spawn, slug):
        self.spawn = spawn
        self.slug = slug
        self.ended = False

    def poll(self):
        how = self.spawn.endings.get(self.slug, "done")
        if how == "waits-to-be-stopped":
            if self.spawn.ledger.stop_pending(str(self.spawn.project), self.slug) is None:
                return None
            self.spawn.runs.stop(self.slug, "stopped-by-request: as asked")
            return 130
        if how == "done":
            _land(self.spawn.runs, self.slug)
            return 0
        self.spawn.runs.fail_run(self.slug, f"{self.slug}: build was refused three times")
        return 3


def _land(runs, slug):
    run = runs.load(slug)
    while not run.finished:
        runs.start_step(slug, provider="fake")
        run = runs.pass_step(slug)


def driver(repo, text=THREE, endings=None, machine=4, spoke=None, merges=None):
    store = BatchStore(repo)
    store.create(read_declaration(_declared(repo, text)))
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
    drive, store, runs, spawn, _ = driver(repo, steps := THREE)

    drive.go("vat")

    assert [slug for slug, _ in spawn.started] == ["rates", "quote"]
    assert store.load("vat").landed_everything


def test_features_that_need_nothing_are_started_together(repo):
    drive, store, runs, spawn, _ = driver(repo, APART)

    drive.go("vat")

    assert sorted(slug for slug, _ in spawn.started) == ["one", "two"]


def test_no_more_children_than_the_machine_could_ever_have_sessions(repo):
    """A child that cannot possibly get a slot is a process idling in a poll loop."""
    drive, store, runs, spawn, _ = driver(repo, APART, machine=1)

    started_at_once = []
    original = spawn.__call__

    drive.go("vat")

    # One at a time, in the order they were declared.
    assert [slug for slug, _ in spawn.started] == ["one", "two"]


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
    drive, store, runs, spawn, ledger = driver(
        repo, endings={"rates": "waits-to-be-stopped"},
    )
    ledger.hold_batch(str(repo), "vat")
    ledger.ask_stop(str(repo), "vat", reason="enough for tonight")

    outcome = drive.go("vat")

    assert outcome.interrupted
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
