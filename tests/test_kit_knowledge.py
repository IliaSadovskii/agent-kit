#!/usr/bin/env python3
"""Tests for the knowledge layer: anchors, entries, the derived index, and the cross-checks.

Layers, and why each one is here:

* **unit** — the anchor resolver, the binding grammar, the cross-checks, and the two writers. These
  are string and dict work, so they are asserted directly and exhaustively rather than through a
  fixture.
* **property-based** (fixed seed, stdlib `random`) — documents generated from a small grammar,
  asserting the two invariants the design names: *a section resolved by anchor and the same section
  resolved by heading are the same section, until the heading is renamed*, and *an entry's rev
  changes exactly when its section's text does*. The generator knows where every body truly is and
  where an anchor may legally go, so it is an oracle rather than a restatement of the resolver.
* **integration** — the cache, against real files in a temporary directory and a counting fake
  grader. "One call per document, zero on an unchanged second run, one call carrying one entry
  after one edit" is the feature's cost promise, and it is measured here rather than argued.
* **contract / end to end** — `blueprint_index.py` driven as a subprocess. `--plan` emits JSON an
  agent consumes and `--anchors` writes into the owner's own documents, so both are asserted from
  outside the process, on the file contents and on the exit code.

No grader runs anywhere in this file: the fake one is a plain function, and nothing here calls a
model or a shell. Nor does anything here run the check's `verification` commands — this
repository's own contract names `scripts/validate.sh`, which runs this file.

Run directly (`python3 tests/test_kit_knowledge.py`); `scripts/validate.sh` runs it the same way.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir))
sys.path.insert(0, os.path.join(REPO, "plugins", "agent-kit", "scripts"))

import kit_knowledge as kk  # noqa: E402  — the path above makes this importable from any cwd
import kit_yaml  # noqa: E402

from kit_knowledge import (SectionError, anchor_section, anchors, headings,  # noqa: E402
                           place_anchor, rev_of, section_body, set_entries, split_binding)

INDEX_SCRIPT = os.path.join(REPO, "plugins", "agent-kit", "scripts", "blueprint_index.py")
CONTRACT_PATH = os.path.join(".agent-kit", "knowledge", "contract.yml")
INDEX_PATH = os.path.join(".agent-kit", "knowledge", "index.yml")

# A failure has to be reproducible from the report alone, so the seed is fixed and printed.
SEED = 20260731


# ------------------------------------------------------------------------------------------
# Helpers


def contract_text(entries, sources=("docs/*.md",)):
    """A contract carrying `entries` per collection: {collection: {key: at}}.

    Only `collections` is written. Slot verdicts are `blueprint_check`'s business and are covered
    there; nothing in this module reads them, and a contract that carried them would say otherwise.
    """
    lines = ["version: 1", "", "collections:"]
    for name in kk.COLLECTION_SLOTS:
        bound = entries.get(name)
        if not bound:
            lines += [f"  {name}:", "    status: not_applicable",
                      "    reason: not part of this fixture"]
            continue
        lines += [f"  {name}:", "    status: filled", "    sources:"]
        lines += [f"      - {pattern}" for pattern in sources]
        lines += ["    entries:"]
        for key, at in bound.items():
            lines.append(f"      {key}:")
            lines.append("        at:" if at is None else f"        at: {at}")
    return "\n".join(lines) + "\n"


class ProjectMixin:
    """A miniature project in a temporary directory: documents, a contract, and an index."""

    def make_project(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, "docs"))
        return root

    def write(self, root, relative, text):
        path = os.path.join(root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def read(self, root, relative):
        with open(os.path.join(root, relative), encoding="utf-8") as handle:
            return handle.read()

    def write_contract(self, root, entries, sources=("docs/*.md",)):
        """Write a contract and prove the helper itself produced what it meant to."""
        text = contract_text(entries, sources)
        path = self.write(root, CONTRACT_PATH, text)
        parsed = kit_yaml.load(text)
        self.assertEqual(kk.entry_bindings(parsed), {name: dict(bound)
                                                     for name, bound in entries.items() if bound},
                         f"the test helper mangled the entries:\n{text}")
        return path

    def contract(self, root):
        return kit_yaml.load_path(os.path.join(root, CONTRACT_PATH))


class Grader:
    """A fake grader that records what it was asked, and answers with fixed facts."""

    def __init__(self, facts=None, gaps=None):
        self.calls = []
        self.facts = facts or {}
        self.gaps = gaps or {}

    def __call__(self, group):
        self.calls.append(group)
        return [{"collection": entry["collection"], "key": entry["key"],
                 # Copied from the plan, as the agent copies it in the real flow: the index records
                 # the hash of the text that was read, not the file's hash at apply time.
                 "rev": entry["rev"],
                 "facts": self.facts.get(entry["key"], {"seen": entry["text"].strip()}),
                 "gaps": self.gaps.get(entry["key"], [])}
                for entry in group["entries"]]

    @property
    def documents(self):
        return [call["document"] for call in self.calls]

    @property
    def keys(self):
        """Every entry key carried by every call, in order — the cost the cache is about."""
        return [entry["key"] for call in self.calls for entry in call["entries"]]


# ------------------------------------------------------------------------------------------
# Unit: anchors, and the binding grammar


class AnchorTest(unittest.TestCase):
    DOC = "\n".join([
        "a line of preamble",
        "<!-- kit: preamble.entry -->",
        "",
        "# Handbook",
        "",
        "## Creating an offer",
        "<!-- kit: developer.create_offer -->",
        "",
        "the answer",
        "",
        "### A detail",
        "",
        "a detail of the answer",
        "",
        "## How anchors work",
        "",
        "Write one under the heading:",
        "",
        "```markdown",
        "## Some heading",
        "<!-- kit: some.key -->",
        "```",
        "",
    ])

    def test_anchors_are_found_with_their_line_numbers(self):
        self.assertEqual(anchors(self.DOC),
                         {"preamble.entry": [1], "developer.create_offer": [6]})

    def test_an_anchor_inside_a_code_fence_is_prose_about_anchors_not_a_binding(self):
        """A document that explains the convention writes the anchor inside a fence.

        Reading that as a binding would point an entry at the paragraph describing anchors, and
        the paragraph is exactly what every project's own handbook will contain.
        """
        self.assertNotIn("some.key", anchors(self.DOC))
        with self.assertRaises(SectionError):
            anchor_section(self.DOC, "some.key")

    def test_an_anchor_and_the_heading_above_it_resolve_to_the_same_section(self):
        body, line = anchor_section(self.DOC, "developer.create_offer")
        self.assertEqual(body, section_body(self.DOC, "Creating an offer"))
        self.assertEqual(line, 5)
        self.assertIn("a detail of the answer", body)
        self.assertNotIn("How anchors work", body)

    def test_the_anchor_line_itself_is_not_part_of_the_body(self):
        """Load-bearing: the hash must not notice the kit's own marker.

        If it did, placing anchors would invalidate every entry the same flow had just bound, and
        adopting anchors would cost a second full parse of the whole corpus for no new information.
        """
        body, _ = anchor_section(self.DOC, "developer.create_offer")
        self.assertNotIn("<!-- kit:", body)

    def test_a_duplicate_anchor_is_structural_and_names_both_lines(self):
        text = "# One\n\n<!-- kit: dup -->\n\n## Two\n\n<!-- kit: dup -->\n"
        with self.assertRaises(SectionError) as caught:
            anchor_section(text, "dup")
        self.assertTrue(caught.exception.structural)
        self.assertIn("not unique", str(caught.exception))
        self.assertIn("line 3", str(caught.exception))
        self.assertIn("line 7", str(caught.exception))

    def test_a_missing_anchor_is_a_finding_not_a_structural_failure(self):
        """One entry of twenty-three drifted; the other twenty-two are still checkable."""
        with self.assertRaises(SectionError) as caught:
            anchor_section(self.DOC, "gone.key")
        self.assertFalse(caught.exception.structural)
        self.assertIn("no anchor `<!-- kit: gone.key -->`", str(caught.exception))

    def test_an_anchor_above_the_first_heading_binds_the_preamble(self):
        """The only sensible reading of a file whose first entry is stated before any heading.

        The span is asserted, not the treatment of the anchor line inside it: the preamble path
        keeps markers where the heading path drops them, and no approved document settles which
        of the two is right. That asymmetry is reported separately rather than pinned here.
        """
        body, line = anchor_section(self.DOC, "preamble.entry")
        self.assertIsNone(line, "the preamble has no heading of its own")
        self.assertIn("a line of preamble", body)
        self.assertNotIn("# Handbook", body)
        self.assertNotIn("the answer", body)

    def test_an_anchor_in_a_document_with_no_headings_binds_the_whole_file(self):
        text = "first line\n<!-- kit: whole.file -->\nlast line\n"
        body, line = anchor_section(text, "whole.file")
        self.assertIsNone(line)
        self.assertIn("first line", body)
        self.assertIn("last line", body)

    def test_a_trailing_hash_run_does_not_hide_the_heading_an_anchor_belongs_to(self):
        text = "## Why C#\n<!-- kit: why -->\n\nbody\n"
        self.assertEqual(anchor_section(text, "why")[0], section_body(text, "Why C#"))


class BindingGrammarTest(unittest.TestCase):
    def test_a_fragment_beginning_kit_is_an_anchor(self):
        self.assertEqual(split_binding("docs/A.md#kit:developer.create_offer"),
                         ("docs/A.md", "anchor", "developer.create_offer"))

    def test_any_other_fragment_is_a_heading(self):
        self.assertEqual(split_binding("docs/A.md#Оффер от агентства"),
                         ("docs/A.md", "heading", "Оффер от агентства"))

    def test_a_heading_containing_a_hash_keeps_everything_after_the_first_one(self):
        self.assertEqual(split_binding("docs/A.md#Why C# won")[2], "Why C# won")

    def test_a_binding_that_names_no_section_is_structural(self):
        for at in ("docs/A.md", "docs/A.md#", ""):
            with self.subTest(at=at):
                with self.assertRaises(SectionError) as caught:
                    split_binding(at)
                self.assertTrue(caught.exception.structural)
                self.assertIn("names no section", str(caught.exception))

    def test_a_heading_whose_literal_text_begins_kit_is_read_as_an_anchor(self):
        """The documented cost of one grammar for both binding kinds.

        `path#kit:…` names an anchor, so a heading that literally starts `kit:` cannot be bound by
        name — it is read as an anchor key and reported as a missing anchor. This test exists so
        that limitation cannot change by accident: if the grammar ever learns to tell the two
        apart, this is the assertion that says so out loud.
        """
        self.assertEqual(split_binding("docs/A.md#kit: with a space"),
                         ("docs/A.md", "anchor", "with a space"))
        text = "## kit: notes\n\nbody\n"
        with self.assertRaises(SectionError) as caught:
            kk.resolve("/nowhere", "docs/A.md#kit: notes", text)
        self.assertIn("no anchor", str(caught.exception))
        # And the heading really is there — the binding is the only thing standing between them.
        self.assertEqual(section_body(text, "kit: notes"), "\nbody\n")


class ResolveTest(ProjectMixin, unittest.TestCase):
    def test_resolve_reports_the_path_kind_line_and_rev(self):
        text = "# Doc\n\n## Bound\n<!-- kit: bound -->\n\nbody\n"
        resolved = kk.resolve("/nowhere", "docs/A.md#kit:bound", text)
        self.assertEqual(resolved["path"], "docs/A.md")
        self.assertEqual(resolved["kind"], "anchor")
        self.assertEqual(resolved["line"], 3, "one-based, and it is the heading's line")
        self.assertEqual(resolved["rev"], rev_of(resolved["body"]))
        self.assertRegex(resolved["rev"], r"^[0-9a-f]{12}$")

    def test_a_heading_binding_reports_the_heading_line(self):
        text = "# Doc\n\n## Bound\n\nbody\n"
        self.assertEqual(kk.resolve("/nowhere", "docs/A.md#Bound", text)["line"], 3)

    def test_a_binding_that_reaches_outside_the_project_is_refused(self):
        with tempfile.TemporaryDirectory() as outer:
            root = os.path.join(outer, "project")
            os.makedirs(root)
            with open(os.path.join(outer, "private.md"), "w", encoding="utf-8") as handle:
                handle.write("# Credentials\n\nhunter2\n")
            for path in ("../private.md", os.path.join(outer, "private.md")):
                with self.subTest(path=path):
                    with self.assertRaises(SectionError) as caught:
                        kk.read_document(root, path)
                    self.assertTrue(caught.exception.structural)
                    self.assertIn("outside the project", str(caught.exception))

    def test_a_missing_document_is_structural(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(SectionError) as caught:
                kk.read_document(root, "docs/gone.md")
        self.assertTrue(caught.exception.structural)
        self.assertIn("source file is gone: docs/gone.md", str(caught.exception))


# ------------------------------------------------------------------------------------------
# Property-based: the invariants the design states


ANCHOR_KEY = "the.entry"
ANCHOR_LINE = f"<!-- kit: {ANCHOR_KEY} -->"


def generate_document(rng):
    """A document from a small grammar. Returns (lines, sections, points).

    `sections` is the truth the generator knows and the resolver has to rediscover: a list of
    (level, title, heading line index). `points` maps a section's index to the line positions an
    anchor may be inserted at — block boundaries only, so the generator never proposes a position
    inside a code fence, where an anchor is prose rather than a binding.
    """
    lines, sections, points, level = [], [], {}, 1
    for number in range(rng.randint(2, 5)):
        if sections:
            level = min(3, max(1, level + rng.choice((-1, 0, 0, 1))))
        title = f"Section {number}"
        sections.append((level, title, len(lines)))
        lines.append("#" * level + " " + title)
        points[len(sections) - 1] = [len(lines)]
        for _ in range(rng.randint(0, 3)):
            shape = rng.choice(("prose", "blank", "item", "fence"))
            if shape == "fence":
                lines += ["```", "# not a heading — it is inside a fence", "```"]
            else:
                lines.append({"prose": "a claim", "blank": "", "item": "- a list item"}[shape])
            points[len(sections) - 1].append(len(lines))
    return lines, sections, points


def as_text(lines):
    """Join generated lines into a file.

    The trailing newline is not decoration: a file ends with one, and with it `splitlines()` is the
    exact inverse of this join — so the line numbers the oracle reasons about are the ones the
    resolver sees.
    """
    return "\n".join(lines) + "\n"


def true_span(sections, index, total):
    """Where the body of `sections[index]` really is: (first line, one past the last)."""
    level, _, start = sections[index]
    for other_level, _, other_start in sections[index + 1:]:
        if other_level <= level:
            return start + 1, other_start
    return start + 1, total


def with_anchor(lines, sections, index, at):
    """`lines` with the anchor inserted at `at`, plus the shifted sections and the true body."""
    mutated = lines[:at] + [ANCHOR_LINE] + lines[at:]
    shifted = [(level, title, line + 1 if line >= at else line)
               for level, title, line in sections]
    start, end = true_span(shifted, index, len(mutated))
    body = [line for number, line in enumerate(mutated[start:end], start) if number != at]
    return mutated, shifted, ("\n".join(body) + "\n" if body else "")


class AnchorPropertyTest(unittest.TestCase):
    DOCUMENTS = 60

    def documents(self):
        """The same corpus for every test here, and a separate stream for their own choices."""
        corpus = random.Random(SEED)
        for number in range(self.DOCUMENTS):
            lines, sections, points = generate_document(corpus)
            yield number, random.Random(SEED + number), lines, sections, points

    def anchored(self):
        """Every document again, with the anchor dropped at a random point in a random section."""
        for number, rng, lines, sections, points in self.documents():
            index = rng.randrange(len(sections))
            at = rng.choice(points[index])
            mutated, shifted, body = with_anchor(lines, sections, index, at)
            yield number, rng, mutated, shifted, index, at, body

    def test_an_anchor_and_its_heading_resolve_to_the_same_section(self):
        for number, _, lines, sections, index, at, expected in self.anchored():
            level, title, heading_at = sections[index]
            text = as_text(lines)
            with self.subTest(seed=SEED, document=number, section=title, anchor_at=at):
                detail = (f"seed {SEED}, document {number}, section {title!r} (level {level}), "
                          f"anchor at line {at}\n{text}")
                self.assertEqual(anchor_section(text, ANCHOR_KEY), (expected, heading_at), detail)
                self.assertEqual(section_body(text, title), expected, detail)

    def test_renaming_the_heading_breaks_the_heading_binding_and_not_the_anchor(self):
        """The whole reason the anchor convention exists, asserted rather than described."""
        for number, _, lines, sections, index, at, expected in self.anchored():
            _, title, heading_at = sections[index]
            renamed = list(lines)
            renamed[heading_at] += " (renamed)"
            text = as_text(renamed)
            with self.subTest(seed=SEED, document=number, section=title, anchor_at=at):
                with self.assertRaises(SectionError):
                    section_body(text, title)
                self.assertEqual(anchor_section(text, ANCHOR_KEY)[0], expected,
                                 f"seed {SEED}, document {number}: the anchor moved with the "
                                 f"rename\n{text}")

    def test_the_anchor_rev_changes_when_and_only_when_the_body_changes(self):
        for number, _, lines, sections, index, at, _ in self.anchored():
            _, title, heading_at = sections[index]
            start, end = true_span(sections, index, len(lines))
            before = rev_of(anchor_section(as_text(lines), ANCHOR_KEY)[0])
            for line_number in range(len(lines)):
                # The heading line moves the section's boundary and the anchor line is the kit's
                # own marker; editing either asks a different question from "did the body change".
                if line_number in (heading_at, at):
                    continue
                mutated = list(lines)
                mutated[line_number] += " (edited)"
                after = rev_of(anchor_section(as_text(mutated), ANCHOR_KEY)[0])
                inside = start <= line_number < end
                with self.subTest(seed=SEED, document=number, section=title, line=line_number,
                                  inside=inside):
                    detail = (f"seed {SEED}, document {number}, section {title!r} (body lines "
                              f"{start}:{end}, anchor at {at}), edited line {line_number}: "
                              f"{lines[line_number]!r}\n{as_text(lines)}")
                    if inside:
                        self.assertNotEqual(before, after, f"edit inside, rev unchanged\n{detail}")
                    else:
                        self.assertEqual(before, after, f"edit outside, rev changed\n{detail}")

    def test_placing_an_anchor_under_every_heading_changes_no_section_rev(self):
        """The property that lets a project adopt anchors without re-parsing its whole corpus.

        Without it, the placement flow would invalidate every entry it had just bound: the anchor
        is the kit's own marker, and counting it as prose would make one commit of markers look
        like an edit to every section in the project.
        """
        for number, _, lines, sections, _ in self.documents():
            text = as_text(lines)
            before = {title: rev_of(section_body(text, title)) for _, title, _ in sections}
            after = text
            for _, title, _ in sections:
                after = place_anchor(after, f"key.{title.replace(' ', '_')}", title)
            with self.subTest(seed=SEED, document=number):
                detail = f"seed {SEED}, document {number}\n{text}\n--- became ---\n{after}"
                self.assertNotEqual(after, text, "no anchor was written at all")
                for _, title, _ in sections:
                    self.assertEqual(rev_of(section_body(after, title)), before[title],
                                     f"placing anchors changed section {title!r}\n{detail}")


# ------------------------------------------------------------------------------------------
# Integration: the index, and the cache that is the whole cost story


DOC_A = """\
# Offers

