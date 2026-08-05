"""The knowledge check, against documents built to fail it.

    python3 -m unittest discover -s tests

A check that reports nothing is indistinguishable from a check that finds nothing, so every rule
here is shown failing on a document that breaks it and silent on one that does not.
"""

import contextlib
import importlib.util
import json
import io
import shutil
import subprocess
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

    # ---- promises the product does not keep ----------------------------------------------------

    MARKED = ("// agent-kit:unmet guest.browse_feed\n"
              "it('the feed is newest first')->todo();\n")

    def suite(self, body, form="->todo()", name="tests/FeedTest.php"):
        """A real git repository, because `git grep` is the path that runs in a real project."""
        manifest = MANIFEST + (f"tests:\n  unmet: {form}\n" if form else "")
        (self.root / ".agent-kit" / "project.yml").write_text(manifest, encoding="utf-8")
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        self.git("init", "-q")
        self.git("add", "-A")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=False)

    def test_a_marked_test_is_listed_with_its_entry_even_when_everything_else_is_clean(self):
        self.suite(self.MARKED)
        code, output = self.run_check()
        self.assertEqual(code, 0, output)          # a promise on record is not a defect in the check
        self.assertIn("Promises the product does not keep (1)", output)
        self.assertIn("tests/FeedTest.php:1 guest.browse_feed", output)
        self.assertIn("sprint with no theme", output)

    def test_a_file_named_in_the_project_language_is_read_like_any_other(self):
        self.suite(self.MARKED, name="tests/Лента.php")   # git ls-files would quote this away
        _code, output = self.run_check()
        self.assertIn("tests/Лента.php:1 guest.browse_feed", output)

    def test_the_mark_quoted_in_a_document_is_not_a_promise(self):
        self.suite(self.MARKED)
        (self.root / "docs" / "audits").mkdir(parents=True)
        (self.root / "docs" / "audits" / "tests.md").write_text(
            "- [ ] `guest.browse_feed` — see agent-kit:unmet guest.browse_feed in the suite\n",
            encoding="utf-8")
        self.git("add", "-A")
        _code, output = self.run_check()
        self.assertIn("Promises the product does not keep (1)", output)

    def test_a_mark_naming_an_entry_that_does_not_exist(self):
        self.suite("// agent-kit:unmet guest.gone\nit('x')->todo();\n")
        _code, output = self.run_check()
        self.assertIn("guest.gone — no such entry", output)

    def test_an_entry_key_without_a_dot_is_an_entry_too(self):
        self.suite("# agent-kit:unmet guest\ndef test_x(): ...\n")
        _code, output = self.run_check()
        self.assertIn("guest", output)
        self.assertNotIn("no such entry", output)

    def test_a_mark_without_an_entry_is_still_listed(self):
        self.suite("# agent-kit:unmet\ndef test_newest_first(): ...\n")
        _code, output = self.run_check()
        self.assertIn("no entry named", output)

    def test_several_suites_are_a_map_and_do_not_crash_the_check(self):
        self.suite(self.MARKED, form='\n    php: "->todo()"\n    js: test.failing')
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertIn("tests/FeedTest.php:1 guest.browse_feed", output)

    def test_a_suite_without_the_mark_says_nothing(self):
        self.suite("it('the feed is newest first');\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_mark_with_no_form_recorded_is_said_without_failing_the_check(self):
        self.suite(self.MARKED, form="")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)          # a run must not stop over a missing manifest key
        self.assertIn("no tests.unmet", output)

    def test_a_project_with_no_marks_is_never_nagged_about_the_form(self):
        self.suite("it('the feed is newest first');\n", form="")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_long_list_is_cut_to_a_glance(self):
        body = "".join(f"// agent-kit:unmet guest.browse_feed\nit('{i}')->todo();\n" for i in range(15))
        self.suite(body)
        _code, output = self.run_check()
        self.assertIn("Promises the product does not keep (15)", output)
        self.assertIn("and 5 more", output)
        self.assertEqual(output.count("guest.browse_feed"), 10)

    # ---- the debt ledger -----------------------------------------------------------------------

    def test_open_debt_is_listed_without_failing_the_check(self):
        (self.root / "docs" / "technical_debt.md").write_text(
            "# Долг\n\n"
            "- [ ] Закрепить инвариант «аккаунт всегда с паролем» — на нём держится правка · PR #21\n"
            "- [ ] Дописать прозу про передачу аккаунта · PR #21\n",
            encoding="utf-8")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)          # a project's own memory is not a defect
        self.assertIn("Debt (2)", output)
        self.assertIn("docs/technical_debt.md:3", output)

    def test_a_project_with_no_ledger_says_nothing_about_debt(self):
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertNotIn("Debt", output)

    def test_prose_around_the_items_is_not_counted(self):
        (self.root / "docs" / "technical_debt.md").write_text(
            "# Долг\n\nПишут прогоны, читают команды. Формат:\n\n"
            "```markdown\n- [ ] <что сделать> — <почему> · <прогон>\n```\n\n"
            "- [ ] Один настоящий пункт · PR #21\n",
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("Debt (1)", output)          # the example inside the fence is indented prose

    # ---- the state of the work -----------------------------------------------------------------

    def repo_with_work(self):
        (self.root / "docs" / "audits").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "audits" / "tests.md").write_text(
            "# Тесты — 2026-08-04\n\n- [ ] один пункт\n- [ ] второй\n", encoding="utf-8")
        runs = self.root / ".agent-kit" / "runs" / "2026-08-05-feed"
        runs.mkdir(parents=True)
        (runs / "run.json").write_text(json.dumps({
            "slug": "2026-08-05-feed", "command": "ship", "step": "build",
            "branch": "claude/feed", "waiting_on": None, "blockers": []}), encoding="utf-8")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
        self.git("branch", "claude/feed")

    def test_state_names_an_abandoned_run_and_the_audits(self):
        self.repo_with_work()
        _code, output = self.run_check("--state")
        self.assertIn("run 2026-08-05-feed left at step=build", output)
        self.assertIn("tests 2026-08-04 (2 open)", output)

    def test_a_finished_run_is_not_reported_as_left_behind(self):
        self.repo_with_work()
        path = self.root / ".agent-kit" / "runs" / "2026-08-05-feed" / "run.json"
        path.write_text(json.dumps({"slug": "2026-08-05-feed", "step": "done"}), encoding="utf-8")
        _code, output = self.run_check("--state")
        self.assertNotIn("left at step", output)

    def test_a_project_with_no_audits_says_so_rather_than_staying_silent(self):
        self.suite("it('x');\n")                       # suite() makes it a repository
        _code, output = self.run_check("--state")
        self.assertIn("audits: none has ever run", output)

    def test_state_survives_a_directory_that_is_not_a_repository(self):
        _code, output = self.run_check("--state")
        self.assertIn("no git repository here", output)      # docs still read

    # ---- hashes this program owns --------------------------------------------------------------

    def sourced_project(self, recorded):
        (self.root / "idea.md").write_text("# Idea\n\nWhat it is for.\n", encoding="utf-8")
        self.write("product.md", f"# Product\n\n`source: idea.md#Idea @{recorded}`\n")

    def test_a_hash_from_before_the_program_is_named_as_such_not_as_a_change(self):
        self.sourced_project("a3f1c9d")            # seven characters: nobody could have computed it
        _code, output = self.run_check()
        self.assertIn("predate this program", output)
        self.assertNotIn("→", output)              # not reported as a value that moved

    def test_record_writes_the_hashes_and_says_what_it_wrote(self):
        self.sourced_project("a3f1c9d")
        _code, output = self.run_check("--record")
        self.assertIn("idea.md#Idea", output)
        code, after = self.run_check()
        self.assertEqual(code, 0, after)            # and the check goes quiet
        self.assertEqual(after, "")

    def test_record_is_idempotent(self):
        self.sourced_project("a3f1c9d")
        self.run_check("--record")
        _code, output = self.run_check("--record")
        self.assertIn("already current", output)

    def test_record_keeps_the_spacing_of_the_line_it_rewrites(self):
        self.sourced_project("a3f1c9d")
        self.run_check("--record")
        line = (self.root / "docs" / "knowledge" / "product.md").read_text(encoding="utf-8")
        self.assertIn("#Idea @", line)              # the space before the @ survived

    # ---- scenarios and their end-to-end tests --------------------------------------------------

    def test_a_scenario_with_no_test_is_counted_as_uncovered(self):
        self.suite("it('x');\n")
        self.write("scenarios.md", "# Scenarios\n\n### Anna accepts an offer\n\n**Who:** Anna\n")
        _code, output = self.run_check("--state")
        self.assertIn("1 described, 0 with an end-to-end test", output)
        self.assertIn("Anna accepts an offer", output)

    def test_a_test_claiming_the_scenario_by_name_counts(self):
        self.suite("// agent-kit:scenario Anna accepts an offer\nit('walks it');\n")
        self.write("scenarios.md", "# Scenarios\n\n### Anna accepts an offer\n\n**Who:** Anna\n")
        self.git("add", "-A")
        _code, output = self.run_check("--state")
        self.assertIn("1 described, 1 with an end-to-end test", output)
        self.assertNotIn("uncovered", output)

    # ---- a project with no blueprint at all ----------------------------------------------------

    def test_a_project_without_knowledge_is_not_a_failure(self):
        shutil.rmtree(self.root / "docs" / "knowledge")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main()
