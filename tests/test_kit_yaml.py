#!/usr/bin/env python3
"""Tests for the kit's YAML-subset reader and writer.

Four layers live here:

* **unit** — every construct the subset admits, and one test per construct outside it, asserting
  the message *and* the line number: a reader that says "line 7: anchors are outside the subset"
  is the whole reason the kit is allowed to have its own parser instead of PyYAML.
* **round trip** — the two files this feature ships are read back and compared against what the
  files say. Everything the kit writes, the kit reads back identically; the check script's verdicts
  are worth nothing if the values it reasons over are not the ones on disk.
* **unit, the writer** — the values that read back as something other than themselves unless they
  are quoted. The index the writer produces is a cache keyed by hashes, so a value that changes on
  the way to disk is not a cosmetic problem: it is an entry that can never come clean again.
* **property-based** (fixed seed, stdlib `random`) — structures generated from the subset's own
  alphabet, asserting `load(dump(x)) == x`. The structure is built before it is written, so the
  generator is the oracle and never restates the writer's own choices.

Run directly (`python3 tests/test_kit_yaml.py`); `scripts/validate.sh` runs it the same way.
"""
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir))
sys.path.insert(0, os.path.join(REPO, "plugins", "agent-kit", "scripts"))

import kit_yaml  # noqa: E402  — the path above is what makes this importable from any cwd

TEMPLATE = os.path.join(REPO, "plugins", "agent-kit", "templates", "project", "contract.yml")
OWN_CONTRACT = os.path.join(REPO, ".agent-kit", "knowledge", "contract.yml")

# A failure has to be reproducible from the report alone, so the seed is fixed and printed.
SEED = 20260731