## Creating an offer
<!-- kit: developer.create_offer -->

A developer publishes an offer.

## Accepting an offer
<!-- kit: broker.accept_offer -->

A broker accepts it.
"""

DOC_B = """\
# The offer

## What an offer is
<!-- kit: offer -->

Pending until accepted.
"""

ENTRIES = {
    "actions": {"developer.create_offer": "docs/A.md#kit:developer.create_offer",
                "broker.accept_offer": "docs/A.md#kit:broker.accept_offer"},
    "entities": {"offer": "docs/B.md#kit:offer"},
}


class CacheTest(ProjectMixin, unittest.TestCase):
    """One call per document, zero on an unchanged second run, one call after one edit.

    The design's cost promise, measured with a counting grader rather than argued. Both halves come
    out of one code path — the cache is per section and the grouping is per document — so both are
    asserted here, including how many entries each call carries.
    """

    def setUp(self):
        self.root = self.make_project()
        self.write(self.root, os.path.join("docs", "A.md"), DOC_A)
        self.write(self.root, os.path.join("docs", "B.md"), DOC_B)
        self.write_contract(self.root, ENTRIES)

    def refresh(self, grader):
        index, calls = kk.refresh(self.root, self.contract(self.root), grader)
        kk.write_index(self.root, index)
        return index, calls

    def test_the_first_run_is_one_call_per_document_carrying_every_entry(self):
        grader = Grader()
        _, calls = self.refresh(grader)
        self.assertEqual(calls, 2)
        self.assertEqual(grader.documents, ["docs/A.md", "docs/B.md"])
        self.assertEqual([len(call["entries"]) for call in grader.calls], [2, 1])
        self.assertEqual(sorted(grader.keys),
                         ["broker.accept_offer", "developer.create_offer", "offer"])

    def test_a_second_run_with_nothing_changed_makes_no_call_at_all(self):
        self.refresh(Grader())
        grader = Grader()
        _, calls = self.refresh(grader)
        self.assertEqual(calls, 0)
        self.assertEqual(grader.calls, [])

    def test_editing_one_section_costs_one_call_carrying_exactly_that_entry(self):
        self.refresh(Grader())
        self.write(self.root, os.path.join("docs", "A.md"),
                   DOC_A.replace("A broker accepts it.", "A broker accepts it, at last."))
        grader = Grader()
        _, calls = self.refresh(grader)
        self.assertEqual(calls, 1, "a rewritten paragraph must not re-parse the other documents")
        self.assertEqual(grader.documents, ["docs/A.md"])
        self.assertEqual(grader.keys, ["broker.accept_offer"],
                         "the cache is per section: the other entry in the same document is fresh")

    def test_the_plan_carries_the_section_text_the_grader_needs(self):
        groups = kk.plan(self.root, self.contract(self.root), kk.load_index(self.root))
        entry = next(item for group in groups for item in group["entries"]
                     if item["key"] == "offer")
        self.assertIn("Pending until accepted.", entry["text"])
        self.assertNotIn("<!-- kit:", entry["text"])
        self.assertEqual(entry["at"], "docs/B.md#kit:offer")
        self.assertEqual(entry["line"], 3)

    def test_an_entry_the_contract_no_longer_lists_is_dropped(self):
        self.refresh(Grader())
        remaining = {"actions": {"developer.create_offer": ENTRIES["actions"]
                                 ["developer.create_offer"]}}
        self.write_contract(self.root, remaining)
        index = kk.apply_results(self.root, self.contract(self.root),
                                 kk.load_index(self.root), [])
        self.assertEqual(list(index["actions"]), ["developer.create_offer"])
        self.assertNotIn("entities", index, "a collection with no entries left keeps no block")

    def test_an_entry_the_grader_did_not_return_keeps_what_the_index_had(self):
        """A run that re-parses one document must not blank the entries it never asked about."""
        self.refresh(Grader(facts={"offer": {"states": ["pending"]}}))
        before = kk.load_index(self.root)
        merged = kk.apply_results(self.root, self.contract(self.root), before,
                                  [{"collection": "actions", "key": "broker.accept_offer",
                                    "rev": before["actions"]["broker.accept_offer"]["rev"],
                                    "facts": {"actor": "broker"}, "gaps": []}])
        self.assertEqual(merged["entities"]["offer"], before["entities"]["offer"])
        self.assertEqual(merged["actions"]["broker.accept_offer"]["facts"], {"actor": "broker"})

    def test_a_result_naming_an_entry_the_contract_does_not_record_is_refused(self):
        """The grader answers about what it was asked; anything else is a merge nobody reviewed."""
        for result in ({"collection": "actions", "key": "ghost.action"},
                       {"collection": "screens", "key": "developer.create_offer"},
                       {"collection": "nonsense", "key": "offer"}):
            with self.subTest(result=result):
                with self.assertRaises(ValueError) as caught:
                    kk.apply_results(self.root, self.contract(self.root),
                                     kk.load_index(self.root), [dict(result, facts={}, gaps=[])])
                self.assertIn("is not an entry this contract records", str(caught.exception))

    def test_a_result_with_no_rev_is_refused_rather_than_dated_from_the_current_file(self):
        """`rev` is the hash of the text the grader read, and only the caller knows it.

        Filling it in from the file on disk would make every mid-run edit invisible, which is the
        whole failure the previous test describes. So its absence is an error with a name, not a
        default.
        """
        self.refresh(Grader())
        for result in ({"collection": "entities", "key": "offer", "facts": {}, "gaps": []},
                       {"collection": "entities", "key": "offer", "rev": "", "facts": {}},
                       {"collection": "entities", "key": "offer", "rev": "not-a-hash",
                        "facts": {}}):
            with self.subTest(result=result):
                with self.assertRaises(ValueError) as caught:
                    kk.apply_results(self.root, self.contract(self.root),
                                     kk.load_index(self.root), [result])
                self.assertIn("no `rev` on the result", str(caught.exception))

    def test_gaps_survive_the_round_trip_through_the_index_file(self):
        gap = "nothing says who expires the offer — `#` and 'quotes' included"
        self.refresh(Grader(gaps={"offer": [gap]}))
        self.assertEqual(kk.load_index(self.root)["entities"]["offer"]["gaps"], [gap])

    def test_a_document_edited_between_plan_and_apply_is_not_recorded_as_parsed(self):
        """The race the two-invocation split creates, and the one it must not lose.

        `--plan` hands a section's text to a grader, the grader takes a while, and the owner edits
        that same section meanwhile. The facts that come back describe text that is no longer on
        disk. Recording them against the *current* hash would bury that for ever: the next check
        finds the entry fresh and never re-parses it. The entry has to come back stale instead.
        """
        self.refresh(Grader())
        self.write(self.root, os.path.join("docs", "B.md"),
                   DOC_B.replace("Pending until accepted.", "Pending until accepted or withdrawn."))
        contract = self.contract(self.root)
        index = kk.load_index(self.root)
        groups = kk.plan(self.root, contract, index)
        self.assertEqual([entry["key"] for group in groups for entry in group["entries"]],
                         ["offer"])
        # The grader is running. The owner edits the same section again.
        self.write(self.root, os.path.join("docs", "B.md"),
                   DOC_B.replace("Pending until accepted.", "Pending, accepted, or withdrawn."))
        graded = groups[0]["entries"][0]["rev"]
        merged = kk.apply_results(self.root, contract, index,
                                  [{"collection": "entities", "key": "offer", "rev": graded,
                                    "facts": {"states": ["pending", "accepted"]}, "gaps": []}])
        kk.write_index(self.root, merged)
        state = {item["key"]: item["stale"]
                 for item in kk.entry_state(self.root, contract, kk.load_index(self.root))}
        self.assertTrue(state["offer"],
                        "the facts describe text that was replaced while the grader ran, so the "
                        "entry must read as stale and be parsed again")

    def test_entry_state_reports_the_recorded_rev_and_the_resolved_one(self):
        self.refresh(Grader())
        state = {item["key"]: item for item in
                 kk.entry_state(self.root, self.contract(self.root), kk.load_index(self.root))}
        self.assertFalse(any(item["stale"] for item in state.values()))
        self.assertEqual(state["offer"]["recorded"], state["offer"]["resolved"]["rev"])
        self.assertEqual(state["offer"]["kind"], "anchor")
        self.assertIsNone(state["offer"]["error"])

    def test_an_index_that_is_not_a_mapping_is_refused_rather_than_read(self):
        self.write(self.root, INDEX_PATH, "- version: 1\n")
        with self.assertRaises(kit_yaml.KitYamlError):
            kk.load_index(self.root)

    def test_no_index_at_all_reads_as_an_empty_one(self):
        self.assertEqual(kk.load_index(self.root), {"version": 1})

    def test_the_index_survives_a_round_trip_through_its_own_writer(self):
        """Every entry the checks read comes back off disk; an all-digit hash is the hard one."""
        self.refresh(Grader(facts={"offer": {"states": ["pending"], "created_by": []}}))
        written = kk.load_index(self.root)
        kk.write_index(self.root, written)
        self.assertEqual(kk.load_index(self.root), written)
        for collection in ("actions", "entities"):
            for key, entry in written[collection].items():
                with self.subTest(entry=f"{collection}/{key}"):
                    self.assertIsInstance(entry["rev"], str)
                    self.assertRegex(entry["rev"], r"^[0-9a-f]{12}$")


# ------------------------------------------------------------------------------------------
# Unit: the cross-checks, asserted on the message and not only on the count


def index_of(**collections):
    """An index built straight from facts: {collection: {key: facts}}."""
    index = {"version": 1}
    for name, entries in collections.items():
        index[name] = {key: {"at": f"docs/A.md#kit:{key}", "rev": "0" * 12,
                             "facts": facts, "gaps": []}
                       for key, facts in entries.items()}
    return index


CLEAN = dict(
    actors={"developer": {"kind": "role", "actions": ["developer.create_offer"]},
            "broker": {"kind": "role", "actions": ["broker.accept_offer"]}},
    entities={"offer": {"states": ["pending", "accepted"],
                        "created_by": ["developer.create_offer"],
                        "closed_by": ["broker.accept_offer"]}},
    actions={"developer.create_offer": {"actor": "developer", "entities_written": ["offer"],
                                        "statuses_set": ["offer.pending"], "screens": ["S1"]},
             "broker.accept_offer": {"actor": "broker", "entities_written": ["offer"],
                                     "statuses_set": ["offer.accepted"], "screens": ["S2"]}},
)

MAP = {"S1": "implemented", "S2": "planned", "S3": "rejected", "S4": "idea"}


def broken(**changes):
    """The clean index with one collection's facts replaced."""
    merged = {name: {key: dict(facts) for key, facts in entries.items()}
              for name, entries in CLEAN.items()}
    for name, entries in changes.items():
        for key, facts in entries.items():
            merged[name][key] = facts
    return index_of(**merged)


