"""The knowledge check, against documents built to fail it.

    python3 -m unittest discover -s tests

A check that reports nothing is indistinguishable from a check that finds nothing, so every rule
here is shown failing on a document that breaks it and silent on one that does not.
"""

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check", ROOT / "plugins" / "agent-kit" / "scripts" / "check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

ACTORS = """<!--
fields: How they appear, What they can do
-->
# Actors

### A guest
`key: guest`

**How they appear:** opens the site
**What they can do:** read the feed
"""

ACTIONS = """<!--
fields: Who, What happens, Can go wrong
-->
# Actions

### Guest reads the feed
`key: guest.browse_feed` · `state: built`

**Who:** guest
**What happens:** the feed is rendered, newest first
**Can go wrong:** nothing that matters
"""

MANIFEST = "knowledge:\n" + "".join(f"  {slot}: filled\n" for slot in check.SLOTS)


class CheckCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "proj"
        (self.root / "docs" / "knowledge").mkdir(parents=True)
        (self.root / ".agent-kit").mkdir()
        self.write("actors.md", ACTORS)
        self.write("actions.md", ACTIONS)
        (self.root / ".agent-kit" / "project.yml").write_text(MANIFEST, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        (self.root / "docs" / "knowledge" / name).write_text(text, encoding="utf-8")

    def run_check(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main([str(self.root), "--offline", *args])
        return code, out.getvalue()

    # ---- the baseline has to be silent, or nothing below means anything -----------------------

    def test_clean_knowledge_says_nothing(self):
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_status_prints_the_standing_even_when_clean(self):
        code, output = self.run_check("--status")
        self.assertEqual(code, 0)
        self.assertIn("built: 1", output)

    # ---- one rule at a time --------------------------------------------------------------------

    def test_an_empty_field_is_a_finding(self):
        self.write("actions.md", ACTIONS.replace("**What happens:** the feed is rendered, newest first",
                                                 "**What happens:**"))
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Fields", output)
        self.assertIn("What happens", output)

    def test_a_field_answered_by_a_list_below_it_is_filled(self):
        self.write("actions.md", ACTIONS.replace(
            "**What happens:** the feed is rendered, newest first",
            "**What happens:**\n1. the feed is rendered\n2. newest first"))
        code, output = self.run_check()
        self.assertEqual(code, 0, output)

    def test_an_action_whose_actor_does_not_exist(self):
        self.write("actions.md", ACTIONS.replace("guest.browse_feed", "ghost.browse_feed"))
        _code, output = self.run_check()
        self.assertIn("no actor 'ghost'", output)

    def test_a_key_named_but_never_defined(self):
        self.write("actions.md", ACTIONS.replace("**Can go wrong:** nothing that matters",
                                                 "**Can go wrong:** falls back to `screen.missing`"))
        _code, output = self.run_check()
        self.assertIn("screen.missing is not defined", output)

    def test_prose_with_a_dot_in_it_is_not_mistaken_for_a_key(self):
        self.write("actions.md", ACTIONS.replace(
            "**Can go wrong:** nothing that matters",
            "**Can go wrong:** nothing — see `config.languages` and `post-card.blade`"))
        code, output = self.run_check()
        self.assertEqual(code, 0, output)

    def test_an_actor_nobody_acts_for(self):
        self.write("actors.md", ACTORS + "\n### A ghost\n`key: ghost`\n\n"
                                         "**How they appear:** never\n**What they can do:** nothing\n")
        _code, output = self.run_check()
        self.assertIn("no action belongs to this actor", output)

    def test_a_slot_with_no_verdict(self):
        (self.root / ".agent-kit" / "project.yml").write_text("knowledge:\n  actors: filled\n",
                                                              encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("no verdict", output)

    def test_an_open_question_is_reported(self):
        (self.root / ".agent-kit" / "project.yml").write_text(
            MANIFEST.replace("scenarios: filled", "scenarios: open_question — no one has walked them"),
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("scenarios — open question", output)

    # ---- the hash both sides have to agree on --------------------------------------------------

    def test_a_source_is_clean_at_the_hash_this_program_prints(self):
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            check.main([str(self.root), "--hash", "idea.md", "Idea"])
        recorded = out.getvalue().strip()
        self.write("product.md", f"# Product\n\n`source: idea.md#Idea @{recorded}`\n")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)

    def test_a_source_that_moved_on_is_reported(self):
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        self.write("product.md", "# Product\n\n`source: idea.md#Idea @deadbeef`\n")
        _code, output = self.run_check()
        self.assertIn("changed", output)

    def test_a_source_pointing_at_nothing(self):
        self.write("product.md", "# Product\n\n`source: gone.md#Idea @deadbeef`\n")
        _code, output = self.run_check()
        self.assertIn("does not exist", output)

    def test_whitespace_at_the_end_of_a_line_does_not_move_the_hash(self):
        self.assertEqual(check.digest("a\nb\n"), check.digest("a   \nb\t\n"))

    # ---- notes -------------------------------------------------------------------------------

    def test_an_open_assumption_is_listed(self):
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Open notes", output)
        self.assertIn("assumed", output)

    # ---- a project with no blueprint at all ----------------------------------------------------

    def test_a_project_without_knowledge_is_not_a_failure(self):
        shutil.rmtree(self.root / "docs" / "knowledge")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main()