class SubsetTest(unittest.TestCase):
    """Everything the subset admits, because the kit's own files are written in it."""

    def test_nested_maps_by_indentation(self):
        self.assertEqual(kit_yaml.load("a:\n  b:\n    c: 1\n  d: 2\ne: 3\n"),
                         {"a": {"b": {"c": 1}, "d": 2}, "e": 3})

    def test_list_of_scalars_indented_under_its_key(self):
        self.assertEqual(kit_yaml.load("sources:\n  - one.md\n  - two.md\n"),
                         {"sources": ["one.md", "two.md"]})

    def test_list_of_scalars_at_its_key_own_indentation(self):
        """Legal YAML, and how a hand-edited file often comes back."""
        self.assertEqual(kit_yaml.load("sources:\n- one.md\n- two.md\nnext: 1\n"),
                         {"sources": ["one.md", "two.md"], "next": 1})

    def test_list_of_maps(self):
        text = "entries:\n  - id: a\n    status: filled\n  - id: b\n    status: empty\n"
        self.assertEqual(kit_yaml.load(text),
                         {"entries": [{"id": "a", "status": "filled"},
                                      {"id": "b", "status": "empty"}]})

    def test_plain_and_quoted_scalars(self):
        text = 'plain: some text\ndouble: "a\\tb"\nsingle: \'it\'\'s\'\nempty_quotes: ""\n'
        self.assertEqual(kit_yaml.load(text),
                         {"plain": "some text", "double": "a\tb", "single": "it's",
                          "empty_quotes": ""})

    def test_null_bool_int_float(self):
        text = ("a: null\nb: ~\nc: true\nd: False\ne: 42\nf: -7\ng: 1.5\nh: 1.5e3\n"
                "i: quoted-looking-number\n")
        self.assertEqual(kit_yaml.load(text),
                         {"a": None, "b": None, "c": True, "d": False, "e": 42, "f": -7,
                          "g": 1.5, "h": 1500.0, "i": "quoted-looking-number"})

    def test_a_key_with_nothing_after_it_is_null(self):
        """The template ships `source:` with no value; it must not read as the string ''."""
        self.assertEqual(kit_yaml.load("source:\nrev:\nnext: 1\n"),
                         {"source": None, "rev": None, "next": 1})

    def test_empty_flow_collections(self):
        self.assertEqual(kit_yaml.load("sources: []\nmapping: {}\n"),
                         {"sources": [], "mapping": {}})

    def test_comments_on_their_own_line_and_after_a_value(self):
        text = "# a whole-line comment\nstatus: filled  # and a trailing one\n\n# another\nn: 1\n"
        self.assertEqual(kit_yaml.load(text), {"status": "filled", "n": 1})

    def test_hash_inside_a_value_survives(self):
        """The case a naive comment stripper eats — and it eats the binding with it."""
        text = ("source: docs/developing.md#What must never end up in the plugin\n"
                "other: docs/developing.md#Releasing  # trailing comment, this one goes\n")
        self.assertEqual(kit_yaml.load(text),
                         {"source": "docs/developing.md#What must never end up in the plugin",
                          "other": "docs/developing.md#Releasing"})

    def test_hash_inside_quotes_is_not_a_comment(self):
        self.assertEqual(kit_yaml.load('a: "# not a comment"\nb: \'# nor this\'\n'),
                         {"a": "# not a comment", "b": "# nor this"})

    def test_literal_block_scalar(self):
        self.assertEqual(kit_yaml.load("text: |\n  one\n  two\nnext: 1\n"),
                         {"text": "one\ntwo\n", "next": 1})

    def test_literal_block_scalar_stripped(self):
        self.assertEqual(kit_yaml.load("text: |-\n  one\n  two\n"), {"text": "one\ntwo"})

    def test_folded_block_scalar(self):
        self.assertEqual(kit_yaml.load("text: >\n  one\n  two\n\n  three\n"),
                         {"text": "one two\nthree\n"})

    def test_folded_block_scalar_stripped(self):
        """`>-` is the form both shipped contracts use for a criterion or a reason."""
        self.assertEqual(kit_yaml.load("text: >-\n  one\n  two\n"), {"text": "one two"})

    def test_block_scalar_keeps_a_line_that_looks_like_a_comment(self):
        """Inside a block scalar there are no comments and no keys — it is all text."""
        self.assertEqual(kit_yaml.load("text: |\n  # not a comment\n  key: not a key\n"),
                         {"text": "# not a comment\nkey: not a key\n"})

    def test_a_number_with_a_leading_zero_is_a_string(self):
        """JSON's number grammar, and the reading a person expects: `007` is not seven.

        It is also mechanical. A section hash is twelve hex characters, and about one in sixteen
        hundred is all digits with a leading zero. Read as a number it comes back short — and a
        slot whose `rev` cannot survive being written down could never come clean again.
        """
        self.assertEqual(kit_yaml.load("rev: 007891234567\n"), {"rev": "007891234567"})
        self.assertEqual(kit_yaml.load("rev: 123456789012\n"), {"rev": 123456789012})
        self.assertEqual(kit_yaml.load("a: 0\nb: 12\nc: -3\nd: 0.5\n"),
                         {"a": 0, "b": 12, "c": -3, "d": 0.5})

    def test_keep_chomping_is_refused_by_name(self):
        """`|+` would be read as clip, which is a wrong value rather than a missing one."""
        with self.assertRaises(kit_yaml.KitYamlError) as caught:
            kit_yaml.load("text: |+\n  one\n\nnext: 1\n")
        self.assertIn("keep chomping", str(caught.exception))
        self.assertEqual(caught.exception.line, 1)

    def test_a_document_with_nothing_in_it(self):
        self.assertIsNone(kit_yaml.load(""))
        self.assertIsNone(kit_yaml.load("# only a comment\n\n"))

    def test_load_path_reads_a_file(self):
        self.assertEqual(kit_yaml.load_path(TEMPLATE)["version"], 1)