class CrossCheckTest(unittest.TestCase):
    def messages(self, index, screens=MAP):
        return [f"{where}: {message}" for where, message in kk.cross_check(index, screens)]

    def assertMentions(self, findings, fragment):
        self.assertTrue(any(fragment in message for message in findings),
                        f"no finding contains {fragment!r}; findings were {findings}")

    def test_a_sound_index_produces_nothing(self):
        self.assertEqual(self.messages(index_of(**CLEAN)), [])

    def test_a_status_no_entity_state_covers_is_reported_with_the_states_it_has(self):
        index = broken(entities={"offer": {"states": ["pending"],
                                           "created_by": ["developer.create_offer"],
                                           "closed_by": ["broker.accept_offer"]}})
        findings = self.messages(index)
        self.assertMentions(findings, "actions/broker.accept_offer: sets offer.accepted")
        self.assertMentions(findings, "no `accepted` state in entities/offer")
        self.assertMentions(findings, "(states are: pending)")

    def test_a_status_that_is_not_qualified_by_its_entity_is_reported_as_uncheckable(self):
        index = broken(actions={"broker.accept_offer": {"actor": "broker",
                                                        "entities_written": ["offer"],
                                                        "statuses_set": ["accepted"]}})
        self.assertMentions(self.messages(index), "a status reads entity.state")

    def test_an_action_attributed_to_an_actor_that_does_not_list_it(self):
        index = broken(actors={"broker": {"kind": "role", "actions": []},
                               "developer": {"kind": "role",
                                             "actions": ["developer.create_offer"]}})
        self.assertMentions(self.messages(index),
                            "actions/broker.accept_offer: attributed to actors/broker, which does "
                            "not list it among the actions it may perform")

    def test_an_actor_no_action_is_attributed_to(self):
        """The other direction: a role in the documents that nothing in the product uses."""
        index = broken(actors={"developer": {"kind": "role",
                                             "actions": ["developer.create_offer"]},
                               "broker": {"kind": "role",
                                          "actions": ["broker.accept_offer"]},
                               "auditor": {"kind": "role", "actions": []}})
        self.assertMentions(self.messages(index),
                            "actors/auditor: declared, but no action is attributed to it")

    def test_an_action_no_actor_initiates(self):
        index = broken(actions={"broker.accept_offer": {"entities_written": ["offer"],
                                                        "statuses_set": ["offer.accepted"]}})
        self.assertMentions(self.messages(index),
                            "actions/broker.accept_offer: no actor initiates it")

    def test_a_screen_an_action_names_that_is_not_on_the_map(self):
        index = broken(actions={"developer.create_offer": {"actor": "developer",
                                                           "entities_written": ["offer"],
                                                           "statuses_set": ["offer.pending"],
                                                           "screens": ["S9"]}})
        findings = self.messages(index)
        self.assertMentions(findings,
                            "actions/developer.create_offer: launches from S9, which is not on "
                            "the screen map")
        self.assertMentions(findings, "screens/S1: on the map, and no action is launched from it")

    def test_a_rejected_or_idea_screen_is_not_expected_to_be_reachable(self):
        """A rejected screen is the owner's decision not to have it; an idea is not a promise."""
        findings = self.messages(index_of(**CLEAN))
        self.assertEqual(findings, [], "S3 is rejected and S4 is an idea; neither is a finding")
        with_planned = dict(MAP, S5="planned")
        self.assertEqual(self.messages(index_of(**CLEAN), with_planned),
                         ["screens/S5: on the map, and no action is launched from it"])

    def test_no_screen_map_silences_the_screens_check_entirely(self):
        """"No map" must never read as "no screens", or every reference becomes a finding."""
        index = broken(actions={"developer.create_offer": {"actor": "developer",
                                                           "entities_written": ["offer"],
                                                           "statuses_set": ["offer.pending"],
                                                           "screens": ["S9"]}})
        self.assertEqual(self.messages(index, None), [])

    def test_an_entity_with_no_creating_or_closing_action(self):
        index = broken(entities={"offer": {"states": ["pending", "accepted"]}})
        findings = self.messages(index)
        self.assertMentions(findings, "entities/offer: no action creates it")
        self.assertMentions(findings, "entities/offer: no action closes it")

    def test_an_entity_no_action_writes_is_not_asked_for_a_lifecycle(self):
        """A reference book nothing writes has no creating action, and that is not a finding."""
        index = broken(entities={"offer": {"states": ["pending", "accepted"],
                                           "created_by": ["developer.create_offer"],
                                           "closed_by": ["broker.accept_offer"]},
                                 "region": {"states": ["active"]}})
        self.assertEqual(self.messages(index), [])

    def test_a_collection_with_no_entries_is_not_an_authority(self):
        """The noise-control property, and the easiest one in the file to regress.

        A project whose `actors` slot is `not_applicable` has no access model to check against.
        Reporting every action's actor as an instance nobody described would bury the findings
        that mean something under one per action.
        """
        index = index_of(actions=CLEAN["actions"], entities=CLEAN["entities"])
        self.assertNotIn("actors", index)
        for message in self.messages(index):
            self.assertNotIn("actors/", message, f"actors is empty, so it is not an authority: "
                                                 f"{message}")

    def test_the_other_checks_skip_a_key_set_completeness_has_reported(self):
        """A document that never described `deal` must not be reported once per check."""
        index = broken(actions={"developer.create_offer": {
            "actor": "developer",
            "entities_written": ["offer", "deal"],
            "statuses_set": ["offer.pending", "deal.created"],
            "screens": ["S1"]}})
        findings = self.messages(index)
        for message in findings:
            with self.subTest(message=message):
                self.assertNotIn("no `created` state", message,
                                 "the statuses check did not skip it")
                self.assertNotIn("entities/deal:", message, "the lifecycle check did not skip it")

    def test_a_key_no_entry_describes_is_reported_once(self):
        """The same sentence twice is the noise the ordering of these checks exists to prevent.

        The design says a document that never described `deal` produces one finding, not four:
        set completeness reports it and the rest stand down. An entry that names the missing key
        through two facts — it writes `deal` and it sets `deal.created` — is the ordinary shape of
        that case, and it must still be one finding.
        """
        index = broken(actions={"developer.create_offer": {
            "actor": "developer",
            "entities_written": ["offer", "deal"],
            "statuses_set": ["offer.pending", "deal.created"],
            "screens": ["S1"]}})
        about_deal = [message for message in self.messages(index) if "deal" in message]
        self.assertEqual(about_deal,
                         ["actions/developer.create_offer: names entities/deal, which no entry "
                          "describes"])

    def test_an_entry_with_no_facts_at_all_is_not_a_crash(self):
        index = index_of(actions={"a.b": {}}, actors={"a": {}}, entities={"e": {}})
        self.assertIsInstance(kk.cross_check(index, MAP), list)


