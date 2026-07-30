#!/usr/bin/env python3
"""Tests for `/agent-kit:blueprint --check`.

Layers, and why each one is here:

* **unit** — the section resolver and the hash, the two pieces every other verdict is computed
  from.
* **property-based** (fixed seed, stdlib `random`) — documents generated from a small grammar of
  nested headings, asserting the invariant the design states: *a section's hash changes when and
  only when the text between its heading and its boundary changes.* The generator knows where each
  body truly is, so it is an oracle rather than a restatement of the implementation.
* **contract / end to end** — the script driven as a subprocess over checked-in fixture trees. The
  three exit codes are the agreement a later stage's gate is built on, so they are asserted from
  outside the process, on the reported message and not only on the number.
* **integration** — the stale/fresh distinction against a real file on disk in a temporary
  directory, because it depends on a live hash, and the verification commands by actually running
  them.

Every command any fixture names is trivial (`true`, `exit 3`, `sleep`). This repository's own
contract names `scripts/validate.sh`, which runs these tests: nothing here may ever run the
commands of the real contract, or the build would recurse. `check(root, run_commands=False)` is the
seam that keeps that honest, and it is asserted below.

Run directly (`python3 tests/test_blueprint_check.py`); `scripts/validate.sh` runs it the same way.
"""
import hashlib
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

import blueprint_check  # noqa: E402  — the path above is what makes this importable from any cwd
import kit_yaml  # noqa: E402

from blueprint_check import (COLLECTION_SLOTS, SINGULAR_SLOTS, SectionError, check,  # noqa: E402
                             headings, render, section_body, section_rev)

SCRIPT = os.path.join(REPO, "plugins", "agent-kit", "scripts", "blueprint_check.py")
FIXTURES = os.path.join(HERE, "fixtures")
TEMPLATE = os.path.join(REPO, "plugins", "agent-kit", "templates", "project", "contract.yml")
CONTRACT_PATH = os.path.join(".agent-kit", "knowledge", "contract.yml")

# A failure has to be reproducible from the report alone, so the seed is fixed and printed.
SEED = 20260731


# ------------------------------------------------------------------------------------------
# Helpers


class CheckMixin:
    def run_check(self, root, *args):
        """Drive the script the way the skill does: a subprocess, from the project root."""
        done = subprocess.run([sys.executable, SCRIPT, *args], cwd=root, capture_output=True,
                              text=True)
        # A crash is never an answer: the codes mean clean, findings, structural, and a traceback
        # on stderr with exit 1 would be read by a gate as "findings".
        self.assertNotIn("Traceback", done.stderr, f"the check crashed:\n{done.stderr}")
        return done

    def assertReports(self, output, *fragments):
        for fragment in fragments:
            self.assertIn(fragment, output)


def _scalar(value):
    """Render a value in the reader's subset, quoting what would otherwise change meaning."""
    if value is None:
        return ""
    text = str(value)
    unsafe = ("true", "false", "null", "~", "")
    if text in unsafe or text != text.strip() or " #" in text or text[:1] in "\"'[{&*!->|":
        return '"{}"'.format(text.replace('"', '\\"'))
    return text


def _emit(lines, key, value, indent):
    pad = " " * indent
    if isinstance(value, dict):
        lines.append(f"{pad}{key}:")
        for inner, item in value.items():
            _emit(lines, inner, item, indent + 2)
    elif isinstance(value, list):
        lines.append(f"{pad}{key}:")
        for item in value:
            lines.append(f"{pad}  - {_scalar(item)}")
    else:
        rendered = _scalar(value)
        lines.append(f"{pad}{key}: {rendered}".rstrip())


DEFAULT_SLOTS = {name: {"status": "open_question"} for name in SINGULAR_SLOTS}
DEFAULT_COLLECTIONS = {name: {"status": "not_applicable", "reason": "a fixture has no product"}
                       for name in COLLECTION_SLOTS}