class OutsideTheSubsetTest(unittest.TestCase):
    """One test per construct the reader refuses, on the message and on the line number.

    "Say so by name and line rather than guessing" is the settled decision this layer holds: a
    reader that swallows an anchor and returns a plausible dict is how a slot silently loses its
    binding.
    """

    def refuses(self, text, line, fragment):
        with self.assertRaises(kit_yaml.KitYamlError) as caught:
            kit_yaml.load(text)
        error = caught.exception
        self.assertEqual(error.line, line, f"wrong line for {fragment!r}: {error}")
        self.assertIn(fragment, error.message)
        self.assertIn(f"line {line}", str(error))
        return error

    def test_a_line_dedented_out_of_a_block_scalar(self):
        """The silent version of this is the worst outcome the reader has.

        One space short of its neighbours, a `status:` line is swallowed into the prose above it:
        the slot keeps the verdict the owner thought they had just changed, and `--check` reports
        the contract clean.
        """
        self.refuses("mvp_bounds:\n  status: not_applicable\n  reason: |\n    Some explanation.\n"
                     "   status: filled\n", 5, "indented less than the block scalar")

    def test_a_block_scalar_header_the_subset_does_not_cover(self):
        """`|2` is a legal explicit indentation indicator — and reading it as the string `"|2"`
        is exactly the guess the reader exists not to make."""
        self.refuses("foo: |2\n  text\n", 1, "block scalar header")

    def test_an_unknown_escape_in_a_double_quoted_scalar(self):
        r"""Dropping the backslash turns `"C:\Users"` into `C:Users` without a word."""
        self.refuses('k: "C:\\Users\\name"\n', 1, "unknown escape")

    def test_anchor(self):
        self.refuses("version: 1\nbase: &defaults\n  a: 1\n", 2, "anchors")

    def test_alias(self):
        self.refuses("version: 1\na: 1\nb: *defaults\n", 3, "aliases")

    def test_tag(self):
        self.refuses("a: !!str 1\n", 1, "tags")

    def test_non_empty_flow_sequence(self):
        self.refuses("version: 1\nslots: [a, b]\n", 2, "flow collections")

    def test_non_empty_flow_mapping(self):
        self.refuses("version: 1\nslots: {a: 1}\n", 2, "flow collections")

    def test_tab_used_for_indentation(self):
        self.refuses("a:\n\tb: 1\n", 2, "tab used for indentation")

    def test_multiple_documents(self):
        self.refuses("a: 1\n---\nb: 2\n", 2, "multiple documents")

    def test_duplicate_key(self):
        self.refuses("a: 1\nb: 2\na: 3\n", 3, "duplicate key 'a'")

    def test_unterminated_double_quote(self):
        self.refuses('a: "unterminated\n', 1, "unterminated double-quoted scalar")

    def test_unterminated_single_quote(self):
        self.refuses("a: 'unterminated\n", 1, "unterminated single-quoted scalar")

    def test_document_starting_indented(self):
        self.refuses("  a: 1\n", 1, "indented line")

    def test_list_item_where_a_key_was_expected(self):
        self.refuses("a: 1\n- x\n", 2, "list item")

    def test_unexpected_indentation(self):
        self.refuses("a: 1\n   b: 2\n", 2, "unexpected indentation")

    def test_a_line_that_is_not_a_key_at_all(self):
        self.refuses("a: 1\njust some prose\n", 2, "expected `key: value`")