class ScreenMapTest(ProjectMixin, unittest.TestCase):
    MAP_JS = """\
window.SCREENS = {
  meta: { platform: 'mobile', nextScreenId: 4 },
  screens: [
    { id: 'S1', title: 'Home', status: 'implemented' },
    { id: 'S2', title: 'Later', status: 'idea' },
  ],
};
"""

    def test_a_project_with_no_map_answers_none_rather_than_empty(self):
        root = self.make_project()
        self.assertIsNone(kk.screen_map_path(root))
        self.assertIsNone(kk.screen_ids(root), "an empty dict would read as `no screens exist`")

    def test_the_conventional_path_is_found_with_ids_and_statuses(self):
        root = self.make_project()
        self.write(root, kk.DEFAULT_SCREEN_MAP, self.MAP_JS)
        self.assertEqual(kk.screen_ids(root), {"S1": "implemented", "S2": "idea"})

    def test_the_manifest_names_the_map_when_the_project_keeps_it_elsewhere(self):
        root = self.make_project()
        self.write(root, os.path.join("product", "map.js"), self.MAP_JS)
        self.write(root, kk.MANIFEST_PATH, "sources:\n  screens: product/map.js\n")
        self.assertEqual(kk.screen_map_path(root), "product/map.js")
        self.assertEqual(sorted(kk.screen_ids(root)), ["S1", "S2"])

    def test_a_manifest_pointing_outside_the_project_is_ignored(self):
        root = self.make_project()
        self.write(root, kk.MANIFEST_PATH, "sources:\n  screens: ../elsewhere.js\n")
        self.assertIsNone(kk.screen_map_path(root))

    def test_an_unreadable_manifest_does_not_take_the_check_down(self):
        root = self.make_project()
        self.write(root, kk.MANIFEST_PATH, "sources:\n  screens: &anchor\n")
        self.write(root, kk.DEFAULT_SCREEN_MAP, self.MAP_JS)
        self.assertEqual(kk.screen_map_path(root), kk.DEFAULT_SCREEN_MAP)


