"""S8 — a batch: the file the owner writes, and the file the program writes.

Two files and confusing them is the defect this suite exists to catch. The
declaration is what a person composed in the evening; `batch.json` is what is
true right now, and no agent and no person edits it.
"""

import json

import pytest

from agent_kit.batch import BatchStore, FeatureStatus, read_declaration
from agent_kit.errors import ConfigError, StateError

WRITTEN = """
name = "2026-08-26-vat"

[features.rates]
brief = "A table of VAT rates, one row per country"

[features.quote]
brief = "Money quotes a price with VAT on it"
needs = ["rates"]

[features.receipt]
brief = "A receipt line naming the VAT that was charged"
needs = ["quote"]
"""


def declared(tmp_path, text=WRITTEN):
    path = tmp_path / "batch.toml"
    path.write_text(text, encoding="utf-8")
    return read_declaration(path)


# --- the file the owner writes ----------------------------------------------


def test_it_reads_the_features_in_the_order_they_were_declared(tmp_path):
    declaration = declared(tmp_path)

    assert declaration.name == "2026-08-26-vat"
    assert [feature.slug for feature in declaration.features] == ["rates", "quote", "receipt"]
    assert declaration.features[1].needs == ["rates"]
    assert declaration.features[0].brief.startswith("A table of VAT rates")


def test_a_need_that_names_no_feature_of_this_batch_is_refused(tmp_path):
    with pytest.raises(ConfigError) as refused:
        declared(tmp_path, 'name = "n"\n\n[features.quote]\nbrief = "b"\nneeds = ["rates"]\n')

    assert refused.value.code == "no-such-feature"
    assert "rates" in refused.value.detail


def test_a_cycle_is_refused_and_the_loop_is_named(tmp_path):
    with pytest.raises(ConfigError) as refused:
        declared(
            tmp_path,
            'name = "n"\n\n[features.a]\nbrief = "b"\nneeds = ["c"]\n'
            '\n[features.b]\nbrief = "b"\nneeds = ["a"]\n'
            '\n[features.c]\nbrief = "b"\nneeds = ["b"]\n',
        )

    assert refused.value.code == "needs-a-cycle"
    for name in ("a", "b", "c"):
        assert name in refused.value.detail


def test_a_feature_that_needs_itself_is_a_cycle(tmp_path):
    with pytest.raises(ConfigError) as refused:
        declared(tmp_path, 'name = "n"\n\n[features.a]\nbrief = "b"\nneeds = ["a"]\n')

    assert refused.value.code == "needs-a-cycle"


def test_a_feature_with_no_brief_is_refused_before_anything_is_made(tmp_path):
    with pytest.raises(ConfigError) as refused:
        declared(tmp_path, 'name = "n"\n\n[features.a]\n')

    assert refused.value.code == "bad-value"
    assert "brief" in refused.value.detail


def test_a_batch_with_no_features_is_not_a_batch(tmp_path):
    with pytest.raises(ConfigError) as refused:
        declared(tmp_path, 'name = "n"\n')

    assert refused.value.code == "no-features"


def test_something_the_kit_does_not_read_is_refused_rather_than_ignored(tmp_path):
    with pytest.raises(ConfigError) as refused:
        declared(tmp_path, 'name = "n"\nprovider = "codex"\n\n[features.a]\nbrief = "b"\n')

    assert refused.value.code == "unknown-key"


# --- the file the program writes --------------------------------------------


@pytest.fixture
def batch(tmp_path):
    store = BatchStore(tmp_path)
    return store, store.create(declared(tmp_path))


def test_a_new_batch_holds_every_feature_pending(tmp_path, batch):
    store, made = batch

    assert (tmp_path / ".agent-kit/v3/batches/2026-08-26-vat/batch.json").is_file()
    assert [feature.slug for feature in made.features] == ["rates", "quote", "receipt"]
    assert all(feature.status is FeatureStatus.PENDING for feature in made.features)
    assert store.load(made.name).to_dict() == made.to_dict()