class RoundTripTest(unittest.TestCase):
    """The two files this feature ships, read back and compared with what they say.

    These are not smoke tests: the check script's every verdict is computed from these values, so
    a reader that quietly turns `status: filled` into something else would make the whole audit
    agree with itself and disagree with the file.
    """

    @classmethod
    def setUpClass(cls):
        cls.template = kit_yaml.load_path(TEMPLATE)
        cls.own = kit_yaml.load_path(OWN_CONTRACT)

    def test_template_shape(self):
        self.assertEqual(self.template["version"], 1)
        self.assertEqual(list(self.template["slots"]),
                         ["north_star", "architecture_stance", "verification", "mvp_bounds",
                          "scenarios", "deferred_seams"])
        self.assertEqual(list(self.template["collections"]),
                         ["actors", "entities", "actions", "screens", "integrations"])

    def test_template_ships_every_slot_empty(self):
        for kind in ("slots", "collections"):
            for name, slot in self.template[kind].items():
                with self.subTest(slot=f"{kind}/{name}"):
                    self.assertEqual(slot["status"], "empty")

    def test_template_collections_carry_an_empty_source_list(self):
        for name, slot in self.template["collections"].items():
            with self.subTest(slot=name):
                self.assertEqual(slot["sources"], [])

    def test_template_verification_has_a_commands_key_and_no_commands(self):
        """The key is there with only comments under it, so an owner fills in place."""
        verification = self.template["slots"]["verification"]
        self.assertIn("commands", verification)
        self.assertIsNone(verification["commands"])
        self.assertEqual(verification["criterion"],
                         "every command runs from the project root and exits 0")

    def test_own_contract_statuses(self):
        self.assertEqual(self.own["version"], 1)
        self.assertEqual({name: slot["status"] for name, slot in self.own["slots"].items()},
                         {"north_star": "open_question", "architecture_stance": "filled",
                          "verification": "filled", "mvp_bounds": "not_applicable",
                          "scenarios": "not_applicable", "deferred_seams": "not_applicable"})
        self.assertEqual({name: slot["status"] for name, slot in self.own["collections"].items()},
                         {"actors": "not_applicable", "entities": "not_applicable",
                          "actions": "not_applicable", "screens": "not_applicable",
                          "integrations": "filled"})

    def test_own_contract_binding_survives_the_hash_in_it(self):
        stance = self.own["slots"]["architecture_stance"]
        self.assertEqual(stance["source"], "docs/developing.md#What must never end up in the plugin")
        self.assertRegex(stance["rev"], r"^[0-9a-f]{12}$")

    def test_own_contract_commands_map(self):
        self.assertEqual(self.own["slots"]["verification"]["commands"],
                         {"validate": "scripts/validate.sh"})

    def test_own_contract_collection_sources(self):
        self.assertEqual(self.own["collections"]["integrations"]["sources"],
                         ["plugins/agent-kit/README.md"])

    def test_folded_prose_comes_back_as_one_line(self):
        """Both files write criteria and reasons with `>-`; folding them is the reader's job."""
        for kind in ("slots", "collections"):
            for name, slot in self.own[kind].items():
                for key in ("criterion", "reason"):
                    value = slot.get(key)
                    if value is None:
                        continue
                    with self.subTest(slot=f"{kind}/{name}", key=key):
                        self.assertIsInstance(value, str)
                        self.assertNotIn("\n", value)
                        self.assertTrue(value.strip())