# ------------------------------------------------------------------------------------------
# Integration: the two writes — the only moments the kit edits someone else's file


class PlaceAnchorTest(unittest.TestCase):
    DOC = "# Handbook\n\nintro\n\n## Creating an offer\n\nthe answer\n\n## Sibling\n\nmore\n"

    def test_the_anchor_lands_on_its_own_line_directly_under_the_heading(self):
        after = place_anchor(self.DOC, "developer.create_offer", "Creating an offer")
        self.assertIn("## Creating an offer\n<!-- kit: developer.create_offer -->\n", after)
        self.assertEqual(after.count("<!-- kit:"), 1)
        self.assertEqual(anchor_section(after, "developer.create_offer")[0],
                         section_body(self.DOC, "Creating an offer"))

    def test_running_it_again_changes_nothing(self):
        once = place_anchor(self.DOC, "d.create", "Creating an offer")
        self.assertEqual(place_anchor(once, "d.create", "Creating an offer"), once)

    def test_an_anchor_already_elsewhere_in_the_file_is_refused_not_moved(self):
        """A binding that already resolves is the owner's; the kit never silently repoints one."""
        elsewhere = self.DOC.replace("more", "more\n<!-- kit: d.create -->")
        with self.assertRaises(SectionError) as caught:
            place_anchor(elsewhere, "d.create", "Creating an offer")
        self.assertIn("the kit never silently moves one", str(caught.exception))
        self.assertIn("line 12", str(caught.exception))

    def test_a_key_already_anchored_twice_is_refused(self):
        twice = self.DOC.replace("intro", "<!-- kit: d.create -->").replace(
            "more", "<!-- kit: d.create -->")
        with self.assertRaises(SectionError) as caught:
            place_anchor(twice, "d.create", "Creating an offer")
        self.assertIn("already in this document twice", str(caught.exception))

    def test_a_heading_that_is_not_there_or_not_unique_is_refused(self):
        with self.assertRaises(SectionError) as caught:
            place_anchor(self.DOC, "k", "Renamed")
        self.assertIn("no heading 'Renamed'", str(caught.exception))
        with self.assertRaises(SectionError) as caught:
            place_anchor(self.DOC + "\n## Sibling\n\nagain\n", "k", "Sibling")
        self.assertIn("is not unique", str(caught.exception))

    def test_a_document_whose_last_line_has_no_newline_still_gets_a_line_of_its_own(self):
        after = place_anchor("# One\n\n## Two\n\nbody", "k", "Two")
        self.assertEqual(after, "# One\n\n## Two\n<!-- kit: k -->\n\nbody\n")