def contract_text(slots=None, collections=None):
    """A whole contract, terminal everywhere unless a slot is overridden."""
    merged_slots = dict(DEFAULT_SLOTS)
    merged_slots.update(slots or {})
    merged_collections = dict(DEFAULT_COLLECTIONS)
    merged_collections.update(collections or {})
    lines = ["version: 1", "", "slots:"]
    for name, slot in merged_slots.items():
        _emit(lines, name, slot, 2)
    lines += ["", "collections:"]
    for name, slot in merged_collections.items():
        _emit(lines, name, slot, 2)
    return "\n".join(lines) + "\n"


class ContractWriterMixin:
    def write_contract(self, root, slots=None, collections=None):
        """Write a contract and prove the helper itself produced what it meant to."""
        text = contract_text(slots, collections)
        path = os.path.join(root, CONTRACT_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        parsed = kit_yaml.load(text)
        for name, slot in (slots or {}).items():
            self.assertEqual(parsed["slots"][name], slot, f"the test helper mangled {name}:\n{text}")
        for name, slot in (collections or {}).items():
            self.assertEqual(parsed["collections"][name], slot,
                             f"the test helper mangled {name}:\n{text}")
        return path


# ------------------------------------------------------------------------------------------
# Unit: the section resolver and the hash


class SectionResolverTest(unittest.TestCase):
    DOC = "\n".join([
        "# Handbook",
        "",
        "intro",
        "",
        "## Bound",
        "",
        "the answer",
        "",
        "### Nested",
        "",
        "a detail of the answer",
        "",
        "## Sibling",
        "",
        "not the answer",
        "",
    ])

    def test_headings_with_levels(self):
        self.assertEqual(headings(self.DOC),
                         [(1, "Handbook", 0), (2, "Bound", 4), (3, "Nested", 8),
                          (2, "Sibling", 12)])

    def test_a_hash_line_inside_a_code_fence_is_not_a_heading(self):
        text = "# Real\n\n```\n# Fake\n```\n\n~~~\n## Also fake\n~~~\n"
        self.assertEqual([title for _, title, _ in headings(text)], ["Real"])

    def test_a_hash_with_no_space_after_it_is_not_a_heading(self):
        self.assertEqual(headings("#nothashtag\n# Real\n"), [(1, "Real", 1)])

    def test_a_closing_hash_run_is_dropped_only_when_it_is_a_closing_sequence(self):
        """A binding names "the heading's literal text", and a heading may end in a `#`.

        Markdown's closing sequence has to be preceded by whitespace — `## Done ##` is titled
        "Done", and `## Why C#` is titled "Why C#". A slot bound to the second one has nowhere to
        resolve to, and the check calls a sound document a missing section.
        """
        self.assertEqual([title for _, title, _ in headings("## Done ##\n")], ["Done"])
        self.assertEqual([title for _, title, _ in headings("## Why C#\n")], ["Why C#"])

    def test_body_runs_to_the_next_heading_of_the_same_level(self):
        self.assertEqual(section_body(self.DOC, "Bound"),
                         "\nthe answer\n\n### Nested\n\na detail of the answer\n")
        self.assertEqual(section_body(self.DOC, "Sibling"), "\nnot the answer")

    def test_body_swallows_a_deeper_subsection(self):
        """"The next heading of the same level *or shallower*" — a nested `###` is inside."""
        body = section_body(self.DOC, "Bound")
        self.assertIn("### Nested", body)
        self.assertIn("a detail of the answer", body)
        self.assertNotIn("not the answer", body)

    def test_body_stops_at_a_shallower_heading(self):
        text = "# One\n\n## Two\n\n### Three\n\nthree body\n\n# Four\n\nfour body\n"
        self.assertEqual(section_body(text, "Three"), "\nthree body\n")

    def test_body_of_the_last_section_runs_to_the_end_of_the_file(self):
        self.assertEqual(section_body("# One\n\nlast\n", "One"), "\nlast")

    def test_a_fenced_heading_does_not_end_a_section(self):
        text = "# One\n\n```\n# Fake\n```\n\n# Two\n\nsecond\n"
        self.assertEqual(section_body(text, "One"), "\n```\n# Fake\n```\n")

    def test_missing_heading_raises(self):
        with self.assertRaises(SectionError) as caught:
            section_body(self.DOC, "Renamed")
        self.assertIn("no heading 'Renamed'", str(caught.exception))

    def test_ambiguous_heading_raises_and_names_both_lines(self):
        text = "# One\n\na\n\n# One\n\nb\n"
        with self.assertRaises(SectionError) as caught:
            section_body(text, "One")
        message = str(caught.exception)
        self.assertIn("not unique", message)
        self.assertIn("line 1", message)
        self.assertIn("line 5", message)

    def test_rev_is_twelve_hex_characters_of_the_body_sha256(self):
        body = section_body(self.DOC, "Bound")
        expected = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
        self.assertEqual(section_rev(self.DOC, "Bound"), expected)
        self.assertRegex(section_rev(self.DOC, "Bound"), r"^[0-9a-f]{12}$")

    def test_editing_a_nested_subsection_changes_the_hash(self):
        before = section_rev(self.DOC, "Bound")
        after = section_rev(self.DOC.replace("a detail of the answer", "a different detail"),
                            "Bound")
        self.assertNotEqual(before, after)

    def test_editing_a_sibling_section_does_not_change_the_hash(self):
        before = section_rev(self.DOC, "Bound")
        after = section_rev(self.DOC.replace("not the answer", "still not the answer"), "Bound")
        self.assertEqual(before, after)

    def test_editing_the_intro_above_the_section_does_not_change_the_hash(self):
        self.assertEqual(section_rev(self.DOC, "Bound"),
                         section_rev(self.DOC.replace("intro", "a new intro"), "Bound"))


# ------------------------------------------------------------------------------------------
# Property-based: the invariant the design states


def generate_document(rng):
    """A document from a small grammar. Returns (lines, sections).

    `sections` is the truth the generator knows and the resolver has to rediscover: a list of
    (level, title, heading line index).
    """
    lines, sections, level = [], [], 1
    for number in range(rng.randint(3, 7)):
        if sections:
            level = min(3, max(1, level + rng.choice((-1, 0, 0, 1))))
        title = f"Section {number}"
        sections.append((level, title, len(lines)))
        lines.append("#" * level + " " + title)
        for _ in range(rng.randint(0, 3)):
            shape = rng.choice(("prose", "blank", "item", "fence"))
            if shape == "prose":
                lines.append(rng.choice(("a claim", "another line of prose", "  indented prose")))
            elif shape == "blank":
                lines.append("")
            elif shape == "item":
                lines.append("- a list item")
            else:
                lines += ["```", "# not a heading — it is inside a fence", "```"]
    return lines, sections


def as_text(lines):
    """Join generated lines into a file.

    The trailing newline is not decoration: a file ends with one, and with it `splitlines()` is
    the exact inverse of this join — so the line numbers the oracle reasons about are the ones the
    resolver sees, including a blank last line.
    """
    return "\n".join(lines) + "\n"


def true_span(sections, index, total):
    """Where the body of `sections[index]` really is: (first line, one past the last)."""
    level, _, start = sections[index]
    for other_level, _, other_start in sections[index + 1:]:
        if other_level <= level:
            return start + 1, other_start
    return start + 1, total


class SectionHashPropertyTest(unittest.TestCase):
    DOCUMENTS = 60

    def documents(self):
        """The same corpus for every test here, and a separate stream for their own choices.

        Drawing the target section from the generator's own stream would make "document 12" name a
        different document in each test, which is exactly what a fixed seed is for.
        """
        corpus = random.Random(SEED)
        for number in range(self.DOCUMENTS):
            lines, sections = generate_document(corpus)
            yield number, random.Random(SEED + number), lines, sections

    def test_body_is_exactly_the_span_the_grammar_produced(self):
        for number, _, lines, sections in self.documents():
            text = as_text(lines)
            for index, (_, title, _) in enumerate(sections):
                start, end = true_span(sections, index, len(lines))
                with self.subTest(seed=SEED, document=number, section=title):
                    self.assertEqual(section_body(text, title), "\n".join(lines[start:end]),
                                     f"seed {SEED}, document {number}:\n{text}")

    def test_the_hash_changes_when_and_only_when_the_body_changes(self):
        for number, rng, lines, sections in self.documents():
            text = as_text(lines)
            index = rng.randrange(len(sections))
            level, title, heading_at = sections[index]
            start, end = true_span(sections, index, len(lines))
            before = section_rev(text, title)
            for line_number in range(len(lines)):
                if line_number == heading_at:
                    continue
                mutated = list(lines)
                mutated[line_number] += " (edited)"
                after = section_rev(as_text(mutated), title)
                inside = start <= line_number < end
                with self.subTest(seed=SEED, document=number, section=title, line=line_number,
                                  inside=inside):
                    detail = (f"seed {SEED}, document {number}, section {title!r} "
                              f"(level {level}, body lines {start}:{end}), edited line "
                              f"{line_number}: {lines[line_number]!r}\n{text}")
                    if inside:
                        self.assertNotEqual(before, after, "edit inside the section, hash unchanged"
                                                           f"\n{detail}")
                    else:
                        self.assertEqual(before, after, "edit outside the section, hash changed"
                                                        f"\n{detail}")

    def test_renaming_the_bound_heading_is_a_missing_section(self):
        for number, rng, lines, sections in self.documents():
            index = rng.randrange(len(sections))
            _, title, heading_at = sections[index]
            mutated = list(lines)
            mutated[heading_at] += " (renamed)"
            with self.subTest(seed=SEED, document=number, section=title):
                with self.assertRaises(SectionError):
                    section_rev(as_text(mutated), title)


# ------------------------------------------------------------------------------------------
# Contract / end to end: the three exit codes, driven as a subprocess


class ExitCodeTest(CheckMixin, ContractWriterMixin, unittest.TestCase):
    def fixture(self, name):
        return os.path.join(FIXTURES, name)

    def write_raw(self, root, text):
        path = os.path.join(root, CONTRACT_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_clean_contract_exits_zero_and_says_nothing_else(self):
        done = self.run_check(self.fixture("clean"), "--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertReports(done.stdout, "slots        3 filled", "collections  1 filled",
                           "verification ok: true → ok")
        self.assertNotIn("✗", done.stdout)
        self.assertNotIn("⚠", done.stdout)
        self.assertNotIn("stale", done.stdout)

    def test_a_bare_invocation_means_check(self):
        self.assertEqual(self.run_check(self.fixture("clean")).returncode, 0)

    def test_an_unknown_argument_is_refused(self):
        done = self.run_check(self.fixture("clean"), "--fix")
        self.assertEqual(done.returncode, 2)
        self.assertIn("usage:", done.stderr)

    def test_findings_exit_one_and_every_one_is_reported(self):
        done = self.run_check(self.fixture("findings"), "--check")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertReports(
            done.stdout,
            "⚠ slots/north_star",
            "empty is not a verdict",
            "⚠ slots/mvp_bounds",
            "conflicts is not a verdict",
            "⚠ slots/scenarios",
            "not_applicable with no reason",
            "⚠ slots/deferred_seams",
            "no slot recorded",
            "⚠ slots/moonshot",
            "not a slot this kit version knows",
            "⚠ slots/architecture_stance",
            "but never verified — record rev: 797d598271bf",
            "⚠ slots/verification",
            "names no commands",
            "⚠ collections/entities",
            "names no sources",
            "⚠ collections/actions",
            "unknown status 'todo'",
        )
        # One run shows everything wrong, not the first thing wrong.
        self.assertEqual(done.stdout.count("⚠"), 9, done.stdout)
        self.assertNotIn("✗", done.stdout)

    def test_a_missing_source_file_is_structural_and_outranks_a_finding(self):
        done = self.run_check(self.fixture("missing-source"), "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout,
                           "✗ slots/architecture_stance", "source file is gone: docs/gone.md",
                           "✗ slots/mvp_bounds", "names no section — the form is path#heading",
                           "⚠ slots/north_star")
        self.assertEqual(done.stdout.count("✗"), 2, done.stdout)

    def test_a_renamed_heading_is_a_missing_section(self):
        done = self.run_check(self.fixture("renamed-heading"), "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "✗ slots/architecture_stance",
                           "docs/handbook.md: no heading 'Boundaries'")

    def test_an_ambiguous_heading_is_structural(self):
        done = self.run_check(self.fixture("ambiguous-heading"), "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "✗ slots/architecture_stance",
                           "heading 'Boundaries' is not unique", "line 6", "line 14")

    def test_a_glob_matching_nothing_is_structural(self):
        done = self.run_check(self.fixture("missing-glob"), "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "✗ collections/integrations",
                           "source matches nothing: docs/integrations/*.md")

    def test_a_contract_outside_the_yaml_subset_is_structural(self):
        done = self.run_check(self.fixture("unparsable"), "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "✗ .agent-kit/knowledge/contract.yml",
                           "line 7: anchors are outside the subset",
                           "the kit reads a YAML subset and will not guess")

    def test_a_filled_slot_with_no_binding_at_all_is_a_finding(self):
        """Filled is a claim that an answer exists somewhere; unbound, it names nowhere."""
        with tempfile.TemporaryDirectory() as root:
            self.write_contract(root, slots={"mvp_bounds": {
                "status": "filled",
                "criterion": "an explicit in-list and an explicit out-list",
            }})
            done = self.run_check(root, "--check")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertReports(done.stdout, "⚠ slots/mvp_bounds",
                           "nothing says where the answer is — bind it with source: path#heading")

    def test_a_contract_that_is_not_a_mapping_is_structural(self):
        with tempfile.TemporaryDirectory() as root:
            self.write_raw(root, "- version: 1\n- slots: 2\n")
            done = self.run_check(root, "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "the contract is not a mapping")

    def test_a_slots_block_that_is_not_a_mapping_is_structural(self):
        with tempfile.TemporaryDirectory() as root:
            self.write_raw(root, "version: 1\nslots:\n  - north_star\ncollections: {}\n")
            done = self.run_check(root, "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "✗ slots", "`slots` is not a mapping of slot id to slot")

    def test_a_slot_that_is_not_a_mapping_is_structural(self):
        with tempfile.TemporaryDirectory() as root:
            self.write_raw(root, "version: 1\nslots:\n  north_star: filled\ncollections: {}\n")
            done = self.run_check(root, "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "✗ slots/north_star", "the slot is not a mapping")

    def test_no_contract_at_all_is_structural_and_names_the_template(self):
        done = self.run_check(self.fixture("no-contract"), "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "✗ .agent-kit/knowledge/contract.yml",
                           "no knowledge contract here",
                           os.path.join("templates", "project", "contract.yml"))


# ------------------------------------------------------------------------------------------
# Integration: staleness against a real file


class StalenessTest(CheckMixin, ContractWriterMixin, unittest.TestCase):
    """The feature's headline behaviour, and the one that needs a live hash.

    "Editing the section a slot binds to makes the next check report it stale and exit 1; editing
    a different section of the same file does not."
    """

    BOUND = "the original answer"
    OTHER = "the other section"

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "docs"))
        self.write_document(self.BOUND, self.OTHER)
        self.rev = section_rev(self.document(self.BOUND, self.OTHER), "Boundaries")
        self.write_contract(self.root, slots={"architecture_stance": {
            "status": "filled",
            "source": "docs/handbook.md#Boundaries",
            "rev": self.rev,
            "criterion": "the rules that decide where a change belongs",
        }})

    @staticmethod
    def document(bound, other):
        return "\n".join(["# Handbook", "", "## Boundaries", "", bound, "",
                          "## Verification", "", other, ""])

    def write_document(self, bound, other):
        with open(os.path.join(self.root, "docs", "handbook.md"), "w", encoding="utf-8") as handle:
            handle.write(self.document(bound, other))

    def test_a_matching_rev_is_clean(self):
        done = self.run_check(self.root, "--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("stale", done.stdout)

    def test_editing_the_bound_section_makes_the_slot_stale(self):
        self.write_document("the answer, rewritten", self.OTHER)
        expected = section_rev(self.document("the answer, rewritten", self.OTHER), "Boundaries")
        done = self.run_check(self.root, "--check")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertReports(done.stdout, "stale        slots/architecture_stance",
                           "docs/handbook.md#Boundaries changed since it was recorded",
                           f"({self.rev} → {expected})")

    def test_editing_a_different_section_of_the_same_file_does_not(self):
        self.write_document(self.BOUND, "the other section, rewritten")
        done = self.run_check(self.root, "--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("stale", done.stdout)

    def test_deleting_the_bound_heading_is_structural_not_stale(self):
        path = os.path.join(self.root, "docs", "handbook.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.document(self.BOUND, self.OTHER).replace("## Boundaries", "## Limits"))
        done = self.run_check(self.root, "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout, "no heading 'Boundaries'")


# ------------------------------------------------------------------------------------------
# Integration: the verification slot, proven by running it


class VerificationCommandTest(CheckMixin, ContractWriterMixin, unittest.TestCase):
    def test_a_failing_command_is_caught_by_running_it(self):
        done = self.run_check(os.path.join(FIXTURES, "failing-command"), "--check")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertReports(done.stdout,
                           "verification ok: true → ok",
                           "verification broken: echo boom >&2; exit 3 → FAILED",
                           "✗ slots/verification",
                           "exited 3",
                           "boom")

    def test_a_passing_command_is_clean(self):
        done = self.run_check(os.path.join(FIXTURES, "clean"), "--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertReports(done.stdout, "verification ok: true → ok")

    def test_run_commands_false_skips_them_entirely(self):
        """The seam CI covers this repository's own contract through, without recursing."""
        root = os.path.join(FIXTURES, "failing-command")
        self.assertEqual(check(root, run_commands=True).exit_code, 2)
        skipped = check(root, run_commands=False)
        self.assertEqual(skipped.commands, [])
        self.assertEqual(skipped.structural, [])
        self.assertEqual(skipped.exit_code, 0)

    def test_a_wedged_command_times_out_rather_than_hanging_the_gate(self):
        original = blueprint_check.COMMAND_TIMEOUT
        blueprint_check.COMMAND_TIMEOUT = 1
        self.addCleanup(setattr, blueprint_check, "COMMAND_TIMEOUT", original)
        with tempfile.TemporaryDirectory() as root:
            self.write_contract(root, slots={"verification": {
                "status": "filled",
                "commands": {"wedged": "sleep 30"},
            }})
            report = check(root)
        self.assertEqual(report.exit_code, 2)
        self.assertEqual(report.commands, [("wedged", "sleep 30", False)])
        self.assertIn("did not finish within 1s", render(report))

    def test_a_command_that_is_not_a_string_is_reported_not_crashed(self):
        """The template ships `commands:` with only comments under it.

        An owner who sets `status: filled`, writes a command name and leaves the value empty gets
        `{"test": None}` — and a crash is not one of the three answers this script is allowed to
        give. Whatever verdict that contract deserves, it has to be reported.
        """
        with tempfile.TemporaryDirectory() as root:
            self.write_contract(root, slots={"verification": {
                "status": "filled",
                "commands": {"test": None},
            }})
            done = self.run_check(root, "--check")
        self.assertNotEqual(done.returncode, 0, done.stdout)
        self.assertIn("verification", done.stdout)


# ------------------------------------------------------------------------------------------
# The template, and this repository's own contract


class TemplateTest(CheckMixin, unittest.TestCase):
    def test_the_template_slot_ids_are_exactly_the_list_in_the_code(self):
        """The template and the slot list are edited a commit apart; they may not drift."""
        template = kit_yaml.load_path(TEMPLATE)
        self.assertEqual(tuple(template["slots"]), SINGULAR_SLOTS)
        self.assertEqual(tuple(template["collections"]), COLLECTION_SLOTS)

    def test_a_project_with_only_the_template_needs_a_verdict_for_every_slot(self):
        with tempfile.TemporaryDirectory() as root:
            destination = os.path.join(root, CONTRACT_PATH)
            os.makedirs(os.path.dirname(destination))
            shutil.copyfile(TEMPLATE, destination)
            done = self.run_check(root, "--check")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        for name in SINGULAR_SLOTS:
            self.assertIn(f"⚠ slots/{name}", done.stdout)
        for name in COLLECTION_SLOTS:
            self.assertIn(f"⚠ collections/{name}", done.stdout)
        self.assertEqual(done.stdout.count("⚠"), len(SINGULAR_SLOTS) + len(COLLECTION_SLOTS))
        self.assertReports(done.stdout, "empty is not a verdict",
                           "slots        6 empty", "collections  5 empty")


class OwnContractTest(unittest.TestCase):
    """This repository's own contract, checked through the module API and never by running it.

    Its `verification` slot names `scripts/validate.sh`, which runs these tests. Running the
    commands here would recurse until something ran out, so this asserts the structural half only —
    and asserts that nothing was run, because that is the property the whole arrangement rests on.

    The guard is not left to the assertion: while this contract is checked, `subprocess.run` inside
    the module raises. A regression in the `run_commands` seam would otherwise not fail the suite,
    it would launch the suite again from inside itself.
    """

    @classmethod
    def setUpClass(cls):
        def refuse(*args, **kwargs):
            raise AssertionError("the check tried to run this repository's own verification "
                                 f"command ({args!r}); that command runs this suite")

        original = blueprint_check.subprocess.run
        blueprint_check.subprocess.run = refuse
        try:
            cls.report = check(REPO, run_commands=False)
        finally:
            blueprint_check.subprocess.run = original

    def test_no_command_was_run(self):
        self.assertEqual(self.report.commands, [])

    def test_the_contract_is_structurally_sound(self):
        self.assertEqual(self.report.structural, [], render(self.report))

    def test_every_slot_has_a_verdict_and_every_binding_is_fresh(self):
        self.assertEqual(self.report.findings, [], render(self.report))
        self.assertEqual(self.report.stale, [], render(self.report))
        self.assertEqual(self.report.exit_code, 0, render(self.report))

    def test_every_slot_this_kit_version_knows_is_accounted_for(self):
        self.assertEqual(sum(self.report.slot_counts.values()), len(SINGULAR_SLOTS))
        self.assertEqual(sum(self.report.collection_counts.values()), len(COLLECTION_SLOTS))
        self.assertNotIn("missing", self.report.slot_counts)
        self.assertNotIn("missing", self.report.collection_counts)

    def test_open_question_is_terminal_and_clean(self):
        """It is counted in the summary and never listed as a finding."""
        self.assertEqual(self.report.slot_counts.get("open_question"), 1)
        self.assertIn("1 open_question", render(self.report))
        self.assertEqual(self.report.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