class WriterTest(unittest.TestCase):
    """`dump`, and the values that would come back as something other than themselves.

    The writer's only customer is a machine-owned file — the derived index — and that file is a
    cache keyed by section hashes. A hash written down as a number, or a gap whose leading `#` is
    eaten as a comment, is not a cosmetic problem: it is an entry that never matches itself again.
    """

    def round_trip(self, value):
        text = kit_yaml.dump({"k": value})
        self.assertTrue(text.endswith("\n"), f"a file ends with a newline: {text!r}")
        return kit_yaml.load(text)["k"]

    def test_the_scalars_a_reader_would_otherwise_take_for_something_else(self):
        for value in ("true", "True", "false", "null", "~", "123", "-7", "1.5", "",
                      "#a leading hash", "a trailing # comment", "  ", " leading space",
                      "trailing space ", "a line\nand another", "[]", "{}", "- a dash",
                      "yes", "0", "'single'", '"double"'):
            with self.subTest(value=value):
                self.assertEqual(self.round_trip(value), value)

    def test_a_hash_that_is_all_digits_survives_being_written_down(self):
        """The case the reader is already careful about, from the other side.

        About one section hash in two hundred is all digits. Written plain it reads back as an int
        and can never equal its own hexdigest, so the entry it belongs to is stale for ever.
        """
        for rev in ("007891234567", "123456789012", "031657175672"):
            with self.subTest(rev=rev):
                self.assertEqual(self.round_trip(rev), rev)
                self.assertIsInstance(self.round_trip(rev), str)

    def test_a_value_holding_both_a_quote_and_a_comment_opener(self):
        """Exactly why single quotes are tried before double.

        The reader cannot tell an escaped `"` inside a double-quoted scalar from the closing one,
        so it thinks the scalar ended and reads the ` #` after it as a comment. Single quotes have
        no escapes to be confused by.
        """
        value = 'he said "ok". # and then left'
        self.assertEqual(self.round_trip(value), value)
        hand_written = 'k: "{}"\n'.format(value.replace('"', '\\"'))
        with self.assertRaises(kit_yaml.KitYamlError):
            kit_yaml.load(hand_written)

    def test_a_value_the_subset_cannot_hold_is_refused_by_name(self):
        """A silently wrong file is the one outcome the writer may not produce.

        By name, not just by refusing: the caller has to be able to say which value it was, and
        `str()`-ing the thing into the file would give a document that reads back as prose.
        """
        for value, named in (({1, 2}, "set"), (object(), "object"), ((1, 2), "tuple"),
                             (b"bytes", "bytes")):
            with self.subTest(value=repr(value)):
                with self.assertRaises(kit_yaml.KitYamlError) as caught:
                    kit_yaml.dump({"k": value})
                self.assertIn(f"{named} is outside the subset", str(caught.exception))

    def test_a_float_with_no_plain_form_in_the_subset_is_refused(self):
        """`1e+20` and `inf` are legal Python and outside the numbers this reader accepts."""
        for value in (float("inf"), float("nan"), 1e20, 1e-5):
            with self.subTest(value=repr(value)):
                with self.assertRaises(kit_yaml.KitYamlError) as caught:
                    kit_yaml.dump({"k": value})
                self.assertIn("has no plain form in the subset", str(caught.exception))

    def test_a_key_that_is_not_a_string_is_refused(self):
        with self.assertRaises(kit_yaml.KitYamlError) as caught:
            kit_yaml.dump({1: "a"})
        self.assertIn("a key must be a string", str(caught.exception))

    def test_a_key_the_reader_could_not_take_back_is_refused_not_written(self):
        """The proof-by-reading-it-back at the end of `dump`, doing its job."""
        with self.assertRaises(kit_yaml.KitYamlError):
            kit_yaml.dump({'a "quoted" key': "x"})

    def test_a_document_that_is_not_a_mapping_is_refused(self):
        for data in ([1, 2], "text", None, 7):
            with self.subTest(data=data):
                with self.assertRaises(kit_yaml.KitYamlError) as caught:
                    kit_yaml.dump(data)
                self.assertIn("mapping at the top level", str(caught.exception))

    def test_empty_collections_are_written_inline(self):
        self.assertEqual(kit_yaml.dump({"sources": [], "facts": {}}),
                         "sources: []\nfacts: {}\n")
        self.assertEqual(kit_yaml.load("sources: []\nfacts: {}\n"),
                         {"sources": [], "facts": {}})

    def test_a_document_with_no_keys_in_it_is_refused(self):
        """The reader gives back `None` for an empty file, so an empty mapping has no rendering.

        It is refused rather than written as a blank file that would read back as nothing. Every
        document the kit writes carries at least `version`, so this is a limit, not a gap.
        """
        with self.assertRaises(kit_yaml.KitYamlError):
            kit_yaml.dump({})

    def test_null_is_written_as_a_bare_key(self):
        self.assertEqual(kit_yaml.dump({"reason": None}), "reason:\n")
        self.assertIsNone(kit_yaml.load(kit_yaml.dump({"reason": None}))["reason"])

    def test_nesting_is_two_spaces_per_level_and_a_list_is_indented_under_its_key(self):
        text = kit_yaml.dump({"actions": {"a.b": {"facts": {"reads": ["lot", "request"]}}}})
        self.assertEqual(text, "actions:\n  a.b:\n    facts:\n      reads:\n"
                               "        - lot\n        - request\n")

    def test_a_list_of_maps_comes_back_as_a_list_of_maps(self):
        data = {"entries": [{"id": "a", "gaps": []}, {"id": "b", "gaps": ["one"]}]}
        self.assertEqual(kit_yaml.load(kit_yaml.dump(data)), data)

    def test_non_ascii_keys_and_values_survive(self):
        data = {"сущности": {"оффер": {"states": ["ожидает", "принят"]}}}
        self.assertEqual(kit_yaml.load(kit_yaml.dump(data)), data)

    def test_plain_is_preferred_where_it_reads_back_unchanged(self):
        """These files are read by people; quoting what needs no quotes is a cost with no payer."""
        text = kit_yaml.dump({"at": "docs/OFFERS.md#kit:developer.create_offer",
                              "line": 47, "rev": "a3f1c9d4e2b1", "actor": "developer"})
        self.assertEqual(text, "at: docs/OFFERS.md#kit:developer.create_offer\n"
                               "line: 47\nrev: a3f1c9d4e2b1\nactor: developer\n")