CONTRACT_WITH_COMMENTS = """\
# The owner's own contract, comments and all.
#
# Every byte of this file except one collection's `entries:` block has to survive the edit.

version: 1

collections:
  # Who or what initiates anything.
  actors:
    status: filled
    sources:
      - docs/*.md
    criterion: everyone who initiates anything

  # The things the product keeps.
  entities:
    status: filled
    sources:
      - docs/*.md
    entries:
      offer:
        at: docs/B.md#kit:offer
      lot:
        at: docs/B.md#Лот
    criterion: >-
      every entity names its states, its transitions and its relations

  actions:
    status: not_applicable
    reason: nothing does anything yet

  screens:
    status: not_applicable
    reason: no interface

  # The last block in the file, and the one an insertion is most likely to run off the end of.
  integrations:
    status: filled
    sources:
      - docs/*.md
    criterion: everything outside this tree that it depends on
"""


class SetEntriesTest(unittest.TestCase):
    """A surgical text edit, because no dumper preserves the prose around the values.

    The contract is a file a person maintains: the statuses are their verdicts and the comments are
    the reason the file is readable. The kit replaces one block and leaves the rest byte for byte.
    """

    @staticmethod
    def without_entries(text):
        """Every line that is not part of an `entries:` block, computed independently of the code.

        The shape is fixed and narrow — `    entries:`, `      <key>:`, `        at: …` — so this
        oracle does not have to know anything about how the edit finds the block.
        """
        kept = []
        for line in text.splitlines(keepends=True):
            stripped = line.rstrip("\n")
            if stripped == "    entries:":
                continue
            if stripped.startswith("      ") and stripped.endswith(":") and \
                    not stripped.startswith("        "):
                continue
            if stripped.startswith("        at:"):
                continue
            kept.append(line)
        return "".join(kept)

    def assertEverythingElseSurvives(self, before, after):
        self.assertEqual(self.without_entries(after), self.without_entries(before),
                         "the edit touched something other than one `entries:` block")

    def entries_of(self, text, collection):
        parsed = kit_yaml.load(text)
        return kk.entry_bindings(parsed).get(collection, {})

    def test_a_collection_with_no_block_yet_gains_one(self):
        after = set_entries(CONTRACT_WITH_COMMENTS, "actors", {"broker": "docs/A.md#kit:broker"})
        self.assertEverythingElseSurvives(CONTRACT_WITH_COMMENTS, after)
        self.assertEqual(self.entries_of(after, "actors"), {"broker": "docs/A.md#kit:broker"})
        self.assertEqual(self.entries_of(after, "entities"),
                         {"offer": "docs/B.md#kit:offer", "lot": "docs/B.md#Лот"},
                         "another collection's entries are none of this edit's business")

    def test_an_existing_block_is_replaced_whole(self):
        after = set_entries(CONTRACT_WITH_COMMENTS, "entities", {"deal": "docs/C.md#kit:deal"})
        self.assertEverythingElseSurvives(CONTRACT_WITH_COMMENTS, after)
        self.assertEqual(self.entries_of(after, "entities"), {"deal": "docs/C.md#kit:deal"})
        self.assertNotIn("offer:", after)

    def test_an_empty_map_removes_the_block_and_nothing_else(self):
        after = set_entries(CONTRACT_WITH_COMMENTS, "entities", {})
        self.assertEverythingElseSurvives(CONTRACT_WITH_COMMENTS, after)
        self.assertEqual(self.entries_of(after, "entities"), {})
        self.assertNotIn("    entries:\n", after)
        self.assertIn("every entity names its states", after)

    def test_the_collection_last_in_the_file_is_written_inside_its_own_block(self):
        after = set_entries(CONTRACT_WITH_COMMENTS, "integrations",
                            {"stripe": "docs/I.md#kit:stripe"})
        self.assertEverythingElseSurvives(CONTRACT_WITH_COMMENTS, after)
        self.assertEqual(self.entries_of(after, "integrations"),
                         {"stripe": "docs/I.md#kit:stripe"})
        self.assertTrue(after.endswith("        at: docs/I.md#kit:stripe\n"))

    def test_every_comment_and_verdict_in_the_file_is_still_there(self):
        after = set_entries(CONTRACT_WITH_COMMENTS, "entities", {"deal": "docs/C.md#kit:deal"})
        for line in ("# The owner's own contract, comments and all.",
                     "  # Who or what initiates anything.",
                     "  # The things the product keeps.",
                     "    reason: nothing does anything yet",
                     "    criterion: >-",
                     "      every entity names its states, its transitions and its relations"):
            with self.subTest(line=line):
                self.assertIn(line + "\n", after)
        self.assertEqual(kit_yaml.load(after)["collections"]["entities"]["criterion"],
                         "every entity names its states, its transitions and its relations")

    def test_a_binding_that_would_not_read_back_plainly_is_quoted(self):
        after = set_entries(CONTRACT_WITH_COMMENTS, "actors",
                            {"broker": "docs/A.md#Roles # and rights"})
        self.assertEqual(self.entries_of(after, "actors"),
                         {"broker": "docs/A.md#Roles # and rights"})

    def test_a_contract_missing_the_block_the_edit_needs_says_which(self):
        with self.assertRaises(SectionError) as caught:
            set_entries("version: 1\n", "actors", {})
        self.assertIn("no `collections:` block", str(caught.exception))
        with self.assertRaises(SectionError) as caught:
            set_entries("version: 1\ncollections:\n  actors:\n    status: empty\n", "entities", {})
        self.assertIn("records no `entities` collection", str(caught.exception))

    def test_a_contract_whose_last_line_has_no_newline_stays_readable(self):
        """The kit writes into a file it did not create, so it cannot assume how it ends.

        `place_anchor` terminates the last line before inserting; this edit is the other half of
        the same flow and writes the same owner's file. Without the same care the inserted block
        lands on the end of the last value, and the contract stops parsing at all — which the next
        check reports as the owner's fault.
        """
        before = CONTRACT_WITH_COMMENTS.rstrip("\n")
        after = set_entries(before, "integrations", {"stripe": "docs/I.md#kit:stripe"})
        try:
            parsed = kit_yaml.load(after)
        except kit_yaml.KitYamlError as exc:
            self.fail(f"the edit left the contract unreadable ({exc}):\n{after}")
        self.assertEqual(kk.entry_bindings(parsed).get("integrations"),
                         {"stripe": "docs/I.md#kit:stripe"})