def test_one_batch_of_a_name_is_created_once(tmp_path, batch):
    store, _ = batch

    with pytest.raises(StateError) as refused:
        store.create(declared(tmp_path))

    assert refused.value.code == "batch-exists"


def test_only_what_waits_for_nothing_is_ready(batch):
    _, made = batch

    assert made.ready() == ["rates"]


def test_a_feature_becomes_ready_when_what_it_needs_has_landed(batch):
    store, made = batch
    made.starting("rates", tree="/trees/rates")
    made.ended("rates", FeatureStatus.DONE, pull_request="https://example/1")

    assert made.ready() == ["quote"]
    assert store.save(made).feature("rates").pull_request == "https://example/1"


def test_a_feature_that_did_not_land_stops_what_needed_it_by_name(batch):
    _, made = batch
    made.starting("rates", tree="/trees/rates")
    made.ended("rates", FeatureStatus.FAILED, reason="build was refused three times")

    assert made.feature("quote").status is FeatureStatus.STOPPED
    assert made.feature("quote").reason == "needed-rates"
    # The one it actually waited for: receipt never needed rates, it needed quote.
    assert made.feature("receipt").reason == "needed-quote"
    assert made.ready() == []
    assert made.finished


def test_what_did_not_need_it_is_untouched(tmp_path):
    store = BatchStore(tmp_path)
    made = store.create(
        declared(tmp_path, 'name = "n"\n\n[features.a]\nbrief = "b"\n\n[features.b]\nbrief = "b"\n')
    )
    made.starting("a", tree="/trees/a")
    made.ended("a", FeatureStatus.FAILED, reason="no")

    assert made.feature("b").status is FeatureStatus.PENDING
    assert made.ready() == ["b"]


def test_skipping_takes_what_needed_it_and_says_so_at_once(batch):
    _, made = batch

    taken = made.skip("rates", "the rates table is not settled yet")

    assert taken == ["rates", "quote", "receipt"]
    assert made.feature("rates").status is FeatureStatus.SKIPPED
    assert made.feature("quote").status is FeatureStatus.SKIPPED
    assert made.feature("quote").reason == "needed-rates"
    assert made.finished


def test_a_batch_is_over_when_nothing_runs_and_nothing_is_ready(batch):
    _, made = batch

    assert not made.finished
    for slug in ("rates", "quote", "receipt"):
        made.starting(slug, tree=f"/trees/{slug}")
        made.ended(slug, FeatureStatus.DONE)

    assert made.finished
    assert made.landed_everything


def test_what_did_not_land_is_named_in_the_order_it_was_declared(batch):
    _, made = batch
    made.starting("rates", tree="/trees/rates")
    made.ended("rates", FeatureStatus.DONE)
    made.starting("quote", tree="/trees/quote")
    made.ended("quote", FeatureStatus.FAILED, reason="refused")

    assert not made.landed_everything
    assert made.first_that_did_not_land().slug == "quote"


def test_a_batch_from_a_newer_kit_is_refused_rather_than_guessed_at(tmp_path, batch):
    store, made = batch
    path = tmp_path / ".agent-kit/v3/batches/2026-08-26-vat/batch.json"
    data = json.loads(path.read_text())
    data["schema"] = data["schema"] + 1
    path.write_text(json.dumps(data))

    with pytest.raises(StateError) as refused:
        store.load(made.name)

    assert refused.value.code == "schema-too-new"


def test_a_feature_nobody_declared_cannot_be_moved(batch):
    _, made = batch

    with pytest.raises(StateError) as refused:
        made.starting("vat-on-shipping", tree="/trees/x")

    assert refused.value.code == "no-such-feature"


def test_the_batch_is_not_repository_content(tmp_path, batch):
    ignore = tmp_path / ".agent-kit/v3/batches/.gitignore"

    assert ignore.read_text().strip().splitlines()[-1] == "*"