def generate_value(rng, depth=0):
    """A value drawn from the subset's own alphabet. The structure is the oracle."""
    scalars = [None, True, False, 0, 42, -7, 1000000, 1.5, -0.25,
               "plain text", "", "true", "007891234567", "123456789012", "#leading hash",
               "trailing # comment", " padded ", "a\nnewline", 'quote " and # hash',
               "Оффер от агентства", "docs/A.md#kit:developer.create_offer", "[]", "-"]
    shape = rng.random()
    if depth >= 3 or shape < 0.55:
        return rng.choice(scalars)
    if shape < 0.8:
        return [generate_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    return generate_map(rng, depth + 1)


def generate_map(rng, depth=0):
    keys = ["version", "actions", "a.b", "developer.create_offer", "123", "kind", "штука",
            "with space", "S12", "_private", "-dash"]
    return {key: generate_value(rng, depth)
            for key in rng.sample(keys, rng.randint(0, min(4, len(keys))))}


def generate_document(rng):
    """A whole document: a mapping with at least one key, because that is what a file holds."""
    while True:
        data = generate_map(rng)
        if data:
            return data


class WriterRoundTripPropertyTest(unittest.TestCase):
    """`load(dump(x)) == x` over generated structures.

    Generating the structure first and writing it second is what makes this a property and not a
    restatement: nothing here knows or cares which quoting the writer picked, only that the value
    that went in is the value that comes out.
    """

    STRUCTURES = 200

    def test_every_generated_structure_survives_the_round_trip(self):
        rng = random.Random(SEED)
        for number in range(self.STRUCTURES):
            data = generate_document(rng)
            with self.subTest(seed=SEED, structure=number):
                text = kit_yaml.dump(data)
                self.assertEqual(kit_yaml.load(text), data,
                                 f"seed {SEED}, structure {number}\n{data!r}\n--- written ---\n"
                                 f"{text}")

    def test_dumping_twice_produces_the_same_bytes(self):
        """A derived file that is committed must not churn a diff on a run that changed nothing."""
        rng = random.Random(SEED + 1)
        for number in range(self.STRUCTURES):
            data = generate_document(rng)
            with self.subTest(seed=SEED + 1, structure=number):
                once = kit_yaml.dump(data)
                self.assertEqual(kit_yaml.dump(kit_yaml.load(once)), once)


if __name__ == "__main__":
    unittest.main()