# ------------------------------------------------------------------------------------------
# Contract / end to end: blueprint_index.py, driven the way the skill drives it


class IndexCliTest(ProjectMixin, unittest.TestCase):
    def setUp(self):
        self.root = self.make_project()
        self.write(self.root, os.path.join("docs", "A.md"), DOC_A)
        self.write(self.root, os.path.join("docs", "B.md"), DOC_B)
        self.write_contract(self.root, ENTRIES)

    def run_index(self, *args, root=None):
        done = subprocess.run([sys.executable, INDEX_SCRIPT, *args], cwd=root or self.root,
                              capture_output=True, text=True)
        self.assertNotIn("Traceback", done.stderr, f"the run crashed:\n{done.stderr}")
        return done

    def write_json(self, name, payload):
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        return path

    def test_plan_then_apply_writes_an_index_the_reader_takes_back(self):
        done = self.run_index("--plan")
        self.assertEqual(done.returncode, 0, done.stderr)
        groups = json.loads(done.stdout)
        self.assertEqual([group["document"] for group in groups], ["docs/A.md", "docs/B.md"])
        self.assertIn("2 grader call(s) for 3 entries", done.stderr)

        results = [{"collection": entry["collection"], "key": entry["key"],
                    "rev": entry["rev"], "facts": {"actor": "developer"}, "gaps": []}
                   for group in groups for entry in group["entries"]]
        done = self.run_index("--apply", self.write_json("results.json", results))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("3 entries parsed", done.stdout)
        index = kk.load_index(self.root)
        self.assertEqual(sorted(index["actions"]),
                         ["broker.accept_offer", "developer.create_offer"])
        self.assertEqual(json.loads(self.run_index("--plan").stdout), [],
                         "everything parsed, so a second plan has nothing to ask")

    def test_an_unknown_argument_is_refused(self):
        done = self.run_index("--rebuild")
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage:", done.stderr)

    def test_apply_refuses_a_result_the_contract_does_not_record(self):
        path = self.write_json("results.json", [{"collection": "actions", "key": "ghost",
                                                 "facts": {}, "gaps": []}])
        done = self.run_index("--apply", path)
        self.assertEqual(done.returncode, 2)
        self.assertIn("is not an entry this contract records", done.stderr)

    def test_anchors_writes_each_one_under_its_heading_and_records_the_bindings(self):
        root = self.make_project()
        self.write(root, os.path.join("docs", "C.md"),
                   "# Offers\n\n## Creating an offer\n\nbody\n\n## The offer\n\nmore\n")
        self.write_contract(root, {"actions": {}, "entities": {}}, sources=("docs/*.md",))
        proposal = self.write_json("proposal.json", [
            {"collection": "actions", "key": "developer.create_offer", "path": "docs/C.md",
             "heading": "Creating an offer"},
            {"collection": "entities", "key": "offer", "path": "docs/C.md",
             "heading": "The offer"},
        ])
        done = self.run_index("--anchors", proposal, root=root)
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        document = self.read(root, os.path.join("docs", "C.md"))
        self.assertIn("## Creating an offer\n<!-- kit: developer.create_offer -->\n", document)
        self.assertIn("## The offer\n<!-- kit: offer -->\n", document)
        contract = kit_yaml.load_path(os.path.join(root, CONTRACT_PATH))
        self.assertEqual(kk.entry_bindings(contract),
                         {"actions": {"developer.create_offer":
                                      "docs/C.md#kit:developer.create_offer"},
                          "entities": {"offer": "docs/C.md#kit:offer"}})

    def test_a_proposal_that_fails_halfway_writes_nothing_at_all(self):
        """Anchors in the owner's documents that the contract does not know about is the one
        state this flow must not be able to produce, so it is all or nothing."""
        root = self.make_project()
        self.write(root, os.path.join("docs", "C.md"),
                   "# Offers\n\n## Creating an offer\n\nbody\n")
        self.write_contract(root, {"actions": {}}, sources=("docs/*.md",))
        before_doc = self.read(root, os.path.join("docs", "C.md"))
        before_contract = self.read(root, CONTRACT_PATH)
        proposal = self.write_json("proposal.json", [
            {"collection": "actions", "key": "developer.create_offer", "path": "docs/C.md",
             "heading": "Creating an offer"},
            {"collection": "actions", "key": "broker.accept_offer", "path": "docs/C.md",
             "heading": "A heading nobody wrote"},
        ])
        done = self.run_index("--anchors", proposal, root=root)
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn("no heading 'A heading nobody wrote'", done.stderr)
        self.assertEqual(self.read(root, os.path.join("docs", "C.md")), before_doc,
                         "the first document was modified before the second one failed")
        self.assertEqual(self.read(root, CONTRACT_PATH), before_contract)

    def test_a_proposal_naming_a_path_outside_the_project_is_refused(self):
        with tempfile.TemporaryDirectory() as outer:
            root = os.path.join(outer, "project")
            os.makedirs(os.path.join(root, "docs"))
            self.write(root, os.path.join("docs", "C.md"), "# Offers\n\n## Creating\n\nbody\n")
            self.write_contract(root, {"actions": {}}, sources=("docs/*.md",))
            outside = os.path.join(outer, "elsewhere.md")
            with open(outside, "w", encoding="utf-8") as handle:
                handle.write("# Elsewhere\n\n## Creating\n\nnot yours\n")
            for path in ("../elsewhere.md", outside):
                with self.subTest(path=path):
                    proposal = os.path.join(root, "proposal.json")
                    with open(proposal, "w", encoding="utf-8") as handle:
                        json.dump([{"collection": "actions", "key": "a.b", "path": path,
                                    "heading": "Creating"}], handle)
                    done = self.run_index("--anchors", proposal, root=root)
                    self.assertEqual(done.returncode, 2, done.stdout)
                    self.assertIn("is not a document in this project", done.stderr)
                    with open(outside, encoding="utf-8") as handle:
                        self.assertNotIn("<!-- kit:", handle.read())

    def test_a_proposal_that_names_the_same_entry_twice_is_refused(self):
        proposal = self.write_json("proposal.json", [
            {"collection": "actions", "key": "developer.create_offer", "path": "docs/A.md",
             "heading": "Creating an offer"},
            {"collection": "actions", "key": "developer.create_offer", "path": "docs/A.md",
             "heading": "Accepting an offer"},
        ])
        done = self.run_index("--anchors", proposal)
        self.assertEqual(done.returncode, 2)
        self.assertIn("is proposed twice", done.stderr)

    def test_a_proposal_missing_a_field_is_refused_by_name(self):
        for proposal, fragment in (
                ([{"collection": "widgets", "key": "a", "path": "docs/A.md", "heading": "Offers"}],
                 "is not a collection this kit version knows"),
                ([{"collection": "actions", "key": "a", "path": "docs/A.md"}],
                 "needs collection, key, path"),
                ([], "expected a non-empty list")):
            with self.subTest(fragment=fragment):
                done = self.run_index("--anchors", self.write_json("p.json", proposal))
                self.assertEqual(done.returncode, 2, done.stdout)
                self.assertIn(fragment, done.stderr)

    def test_a_project_with_no_contract_is_refused_rather_than_crashed(self):
        with tempfile.TemporaryDirectory() as root:
            done = self.run_index("--plan", root=root)
        self.assertEqual(done.returncode, 2)
        self.assertIn("no knowledge contract", done.stderr)



