import glob
import os
import sys
import textwrap
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "plugins", "agent-kit", "scripts")
sys.path.insert(0, SCRIPTS)

import kit_yaml  # noqa: E402


def load(text):
    return kit_yaml.load(textwrap.dedent(text), "<test>")


class ScalarTests(unittest.TestCase):
    def test_plain_scalars(self):
        data = load(
            """
            a: hello world
            b: 42
            c: -7
            d: null
            e: ~
            f:
            g: true
            h: false
            """
        )
        self.assertEqual(
            data,
            {"a": "hello world", "b": 42, "c": -7, "d": None, "e": None, "f": None, "g": True, "h": False},
        )

    def test_quoted_scalars(self):
        data = load(
            """
            a: "hello # not a comment"
            b: 'it''s quoted'
            c: "escaped \\"quote\\""
            """
        )
        self.assertEqual(
            data,
            {"a": "hello # not a comment", "b": "it's quoted", "c": 'escaped "quote"'},
        )

    def test_comments_and_blank_lines(self):
        data = load(
            """
            # a full-line comment

            a: value  # a trailing comment
            """
        )
        self.assertEqual(data, {"a": "value"})


class BlockTests(unittest.TestCase):
    def test_nested_map(self):
        data = load(
            """
            slots:
              north_star:
                status: empty
                reason: null
            """
        )
        self.assertEqual(data, {"slots": {"north_star": {"status": "empty", "reason": None}}})

    def test_block_list_of_scalars(self):
        data = load(
            """
            commands:
              - scripts/validate.sh
              - "python3 -m unittest"
            """
        )
        self.assertEqual(data, {"commands": ["scripts/validate.sh", "python3 -m unittest"]})

    def test_list_nested_under_map_key(self):
        data = load(
            """
            verification:
              status: filled
              commands:
                - a
                - b
            """
        )
        self.assertEqual(data, {"verification": {"status": "filled", "commands": ["a", "b"]}})


class ErrorTests(unittest.TestCase):
    def test_tab_indentation_is_an_error(self):
        text = "a:\n\tb: 1\n"
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            kit_yaml.load(text, "<test>")
        self.assertIn("tab", str(ctx.exception))
        self.assertIn("<test>:2", str(ctx.exception))

    def test_flow_list_is_an_error(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load("a: [1, 2]\n")
        self.assertIn("flow collection", str(ctx.exception))

    def test_flow_map_is_an_error(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load("a: {b: 1}\n")
        self.assertIn("flow collection", str(ctx.exception))

    def test_block_scalar_is_an_error(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load("a: |\n  text\n")
        self.assertIn("block scalar", str(ctx.exception))

    def test_anchor_is_an_error(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load("a: &anchor 1\n")
        self.assertIn("anchor", str(ctx.exception))

    def test_multiple_documents_is_an_error(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load("a: 1\n---\nb: 2\n")
        self.assertIn("multiple documents", str(ctx.exception))

    def test_error_names_the_line(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load(
                """
                a: 1
                b: [2]
                """
            )
        self.assertIn(":3:", str(ctx.exception))


class RevScalarTests(unittest.TestCase):
    """A rev is a 12-hex-digit hash and must survive the reader as a string."""

    def test_all_digit_rev_with_leading_zero_stays_a_string(self):
        # Read as an int this comes back as 31657175672, and the slot it belongs
        # to could never match its own hash again.
        data = load(
            """
            rev: 031657175672
            """
        )
        self.assertEqual(data["rev"], "031657175672")

    def test_ordinary_integers_are_still_integers(self):
        data = load(
            """
            a: 0
            b: 42
            c: -7
            """
        )
        self.assertEqual(data, {"a": 0, "b": 42, "c": -7})


class EscapeTests(unittest.TestCase):
    def test_escaped_backslash_before_n_is_not_a_newline(self):
        # Source characters: backslash backslash n — an escaped backslash then a
        # literal n. Sequential str.replace would turn this into a newline.
        data = load(
            """
            a: "x\\\\ny"
            """
        )
        self.assertEqual(data["a"], "x\\ny")

    def test_known_escapes(self):
        data = load(
            """
            a: "one\\ntwo"
            b: "a\\tb"
            c: "say \\"hi\\""
            """
        )
        self.assertEqual(data["a"], "one\ntwo")
        self.assertEqual(data["b"], "a\tb")
        self.assertEqual(data["c"], 'say "hi"')

    def test_unsupported_escape_is_named_not_guessed(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load(
                """
                a: "C:\\Users"
                """
            )
        self.assertIn("unsupported escape", str(ctx.exception))


class ListOfMapsTests(unittest.TestCase):
    def test_list_of_maps_names_the_construct(self):
        with self.assertRaises(kit_yaml.KitYamlError) as ctx:
            load(
                """
                items:
                  - key: value
                    other: value
                """
            )
        self.assertIn("list items that are maps are not supported", str(ctx.exception))

    def test_quoted_scalar_containing_a_colon_is_still_a_scalar(self):
        data = load(
            """
            items:
              - "key: value"
            """
        )
        self.assertEqual(data["items"], ["key: value"])


class RoundTripTests(unittest.TestCase):
    """Every YAML file the kit owns must parse without hitting the unsupported path."""

    def _files(self):
        return [
            os.path.join(REPO, "plugins", "agent-kit", "templates", "project", "manifest.yml"),
            os.path.join(REPO, "plugins", "agent-kit", "templates", "project", "contract.yml"),
            os.path.join(REPO, ".agent-kit", "project", "manifest.yml"),
            os.path.join(REPO, ".agent-kit", "knowledge", "contract.yml"),
        ]

    def test_reads_back_every_yaml_file_the_kit_owns(self):
        files = self._files()
        for path in files:
            # Asserted, not filtered: skipping the ones that are missing would let
            # the file this covers disappear and the test still pass.
            self.assertTrue(os.path.isfile(path), "kit-owned YAML file is missing: {}".format(path))
        for path in files:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            with self.subTest(path=path):
                data = kit_yaml.load(text, path)
                self.assertIsInstance(data, dict)

    def test_reads_back_every_fixture_contract(self):
        fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
        for path in sorted(glob.glob(os.path.join(fixtures_dir, "*", ".agent-kit", "knowledge", "contract.yml"))):
            if "unparseable" in path:
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            with self.subTest(path=path):
                data = kit_yaml.load(text, path)
                self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()
