#!/usr/bin/env python3
"""Tests for the kit's YAML-subset reader.

Two layers live here:

* **unit** — every construct the subset admits, and one test per construct outside it, asserting
  the message *and* the line number: a reader that says "line 7: anchors are outside the subset"
  is the whole reason the kit is allowed to have its own parser instead of PyYAML.
* **round trip** — the two files this feature ships are read back and compared against what the
  files say. Everything the kit writes, the kit reads back identically; the check script's verdicts
  are worth nothing if the values it reasons over are not the ones on disk.

Run directly (`python3 tests/test_kit_yaml.py`); `scripts/validate.sh` runs it the same way.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, os.pardir))
sys.path.insert(0, os.path.join(REPO, "plugins", "agent-kit", "scripts"))

import kit_yaml  # noqa: E402  — the path above is what makes this importable from any cwd

TEMPLATE = os.path.join(REPO, "plugins", "agent-kit", "templates", "project", "contract.yml")
OWN_CONTRACT = os.path.join(REPO, ".agent-kit", "knowledge", "contract.yml")


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


if __name__ == "__main__":
    unittest.main()