# ------------------------------------------------------------------------------------------
# The review round: what the design reviewer found, and what each fix has to keep true


class BrokenBindingTest(ProjectMixin, unittest.TestCase):
    """A binding that stopped resolving must never cost more than the entry it belongs to.

    Two separate ways it used to: `--plan` dropped such an entry without a word, so a contract
    whose every binding had broken planned nothing and read as "the index is current"; and
    `--apply` raised on the first one, throwing away every other result in the batch — dozens of
    grader calls, measured at roughly 40k tokens a document.
    """

    def setUp(self):
        self.root = self.make_project()
        self.write(self.root, os.path.join("docs", "A.md"), DOC_A)
        self.write(self.root, os.path.join("docs", "B.md"), DOC_B)
        self.write_contract(self.root, ENTRIES)

    def run_index(self, *args):
        done = subprocess.run([sys.executable, INDEX_SCRIPT, *args], cwd=self.root,
                              capture_output=True, text=True)
        self.assertNotIn("Traceback", done.stderr, f"the run crashed:\n{done.stderr}")
        return done

    def break_one_anchor(self):
        """Remove the anchor `entities/offer` binds to, leaving the document in place."""
        self.write(self.root, os.path.join("docs", "B.md"),
                   DOC_B.replace("<!-- kit: offer -->\n", ""))

    def test_plan_names_every_entry_it_could_not_plan(self):
        self.break_one_anchor()
        done = self.run_index("--plan")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("skipped entities/offer", done.stderr)
        self.assertIn("no anchor", done.stderr)
        self.assertEqual([entry["key"] for group in json.loads(done.stdout)
                          for entry in group["entries"]],
                         ["developer.create_offer", "broker.accept_offer"])

    def test_a_plan_that_is_empty_only_because_everything_broke_says_so(self):
        """An empty plan reads as "the index is current"; it must not be able to mean this."""
        for name, text in (("A.md", DOC_A), ("B.md", DOC_B)):
            self.write(self.root, os.path.join("docs", name),
                       "\n".join(line for line in text.splitlines()
                                 if not line.startswith("<!-- kit:")) + "\n")
        done = self.run_index("--plan")
        self.assertEqual(json.loads(done.stdout), [])
        for key in ("developer.create_offer", "broker.accept_offer", "offer"):
            self.assertIn(f"skipped {'entities' if key == 'offer' else 'actions'}/{key}",
                          done.stderr)

    def test_apply_keeps_the_batch_when_one_binding_broke_while_the_grader_ran(self):
        plan = json.loads(self.run_index("--plan").stdout)
        results = [{"collection": entry["collection"], "key": entry["key"], "rev": entry["rev"],
                    "facts": {"seen": True}, "gaps": []}
                   for group in plan for entry in group["entries"]]
        self.break_one_anchor()
        path = os.path.join(self.root, "results.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(results, handle)
        done = self.run_index("--apply", path)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("skipped entities/offer", done.stderr)
        index = kk.load_index(self.root)
        self.assertEqual(sorted(index["actions"]), ["broker.accept_offer",
                                                    "developer.create_offer"])
        self.assertNotIn("offer", index.get("entities", {}),
                         "the entry could not be resolved, so nothing about it was recorded")

    def test_apply_reports_the_skip_through_the_module_api_too(self):
        skipped = []
        self.break_one_anchor()
        kk.apply_results(self.root, self.contract(self.root), kk.load_index(self.root),
                         [{"collection": "entities", "key": "offer", "rev": "a" * 12,
                           "facts": {}, "gaps": []}], skipped)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0][0], "entities/offer")
        self.assertIn("no anchor", skipped[0][1])


class ScreenReachabilityTest(unittest.TestCase):
    """The design's sentence is "reached by some actor and launches some action" — both halves."""

    def messages(self, index, screens):
        return [f"{where}: {message}" for where, message in kk.cross_check(index, screens)]

    def test_a_live_screen_reached_only_by_an_actorless_action_is_reported(self):
        index = index_of(
            actors={"developer": {"kind": "role", "actions": ["developer.create_offer"]}},
            actions={"developer.create_offer": {"actor": "developer", "screens": ["S1"]},
                     "unknown.publish": {"screens": ["S2"]}},
        )
        found = self.messages(index, {"S1": "implemented", "S2": "implemented"})
        self.assertIn("screens/S2: on the map, but no action launched from it names an actor — "
                      "nothing says who reaches it", found)
        self.assertNotIn("screens/S1: on the map, and no action is launched from it", found)

    def test_a_screens_entry_naming_an_id_the_map_does_not_have_is_reported(self):
        index = index_of(actions={"developer.create_offer": {"actor": "developer",
                                                             "screens": ["S1"]}},
                         screens={"home": {"screen": "S9"}})
        self.assertIn("screens/home: describes S9, which is not on the screen map",
                      self.messages(index, {"S1": "implemented"}))

    def test_a_screens_entry_naming_no_id_at_all_is_reported(self):
        index = index_of(actions={"developer.create_offer": {"actor": "developer",
                                                             "screens": ["S1"]}},
                         screens={"home": {"purpose": "the first thing you see"}})
        self.assertIn("screens/home: names no screen id — an entry here describes one card on the "
                      "map, and the map is the authority",
                      self.messages(index, {"S1": "implemented"}))

    def test_a_screens_entry_that_matches_the_map_is_silent(self):
        index = index_of(actions={"developer.create_offer": {"actor": "developer",
                                                             "screens": ["S1"]}},
                         screens={"home": {"screen": "S1"}})
        self.assertEqual([m for m in self.messages(index, {"S1": "implemented"})
                          if m.startswith("screens/")], [])


class NamedScreenMapTest(ProjectMixin, unittest.TestCase):
    """A map the manifest names and does not have used to disable the check in silence."""

    def test_the_named_path_is_reported_even_when_it_is_gone(self):
        root = self.make_project()
        self.write(root, kk.MANIFEST_PATH, "sources:\n  screens: product/map.js\n")
        self.assertEqual(kk.named_screen_map(root), "product/map.js")
        self.assertIsNone(kk.screen_map_path(root),
                          "nothing else on disk, so there is no map to fall back to")

    def test_a_project_that_names_no_map_names_none(self):
        root = self.make_project()
        self.write(root, kk.MANIFEST_PATH, "sources:\n  screens:\n")
        self.assertIsNone(kk.named_screen_map(root))


class EntryQuotingTest(unittest.TestCase):
    """`set_entries` writes into a file the owner maintains, so it uses the writer's own rule.

    The duplicate it replaced called a value plain whenever it held no ` #`, while the reader cuts
    a comment after a tab too — so a heading with a tab before a `#` was written unquoted and read
    back truncated, silently corrupting the contract.
    """

    CONTRACT = ("version: 1\n\ncollections:\n  actions:\n    status: filled\n"
                "    sources:\n      - docs/*.md\n    criterion: who and what\n")

    def round_trip(self, at):
        text = set_entries(self.CONTRACT, "actions", {"a.b": at})
        return kit_yaml.load(text)["collections"]["actions"]["entries"]["a.b"]["at"]

    def test_a_binding_survives_whatever_is_in_the_heading(self):
        for at in ("docs/A.md#Plain heading",
                   "docs/A.md#Оффер от агентства",
                   "docs/A.md#Heading\t#tail",
                   "docs/A.md#Heading # tail",
                   "docs/A.md#kit:developer.create_offer",
                   "docs/A.md#It's mine"):
            with self.subTest(at=at):
                self.assertEqual(self.round_trip(at), at)

    def test_a_key_outside_the_plain_grammar_is_quoted(self):
        text = set_entries(self.CONTRACT, "actions", {"оффер от агентства": "docs/A.md#X"})
        self.assertEqual(list(kit_yaml.load(text)["collections"]["actions"]["entries"]),
                         ["оффер от агентства"])

if __name__ == "__main__":
    unittest.main()
