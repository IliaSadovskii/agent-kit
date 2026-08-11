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


def without_shape(text):
    """Drop the "written by an older kit" statement.

    These fixtures are deliberately minimal — two slots, three fields — so they are behind the
    shipped templates by construction, and that block would appear in every assertion about every
    other rule. It is orthogonal to all of them and has tests of its own, which keep it.
    """
    if "Written by an older kit" not in text:
        return text
    kept, dropping = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("Written by an older kit"):
            dropping = True
            if kept and kept[-1] == "\n":
                kept.pop()
            continue
        if dropping and (line.startswith("  ") or line == "\n"):
            continue
        dropping = False
        kept.append(line)
    return "".join(kept)


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

    def run_check(self, *args, keep_shape=False):
        """Run the check, and by default drop the "written by an older kit" block.

        These fixtures are deliberately minimal — two slots, three fields — so they are behind the
        shipped templates by construction, and that statement would appear in every assertion about
        every other rule. It is orthogonal to all of them and has its own tests, which ask for it.
        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main([str(self.root), "--offline", *args])
        text = out.getvalue()
        return code, text if keep_shape else without_shape(text)

    # ---- the baseline has to be silent, or nothing below means anything -----------------------

    def test_clean_knowledge_says_nothing(self):
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_status_prints_the_standing_even_when_clean(self):
        code, output = self.run_check("--status")
        self.assertEqual(code, 0)
        self.assertIn("built: 1", output)

    # ---- the product's parts, and who has walked them -------------------------------------------

    def test_parts_are_counted_walked_against_derived(self):
        """Two commands were told to read this and neither had anything to read it with: a plain
        blueprint offers the walk, and an epic's gate says how much of the description nobody has
        ever seen."""
        self.write("product.md", "# Product\n\n## Parts\n\n"
                                 "- вход и аккаунт — `walked: 2026-08-09`\n"
                                 "- карта тем — `derived`\n"
                                 "- урок — `walked: 2026-08-10`\n")
        _code, output = self.run_check("--status")
        self.assertIn("Parts: 3 recorded, 2 walked", output)
        self.assertIn("1 derived", output)

    def test_a_product_with_no_parts_recorded_says_so(self):
        self.write("product.md", "# Product\n\n## What it is for\n\nA feed.\n")
        _code, output = self.run_check("--status")
        self.assertIn("Parts: none recorded", output)

    def test_the_templates_own_example_is_not_counted_as_a_part(self):
        """A file copied and not yet filled in would otherwise report three parts nobody has."""
        template = (ROOT / "plugins" / "agent-kit" / "templates" / "knowledge" / "product.md")
        self.write("product.md", template.read_text(encoding="utf-8"))
        _code, output = self.run_check("--status")
        self.assertIn("Parts: none recorded", output)

    def test_the_parts_count_is_a_statement_and_not_a_finding(self):
        self.write("product.md", "# Product\n\n## Parts\n\n- вход — `derived`\n")
        code, _output = self.run_check("--status")
        self.assertEqual(code, 0)

    # ---- knowledge written by an older kit -----------------------------------------------------

    def test_a_record_declaring_fewer_fields_than_the_template_is_named(self):
        """Each file is checked against its own `fields:` line, so a field the templates gained
        later is invisible to every other check there is."""
        self.write("actions.md", ACTIONS.replace("fields: Who, What happens, Can go wrong",
                                                 "fields: Who, What happens"))
        code, output = self.run_check(keep_shape=True)
        self.assertEqual(code, 0, "behind is not broken")
        self.assertIn("Written by an older kit", output)
        self.assertIn("actions.md declares 2 fields per record", output)

    def test_it_names_neither_side_as_the_missing_one(self):
        """The template is in English and the files are in the project's language, so pairing them
        is a guess — both lists are printed and the pairing is done with the owner."""
        self.write("actions.md", ACTIONS.replace("fields: Who, What happens, Can go wrong",
                                                 "fields: Кто, Что происходит"))
        _code, output = self.run_check(keep_shape=True)
        self.assertIn("Template:", output)
        self.assertIn("Here: Кто, Что происходит", output)

    def test_a_project_matching_the_templates_says_nothing(self):
        for name in ("product", "actors", "entities", "actions", "screens", "integrations",
                     "scenarios", "stack"):
            model = ROOT / "plugins" / "agent-kit" / "templates" / "knowledge" / f"{name}.md"
            self.write(f"{name}.md", model.read_text(encoding="utf-8"))
        (self.root / ".agent-kit" / "project.yml").write_text(
            (ROOT / "plugins" / "agent-kit" / "templates" / "project.yml").read_text(encoding="utf-8"),
            encoding="utf-8")
        _code, output = self.run_check(keep_shape=True)
        self.assertNotIn("Written by an older kit", output)

    # ---- the channels a program can check ------------------------------------------------------

    def test_a_file_in_a_run_directory_that_belongs_to_nothing_is_named(self):
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text('{"slug": "x"}', encoding="utf-8")
        (directory / "run.log").write_text("", encoding="utf-8")
        _code, output = self.run_check()
        self.assertNotIn("not a run's own", output)
        (directory / "advance.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("x/advance.sh", output)

    def test_an_audit_box_ticked_without_its_pull_request_is_named(self):
        audits = self.root / "docs" / "audits"
        audits.mkdir(parents=True)
        (audits / "tests.md").write_text(
            "# Tests\n\n- [x] closed by PR #21\n- [ ] still open\n- [x] done, honest\n",
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("ticked without naming the pull request", output)
        self.assertIn("tests.md (1)", output)

    def test_a_declined_item_is_not_a_tick_waiting_for_a_pull_request(self):
        """The lens's own way of recording a refusal. No pull request will ever close one, so a
        rule demanding a number would be permanently wrong about a format the kit prescribes."""
        audits = self.root / "docs" / "audits"
        audits.mkdir(parents=True)
        (audits / "tests.md").write_text(
            "# Tests\n\n- [x] declined: `guest.open_post` — visual only\n", encoding="utf-8")
        _code, output = self.run_check()
        self.assertNotIn("ticked without naming the pull request", output)

    def test_unsigned_ticks_are_counted_per_file_rather_than_listed(self):
        audits = self.root / "docs" / "audits"
        audits.mkdir(parents=True)
        (audits / "tests.md").write_text("# Tests\n\n" + "- [x] done\n" * 12, encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("(12)", output)
        self.assertNotIn("tests.md:3", output)

    # ---- the brief: what a run reads before it designs, in one call ---------------------------

    def test_a_brief_carries_the_entry_the_corner_and_the_map(self):
        self.write("stack.md", "# Stack\n\nLaravel, and no ORM tricks.\n")
        code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertEqual(code, 0)
        self.assertIn("Guest reads the feed", output)
        self.assertIn("newest first", output)
        self.assertIn("knowledge:", output)            # the project's own corner
        self.assertIn("no ORM tricks", output)         # the library map

    def test_a_brief_pulls_in_what_the_entry_names(self):
        self.write("stack.md", "# Stack\n")
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("A guest", output, "the actor the entry names comes with it")

    def test_a_brief_says_what_it_could_not_find(self):
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("does not exist", output, "a missing library map is said, not left out")

    def test_a_brief_names_its_own_boundary(self):
        """Silence in a brief has to mean one thing. Without the boundary, a brief that dropped
        the entry its entry depends on reads like one where the entry depends on nothing."""
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("pulled in:", output)
        self.assertIn("is not looked up", output)

    def test_a_brief_names_a_key_the_knowledge_never_defined(self):
        self.write("actions.md", ACTIONS.replace(
            "**Can go wrong:**", "**Reached from:** `screen.feed`\n\n**Can go wrong:**"))
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertIn("defined nowhere", output)
        self.assertIn("screen.feed", output)

    def test_a_brief_does_not_call_prose_a_missing_key(self):
        """A status, a column and a config path all look like a key. Guessing at them named
        twenty-two innocents in one entry on a real project."""
        self.write("actions.md", ACTIONS.replace(
            "**Can go wrong:**", "**What changes:** the post goes to `archived`, "
                                 "`posts.author_id` stays\n\n**Can go wrong:**"))
        _code, output = self.run_check("--brief", "guest.browse_feed")
        self.assertNotIn("archived", output.split("pulled in:")[-1])
        self.assertNotIn("posts.author_id", output.split("pulled in:")[-1])

    def test_an_unknown_key_names_the_near_miss_instead_of_guessing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _output = self.run_check("--brief", "guest.browse_fee")
        self.assertEqual(code, 2)
        self.assertIn("guest.browse_feed", err.getvalue())

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

    def test_an_open_assumption_is_named_by_the_entry_it_stands_under(self):
        """A run took the decision and every later run in that entry follows it, so what a command
        needs is which entries carry one — it only settles the blocks where it is about to build.
        One `epic` left seventy-four, and printing each of them before every command buries the
        findings that are real."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-04 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, output = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Decisions taken without the owner (1) in 1 entry", output)
        self.assertIn("guest.browse_feed", output)
        self.assertNotIn("beside the post", output, "the count and the entry, not every line")

    def test_a_stale_block_is_a_statement_and_not_a_finding(self):
        """The block sits under the entry it corrects, so no run is misled while it stands. Counting
        it as a defect made every command after a batch report the knowledge as broken, and every
        `next` recommend the same command."""
        self.write("actions.md", ACTIONS + "\n> **[stale 2026-08-05 · claude/x]** Says the driver "
                                           "is `log`; mail goes out over SMTP now.\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("Prose a feature has already outdated (1)", output)
        self.assertIn("SMTP", output)
        self.assertNotIn("Open notes", output)

    def test_an_assumption_stays_a_finding(self):
        """It is a question nobody has answered, which is not the same thing at all."""
        self.write("actions.md", ACTIONS + "\n> **[assumed 2026-08-05 · claude/x]** Nothing says "
                                           "where it is stored. Took: beside the post.\n")
        code, _output = self.run_check()
        self.assertEqual(code, 1)

    def test_an_accepted_block_is_a_statement_and_not_a_finding(self):
        """The owner already said yes, so nothing is outstanding but an interview. Counting it as a
        defect would make every command red between accepting an idea and writing it up."""
        self.write("actions.md", ACTIONS + "\n> **[accepted 2026-08-09 · advise/product]** Импорт "
                                           "каталога одним файлом. Владелец: да, в границы MVP.\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("Accepted and not yet written up (1)", output)
        self.assertIn("каталога", output)
        self.assertNotIn("Open notes", output)

    def test_an_accepted_block_is_listed_apart_from_a_stale_one(self):
        """Two statements with different closers: one is rewritten prose, the other an interview.
        Merging their sections would send the owner to the wrong command."""
        self.write("actions.md", ACTIONS
                   + "\n> **[stale 2026-08-05 · claude/x]** Says the driver is `log`; SMTP now.\n"
                   + "\n> **[accepted 2026-08-09 · advise/code]** Статусы вынести в перечисление.\n")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("Prose a feature has already outdated (1)", output)
        self.assertIn("Accepted and not yet written up (1)", output)

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

    def test_the_unmet_list_is_never_cut(self):
        # ship is told to read the marked test for the entry it is about to touch, so a list cut
        # to a glance can hide exactly the one that run needed.
        body = "".join(f"// agent-kit:unmet guest.browse_feed\nit('{i}')->todo();\n" for i in range(15))
        self.suite(body)
        _code, output = self.run_check()
        self.assertIn("Promises the product does not keep (15)", output)
        self.assertEqual(output.count("guest.browse_feed"), 15)

    def with_merged_pr(self, *args):
        """The check run against a `gh` that says every pull request has merged."""
        import os
        self.write("actions.md", ACTIONS.replace("`state: built`", "`state: building (pr: 7)`"))
        fake = self.root / "bin"
        fake.mkdir(exist_ok=True)
        (fake / "gh").write_text('#!/bin/sh\nprintf \'{"state":"MERGED"}\\n\'\n', encoding="utf-8")
        (fake / "gh").chmod(0o755)
        was = os.environ["PATH"]
        os.environ["PATH"] = f"{fake}:{was}"
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = check.main([str(self.root), *args])
        finally:
            os.environ["PATH"] = was
        return code, without_shape(out.getvalue())

    def test_a_merged_pull_request_moves_the_state_without_killing_the_run(self):
        """The crash this covers took every command's preflight down the day a feature landed."""
        code, output = self.with_merged_pr("--sync")
        self.assertEqual(code, 0, output)
        self.assertIn("building (pr: 7) → built", output)
        self.assertIn("state: built",
                      (self.root / "docs" / "knowledge" / "actions.md").read_text(encoding="utf-8"))

    def test_the_check_writes_nothing_unless_it_is_asked_to(self):
        """Every command runs this before it starts; only `blueprint --check` may leave a change."""
        code, output = self.with_merged_pr()
        self.assertEqual(code, 0, output)
        self.assertNotIn("→ built", output)
        self.assertIn("state: building (pr: 7)",
                      (self.root / "docs" / "knowledge" / "actions.md").read_text(encoding="utf-8"))

    def test_a_line_behind_its_merged_pull_request_is_said_out_loud(self):
        """Writing is asked for; noticing is not. A merged feature stuck at `building` was invisible
        to every command for one release, which is how it reached a live project."""
        _code, output = self.with_merged_pr()
        self.assertIn("pull request 7 has merged", output)
        self.assertIn("guest.browse_feed", output)

    def test_offline_asks_gh_nothing_at_all(self):
        _code, output = self.with_merged_pr("--offline")
        self.assertEqual(output, "")

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

    def test_a_mark_naming_a_scenario_that_no_longer_exists_is_said_out_loud(self):
        self.suite("// agent-kit:scenario Anna accepts an offer\nit('walks it');\n")
        self.write("scenarios.md", "# Scenarios\n\n### Anna declines an offer\n\n**Who:** Anna\n")
        self.git("add", "-A")
        _code, output = self.run_check("--state")
        self.assertIn("no scenario by that heading exists", output)

    # ---- dependency manifests nobody recorded ---------------------------------------------------

    def test_a_manifest_the_project_does_not_record(self):
        self.suite("it('x');\n")
        (self.root / "package.json").write_text('{"name": "x"}\n', encoding="utf-8")
        self.git("add", "-A")
        _code, output = self.run_check()
        self.assertIn("package.json is a dependency manifest that project.yml does not record",
                      output)

    def test_a_recorded_manifest_is_not_reported_twice(self):
        self.suite("it('x');\n")
        (self.root / "package.json").write_text('{"name": "x"}\n', encoding="utf-8")
        current = check.digest('{"name": "x"}\n')
        (self.root / ".agent-kit" / "project.yml").write_text(
            MANIFEST + f"checks:\n  deps:\n    package.json: {current}\n", encoding="utf-8")
        self.git("add", "-A")
        code, output = self.run_check()
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "")

    # ---- a project with no blueprint at all ----------------------------------------------------

    def test_a_project_without_knowledge_is_not_a_failure(self):
        shutil.rmtree(self.root / "docs" / "knowledge")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    # ---- the gate of an epic ---------------------------------------------------------------------
    #
    # A sprint with a thin blueprint still delivers five features; an epic with one has no stopping
    # condition. These three are what it refuses to start without.

    def ready_for_mvp(self, product=None, scenarios=None, commands=True):
        self.write("product.md", product if product is not None else
                   "# Product\n\n## MVP bounds\n\n**In:** sign-in, the composer\n\n"
                   "**Out:** comments, search\n")
        self.write("scenarios.md", scenarios if scenarios is not None else
                   "# Scenarios\n\n### Anna publishes a story\n\n**Who:** Anna\n")
        if commands:
            (self.root / ".agent-kit" / "project.yml").write_text(
                MANIFEST + "commands:\n  test: make test\n  run: make up\n", encoding="utf-8")
        return self.run_check("--epic")

    def test_a_project_that_may_start_an_mvp(self):
        code, output = self.ready_for_mvp()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_bounds_written_in_another_language_are_still_bounds(self):
        """The bounds are the owner's prose, in the project's own language — the heading is too."""
        code, output = self.ready_for_mvp(
            product="# Продукт\n\n## Границы MVP\n\n**Входит:** вход, композер\n\n"
                    "**Не входит:** комментарии, поиск\n")
        self.assertEqual(code, 0, output)

    def test_no_bounds_at_all(self):
        code, output = self.ready_for_mvp(product="# Product\n\n## What it is for\n\nStories.\n")
        self.assertEqual(code, 1)
        self.assertIn("no MVP bounds section", output)

    def test_bounds_with_only_one_side(self):
        code, output = self.ready_for_mvp(
            product="# Product\n\n## MVP bounds\n\n**In:** sign-in, the composer\n")
        self.assertEqual(code, 1)
        self.assertIn("not two lists", output)

    def test_no_scenarios_to_prove_the_end_against(self):
        code, output = self.ready_for_mvp(scenarios="# Scenarios\n\nNone yet.\n")
        self.assertEqual(code, 1)
        self.assertIn("no scenarios are described", output)

    def test_no_command_that_starts_the_application(self):
        code, output = self.ready_for_mvp(commands=False)
        self.assertEqual(code, 1)
        self.assertIn("commands.run", output)

    # ---- what a run may not close with ---------------------------------------------------------
    #
    # These are the two rules that used to hold only if the run remembered them at the end of its
    # longest step. Each is shown firing, and shown silent on the run that did the thing right.

    def close(self, **fields):
        """A run file at `done` with everything filled in, minus whatever the test breaks."""
        state = {"slug": "x", "command": "ship", "step": "done", "suite": "made 41 green, lint ok",
                 "review": {"verdict": "ok", "findings": [], "security": None}}
        state.update(fields)
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "run.json").write_text(json.dumps(state), encoding="utf-8")
        return self.run_check("--run", str(directory))

    def test_a_finished_run_that_did_everything_says_nothing(self):
        code, output = self.close()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_major_finding_left_open_is_not_done(self):
        code, output = self.close(review={"findings": [
            {"severity": "major", "what": "the token is logged", "closed": False}]})
        self.assertEqual(code, 1)
        self.assertIn("a major review finding is open", output)
        self.assertIn("the token is logged", output)

    def test_a_finding_that_was_closed_is_not_reported(self):
        code, output = self.close(review={"findings": [
            {"severity": "critical", "what": "x", "closed": True},
            {"severity": "minor", "what": "y", "closed": False}]})
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_run_that_says_nothing_about_its_suite(self):
        code, output = self.close(suite=None)
        self.assertEqual(code, 1)
        self.assertIn("`suite` is empty", output)

    def test_a_finding_written_as_a_sentence_is_not_a_finding(self):
        """Five runs of one night wrote `"major — …, closed by …"` instead of a record, so the rule
        about closing with an open critical one was never once applied — the check skipped what it
        could not read, silently."""
        code, output = self.close(review={"findings": [
            "major — assertMissing cannot fail. Closed by reordering the fixtures."]})
        self.assertEqual(code, 1)
        self.assertIn("written as a sentence", output)

    def test_a_record_field_filled_with_prose_is_named(self):
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps(
            {"slug": "x", "step": "build", "tasks": ["write the test", "make it pass"]}),
            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("fill a field of records with sentences", output)
        self.assertIn("tasks (1)", output)

    def test_records_written_as_sentences_stop_a_run_closing(self):
        for field in ("tasks", "assumptions"):
            code, output = self.close(**{field: ["did the thing", "did the other"]})
            self.assertEqual(code, 1, field)
            self.assertIn(f"`{field}` is written as sentences", output)

    def test_a_run_still_working_is_not_judged(self):
        code, output = self.close(step="build", suite=None, review={"findings": [
            {"severity": "critical", "what": "x", "closed": False}]})
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_blocked_run_is_already_saying_so(self):
        code, output = self.close(step="blocked", suite=None)
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    # ---- the handoff, the other moment a run file has to stand on its own ----------------------

    def handover(self, **fields):
        state = {"slug": "x", "command": "ship", "step": "build", "suite": None,
                 "approach": "the endpoint, then the screen",
                 "tasks": [{"id": 1, "what": "the endpoint", "done": True}],
                 "handoff": "stopped after task 1; the queue seam deadlocks under sqlite"}
        state.update(fields)
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "run.json").write_text(json.dumps(state), encoding="utf-8")
        return self.run_check("--run", str(directory))

    def test_a_handoff_that_stands_on_its_own_says_nothing(self):
        code, output = self.handover()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_note_that_outgrew_the_field_is_named(self):
        code, output = self.handover(handoff="x" * (check.HANDOFF_MAX + 1))
        self.assertEqual(code, 1)
        self.assertIn("against a ceiling", output)

    def test_a_handoff_with_no_approach_would_be_designed_twice(self):
        code, output = self.handover(approach="")
        self.assertEqual(code, 1)
        self.assertIn("design this feature a second time", output)

    def test_a_handoff_whose_tasks_are_prose_says_nothing_about_what_is_left(self):
        code, output = self.handover(tasks=["the endpoint", "the screen"])
        self.assertEqual(code, 1)
        self.assertIn("`done` is how the next session tells", output)
        code, output = self.handover(tasks=[])
        self.assertEqual(code, 1)
        self.assertIn("which task the handoff stopped after", output)

    def test_no_note_means_no_handoff_to_judge(self):
        for note in (None, "", "  "):
            code, output = self.handover(handoff=note, approach="", tasks=[])
            self.assertEqual(code, 0, repr(note))
            self.assertEqual(output, "", repr(note))

    def test_the_template_itself_closes_nothing(self):
        """The shipped template carries a placeholder severity; it must not read as a finding."""
        template = json.loads(
            (ROOT / "plugins" / "agent-kit" / "templates" / "run.json").read_text(encoding="utf-8"))
        template["step"] = "done"
        template["suite"] = "green"
        template["pr"] = 21
        self.assertEqual(check.run_defects(template), [])

    def test_a_run_that_owed_a_pull_request_and_has_no_number(self):
        state = {"deliver": "pr", "step": "done", "suite": "green", "tasks": [], "pr": None}
        self.assertTrue(any("`pr` is empty" in line for line in check.run_defects(state)))

    def test_a_run_that_hit_a_blocker_may_close_without_one(self):
        state = {"deliver": "pr", "step": "done", "suite": "green", "pr": None,
                 "blockers": ["the gateway has no sandbox key"]}
        self.assertFalse(any("`pr` is empty" in line for line in check.run_defects(state)))

    def test_a_feature_inside_a_batch_owes_no_pull_request(self):
        """`deliver` decides it, not `command`: a child pushes a branch, and a batch's own file
        carries no `deliver` at all — both fall outside this by construction."""
        child = {"deliver": "branch", "step": "done", "suite": "green", "pr": None}
        self.assertEqual(check.run_defects(child), [])
        batch = {"command": "sprint", "step": "done", "suite": "green", "pr": None}
        self.assertFalse(any("`pr` is empty" in line for line in check.run_defects(batch)))

    def test_a_batch_that_left_no_durable_record(self):
        state = {"command": "sprint", "slug": "2026-08-05-offers", "step": "done",
                 "suite": "green", "pr": 21}
        defects = check.run_defects(state, self.root)
        self.assertTrue(any("docs/runs/2026-08-05-offers.json" in line for line in defects))

    def test_a_batch_that_wrote_its_record_says_nothing(self):
        (self.root / "docs" / "runs").mkdir(parents=True)
        (self.root / "docs" / "runs" / "2026-08-05-offers.json").write_text("{}", encoding="utf-8")
        state = {"command": "sprint", "slug": "2026-08-05-offers", "step": "done",
                 "suite": "green", "pr": 21}
        self.assertEqual(check.run_defects(state, self.root), [])

    def test_without_a_project_the_record_rule_is_skipped_rather_than_guessed(self):
        state = {"command": "sprint", "slug": "2026-08-05-offers", "step": "done",
                 "suite": "green", "pr": 21}
        self.assertEqual(check.run_defects(state), [])

    def test_a_knowledge_file_the_kit_has_no_template_for_is_named(self):
        """Three checks key off the template — fields, shape, verdict — and a file with none slips
        all three at once. The product template itself invites one for an API or a CLI."""
        self.write("endpoints.md", "# Endpoints\n\n### GET /feed\n`key: endpoint.feed`\n")
        _code, output = self.run_check(keep_shape=True)
        self.assertIn("endpoints.md has no template", output)

    def test_a_step_no_reader_knows_is_named(self):
        directory = self.root / ".agent-kit" / "runs" / "x"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"slug": "x", "step": "polishing"}),
                                            encoding="utf-8")
        _code, output = self.run_check()
        self.assertIn("step 'polishing'", output)

    def test_the_steps_a_driver_writes_are_not_findings(self):
        directory = self.root / ".agent-kit" / "runs" / "batch"
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"slug": "batch", "step": "building"}),
                                            encoding="utf-8")
        code, output = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_a_run_directory_with_no_file(self):
        code, _output = self.run_check("--run", str(self.root / ".agent-kit" / "runs" / "gone"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
